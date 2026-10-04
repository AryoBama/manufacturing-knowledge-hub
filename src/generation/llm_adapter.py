import os
import json
import re
from typing import Optional, List, Union
from src.query.models import QueryUnderstanding
from src.retrieval.models import RetrievalResult, SufficiencyCheck
from src.retrieval.structured_store import StructuredKnowledgeStore
from src.generation.evidence import EvidencePackage, EvidenceFusionEngine
from src.generation.models import GeneratedAnswer, ConfidenceLevel, SourceCitation
from src.generation.synthesizer import AnswerSynthesizer


from src.adapters.llm import LLMAdapter, OfflineMockAdapter, get_llm_adapter


class LLMAnswerAdapter:
    """
    Phase 3 Pluggable LLM Grounding Adapter:
    Consumes EvidencePackage and generates natural language responses strictly constrained
    to retrieved evidence IDs.
    Delegates all provider/protocol communication to the pluggable LLMAdapter.
    If no key is configured, network drops, or output is invalid, falls back gracefully to
    the deterministic AnswerSynthesizer.
    """
    def __init__(
        self,
        fallback_synthesizer: Optional[AnswerSynthesizer] = None,
        structured_store: Optional[StructuredKnowledgeStore] = None,
        adapter: Optional[LLMAdapter] = None,
    ):
        self.fallback_synthesizer = fallback_synthesizer or AnswerSynthesizer(structured_store=structured_store)
        self.structured_store = structured_store
        self.adapter = adapter or get_llm_adapter()

    def generate(self, package: EvidencePackage) -> GeneratedAnswer:
        # If offline or no key available, directly use deterministic generator
        if isinstance(self.adapter, OfflineMockAdapter):
            return self.fallback_synthesizer.generate(package)

        try:
            return self._call_llm(package)
        except Exception as e:
            ans = self.fallback_synthesizer.generate(package)
            err_msg = str(e)
            if "429" in err_msg or "ResourceExhausted" in err_msg or "quota" in err_msg.lower() or "too many requests" in err_msg.lower():
                clean_err = "LLM provider rate limit exceeded (429 Quota)"
            elif "401" in err_msg or "403" in err_msg or "unauthorized" in err_msg.lower():
                clean_err = "LLM authentication failed"
            else:
                clean_err = re.sub(r'https?://\S+', '', err_msg).strip()
                clean_err = clean_err.split("\n")[0][:100]
            ans.confidence_reason += f" (Note: Deterministic fallback applied: {clean_err})"
            return ans

    def synthesize(
        self,
        query: Union[str, EvidencePackage],
        understanding: Optional[QueryUnderstanding] = None,
        results: Optional[List[RetrievalResult]] = None,
        sufficiency: Optional[SufficiencyCheck] = None
    ) -> GeneratedAnswer:
        if isinstance(query, EvidencePackage):
            return self.generate(query)

        package = EvidenceFusionEngine.fuse(
            understanding=understanding,
            retrieval_results=results or [],
            sufficiency=sufficiency,
            structured_store=self.structured_store
        )
        return self.generate(package)

    def _call_llm(self, package: EvidencePackage) -> GeneratedAnswer:
        # Deterministic generation handles safe refusal states before making LLM calls
        base_ans = self.fallback_synthesizer.generate(package)
        if base_ans.requires_clarification or package.sufficiency.value != "sufficient":
            return base_ans

        system_msg = (
            "You are an industrial engineer at Chandra Asri Pacific.\n"
            "Answer the technical query directly, concisely, and factually in natural language using ONLY the provided verified evidence.\n"
            "State specific values, tags, setpoints, and units directly (e.g. pressure, temperature, trip setpoint).\n"
            "Do not extrapolate or speculate beyond the evidence.\n"
            "Do NOT output raw JSON, code blocks, or meta-commentary. Output the direct factual explanation."
        )

        q_tokens = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', package.query.lower()))
        stop_words = {"what", "how", "about", "the", "for", "and", "does", "can", "tell", "show", "is", "are"}
        substantive_tokens = {t for t in q_tokens if t not in stop_words}

        def item_priority(it):
            score = 0
            c_lower = it.content.lower()
            if any(t in c_lower for t in substantive_tokens):
                score += 15
            if it.evidence_type == "document_chunk":
                score += 5
            return score

        sorted_items = sorted(package.items, key=item_priority, reverse=True)
        evidence_text = "\n".join(
            f"[{item.document_id} p.{getattr(item.source, 'page_number', 1)}]: {item.content}"
            for item in sorted_items[:15]
        )
        user_msg = f"Equipment: {package.equipment_tag or 'N/A'}\nQuery: {package.query}\nEvidence:\n{evidence_text}"

        content = self.adapter.complete(user_msg, system_prompt=system_msg, temperature=0.0)

        cleaned = content.strip()
        # 1. Strip markdown fences if present
        if "```" in cleaned:
            cleaned = re.sub(r'^```(?:json|markdown)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        # 2. If model output JSON structure, parse or safely extract summary_answer
        if '"summary_answer"' in cleaned or (cleaned.startswith("{") and cleaned.endswith("}")):
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "summary_answer" in parsed:
                    cleaned = str(parsed["summary_answer"]).strip()
                    pts = parsed.get("detailed_points")
                    if isinstance(pts, list) and len(pts) > 0:
                        base_ans.detailed_points = [str(p).strip() for p in pts if str(p).strip()]
                        attribution = self.fallback_synthesizer._attribution(package, base_ans.detailed_points, base_ans.citations)
                        for field, value in attribution.items():
                            setattr(base_ans, field, value)
            except Exception:
                # Regex fallback to extract value of "summary_answer": "..." even from truncated JSON
                m = re.search(r'"summary_answer"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
                if m:
                    try:
                        cleaned = m.group(1).encode('utf-8').decode('unicode_escape', errors='ignore').strip()
                    except Exception:
                        cleaned = m.group(1).strip()
                else:
                    # Clean any leading/trailing JSON markers
                    cleaned = re.sub(r'^[{\s"]*summary_answer[":\s]*', '', cleaned).strip()
                    cleaned = re.sub(r'[,}\s"]*$', '', cleaned).strip()

        # 3. Final safety sanitization: never allow raw JSON syntax to leak into natural language summary
        cleaned = re.sub(r'^\s*\{\s*"summary_answer":\s*"?', '', cleaned)
        cleaned = re.sub(r'"\s*,\s*"detailed_points":.*$', '', cleaned, flags=re.DOTALL)
        cleaned = cleaned.rstrip('"}').strip()

        if cleaned:
            base_ans.summary_answer = cleaned

        return base_ans
