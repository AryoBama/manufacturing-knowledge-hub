import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from src.query.models import QueryRequest, QueryUnderstanding, KnowledgeType
from src.query.intent import classify_intent
from src.query.parser import extract_entities
from src.query.entity_resolution import resolve_equipment_entity

# Config path
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "configs" / "knowledge_routing.json"


class KnowledgeRouter:
    """
    Intent-Specific Knowledge & Document Router.
    Maps: Intent -> Knowledge Types -> Document Categories (with intent-dependent source priority)
    """
    def __init__(self, config_file: Path = CONFIG_PATH):
        self.config_file = config_file
        self._intent_to_kt: Dict[str, List[str]] = {}
        self._kt_to_docs: Dict[str, List[str]] = {}
        self._intent_source_priority: Dict[str, List[str]] = {}
        self._load_config()

    def _load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self._intent_to_kt = cfg.get("intent_to_knowledge_types", {})
                self._kt_to_docs = cfg.get("knowledge_to_document_types", {})
                self._intent_source_priority = cfg.get("intent_source_priority", {})
                return
            except Exception as e:
                print(f"[WARN] Failed to load {self.config_file}: {e}, using default routing table.")

        # Hardcoded default fallback
        self._intent_to_kt = {
            "troubleshooting": [
                KnowledgeType.OPERATING_PROCEDURE.value,
                KnowledgeType.PROTECTION_LOGIC.value,
                KnowledgeType.FAILURE_HISTORY.value,
                KnowledgeType.PROCESS_LOGIC.value
            ],
            "protection": [
                KnowledgeType.PROTECTION_LOGIC.value,
                KnowledgeType.PROCESS_LOGIC.value
            ],
            "failure_history": [
                KnowledgeType.FAILURE_HISTORY.value
            ],
            "procedure": [
                KnowledgeType.OPERATING_PROCEDURE.value
            ],
            "equipment_information": [
                KnowledgeType.EQUIPMENT_SPEC.value
            ],
            "location": [
                KnowledgeType.PHYSICAL_LOCATION.value
            ],
            "general_information": [
                KnowledgeType.GENERAL_KNOWLEDGE.value
            ]
        }
        self._kt_to_docs = {
            KnowledgeType.OPERATING_PROCEDURE.value: ["OPL", "SOP"],
            KnowledgeType.PROCESS_LOGIC.value: ["PID"],
            KnowledgeType.PROTECTION_LOGIC.value: ["INTERLOCK", "PID"],
            KnowledgeType.FAILURE_HISTORY.value: ["MAINTENANCE"],
            KnowledgeType.EQUIPMENT_SPEC.value: ["DATASHEET", "GA_DRAWING"],
            KnowledgeType.PHYSICAL_LOCATION.value: ["PLOT_PLAN", "GA_DRAWING"],
            KnowledgeType.GENERAL_KNOWLEDGE.value: [
                "DATASHEET", "OPL", "INTERLOCK", "MAINTENANCE", "PID", "GA_DRAWING", "PLOT_PLAN"
            ]
        }
        self._intent_source_priority = {
            "troubleshooting": ["OPL", "INTERLOCK", "MAINTENANCE", "PID"],
            "protection": ["INTERLOCK", "PID"],
            "failure_history": ["MAINTENANCE"],
            "procedure": ["OPL", "SOP"],
            "equipment_information": ["DATASHEET", "GA_DRAWING"],
            "location": ["PLOT_PLAN", "GA_DRAWING"],
            "general_information": [
                "DATASHEET", "OPL", "INTERLOCK", "MAINTENANCE", "PID", "GA_DRAWING", "PLOT_PLAN"
            ]
        }

    def get_knowledge_types(self, intent: str) -> List[str]:
        return self._intent_to_kt.get(intent, self._intent_to_kt.get("general_information", ["general_knowledge"]))

    def route_to_documents(self, knowledge_types: List[str], intent: Optional[str] = None) -> List[str]:
        """
        Intent-dependent document prioritization:
        If intent is known, returns document types ordered by priority specific to that information need.
        """
        if intent and intent in self._intent_source_priority:
            return list(self._intent_source_priority[intent])

        doc_set = []
        for kt in knowledge_types:
            for doc in self._kt_to_docs.get(kt, []):
                if doc not in doc_set:
                    doc_set.append(doc)
        return doc_set

    def route_intent(self, intent: str) -> Tuple[List[str], List[str]]:
        kt = self.get_knowledge_types(intent)
        docs = self.route_to_documents(kt, intent=intent)
        return kt, docs


# Global default router instance
_DEFAULT_ROUTER = KnowledgeRouter()
KNOWLEDGE_TO_DOCUMENTS = _DEFAULT_ROUTER._kt_to_docs


def get_knowledge_types_for_intent(intent: str) -> List[str]:
    return _DEFAULT_ROUTER.get_knowledge_types(intent)


def route_knowledge_to_documents(knowledge_types: List[str], intent: Optional[str] = None) -> List[str]:
    return _DEFAULT_ROUTER.route_to_documents(knowledge_types, intent=intent)


def understand_query(request: QueryRequest) -> QueryUnderstanding:
    intent = classify_intent(request.query)
    entities = extract_entities(request.query)
    tag, resolution, requires_clarification, reason = resolve_equipment_entity(
        query=request.query,
        explicit_tag=request.equipment_tag,
        session_context=request.session_context
    )

    if intent == "general_information" and requires_clarification:
        # If multiple equipment tags are mentioned, ALWAYS demand clarification to prevent cross-asset cross-talk!
        if len(resolution.candidate_tags) > 1:
            requires_clarification = True
        else:
            requires_clarification = False
            reason = None

    knowledge_types = _DEFAULT_ROUTER.get_knowledge_types(intent)

    return QueryUnderstanding(
        query=request.query,
        intent=intent,
        equipment_tag=tag,
        resolution=resolution,
        entities=entities,
        knowledge_types=knowledge_types,
        requires_clarification=requires_clarification,
        clarification_reason=reason
    )
