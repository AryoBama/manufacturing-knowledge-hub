from typing import Optional
from src.generation.models import GeneratedAnswer, ConfidenceLevel


class AnswerFormatter:
    """
    Renders GeneratedAnswer into clean, industrial-grade formats:
    - Markdown (for web UI, docs, reports)
    - Terminal Text (with clean ANSI/ASCII for CLI and video presentations)
    """

    @staticmethod
    def to_markdown(ans: GeneratedAnswer) -> str:
        lines = []
        tag_str = f" `{ans.equipment_tag}`" if ans.equipment_tag else ""
        name_str = f" ({ans.equipment_name})" if ans.equipment_name else ""
        
        lines.append(f"### Knowledge Hub Response: {tag_str}{name_str}")
        lines.append("")

        # Categorical Confidence Badge
        conf_icon = "🟢" if ans.confidence == ConfidenceLevel.HIGH else ("🟡" if ans.confidence == ConfidenceLevel.MEDIUM else "🔴")
        qid_str = f" `[{ans.query_id}]`" if ans.query_id else ""
        lines.append(f"> **Confidence**: {conf_icon} **{ans.confidence.value}**{qid_str} — _{ans.confidence_reason}_")
        lines.append("")

        # Decomposed Confidence Details
        if ans.confidence_breakdown:
            bd = ans.confidence_breakdown
            lines.append("<details>")
            lines.append(f"<summary>🔍 <b>Confidence Score Decomposition ({bd.final_score * 100:.1f}%)</b></summary>")
            lines.append("")
            lines.append(f"- **Asset Match**: {bd.asset_match_score * 100:.0f}% (Weight: 25%)")
            lines.append(f"- **Source Document Validity**: {bd.source_validity_score * 100:.0f}% (Weight: 25%)")
            lines.append(f"- **Retrieval Sufficiency**: {bd.retrieval_sufficiency_score * 100:.0f}% (Weight: 25%)")
            lines.append(f"- **Knowledge Coverage**: {bd.coverage_score * 100:.0f}% (Weight: 15%)")
            lines.append(f"- **Intent Certainty**: {bd.intent_confidence * 100:.0f}% (Weight: 10%)")
            if bd.conflict_penalty > 0:
                lines.append(f"- ⚠️ **Conflict Penalty**: -{bd.conflict_penalty * 100:.0f}%")
            if bd.obsolete_penalty > 0:
                lines.append(f"- ⚠️ **Obsolete Document Penalty**: -{bd.obsolete_penalty * 100:.0f}%")
            lines.append(f"- *Formula*: `{bd.formula}`")
            lines.append("</details>")
            lines.append("")

        # Clarification prompt if required
        if ans.requires_clarification:
            lines.append(f"> [!WARNING]  ")
            lines.append(f"> **Clarification Required**: {ans.clarification_prompt or ans.summary_answer}")
            lines.append("")
            return "\n".join(lines)


        # Factual Summary
        lines.append(f"**Factual Summary**: {ans.summary_answer}")
        lines.append("")

        # Detailed points
        if ans.detailed_points:
            lines.append("**Technical Evidence & Specifications**:")
            for p in ans.detailed_points:
                lines.append(f"- {p}")
            lines.append("")

        # Traceable Citations
        if ans.citations:
            lines.append("**Verified Engineering Sources**:")
            for c in ans.citations:
                rev_str = f", Rev: `{c.revision}`" if c.revision else ", Rev: `N/A`"
                stat_str = f", Status: `{c.status}`" if c.status else ""
                pg_str = f", Page {c.page}" if c.page is not None else ""
                lines.append(f"- **{c.document_type}** — `{c.document_id}` [Evidence ID: `{c.evidence_id}`] ({c.file_name}{rev_str}{stat_str}{pg_str})")
            lines.append("")

        # Decoupled Operational Recommendations (only if present)
        if ans.recommendations:
            lines.append("**Operational Guidance (Decoupled & Evidence-Bounded)**:")
            for idx, rec in enumerate(ans.recommendations, 1):
                p_badge = f"[{rec.priority}]"
                app_str = f" (Applicability: _{rec.applicability}_)" if rec.applicability else ""
                ref_str = f" [Basis: {rec.basis} | Evidence: `{rec.evidence_id}`]" if rec.evidence_id else f" [Basis: {rec.basis}]"
                lines.append(f"{idx}. {p_badge} **Action**: {rec.action}{app_str}")
                lines.append(f"   - _{ref_str}_")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_terminal_text(ans: GeneratedAnswer) -> str:
        border = "=" * 76
        divider = "-" * 76
        lines = [border]

        tag_display = ans.equipment_tag or "GENERAL"
        name_display = f" | {ans.equipment_name}" if ans.equipment_name else ""
        lines.append(f" [CHANDRA ASRI MANUFACTURING KNOWLEDGE HUB] ")
        if ans.query_id:
            lines.append(f" Trace ID     : {ans.query_id}")
        lines.append(f" Target Asset : {tag_display}{name_display}")
        lines.append(f" Query Intent : {ans.intent.upper()}")
        score_str = f" ({ans.confidence_breakdown.final_score * 100:.1f}%)" if ans.confidence_breakdown else ""
        lines.append(f" Confidence   : {ans.confidence.value}{score_str} - {ans.confidence_reason}")
        lines.append(divider)


        if ans.requires_clarification:
            lines.append(" [!] CLARIFICATION REQUIRED:")
            lines.append(f"     {ans.clarification_prompt or ans.summary_answer}")
            lines.append(border)
            return "\n".join(lines)

        lines.append(" FACTUAL SUMMARY:")
        lines.append(f"   {ans.summary_answer}")
        lines.append("")

        if ans.detailed_points:
            lines.append(" TECHNICAL EVIDENCE & DETAILS:")
            for pt in ans.detailed_points:
                safe_pt = pt.replace("\u2192", "->").replace("•", "*")
                lines.append(f"   {safe_pt}")
            lines.append("")

        if ans.citations:
            lines.append(" PROVENANCE & SOURCE CITATIONS:")
            for c in ans.citations:
                lines.append(f"   * [{c.evidence_id}] {c.badge} -> {c.file_name}")
            lines.append("")

        if ans.recommendations:
            lines.append(" OPERATIONAL RECOMMENDATIONS (DECOUPLED & GROUNDED):")
            for idx, rec in enumerate(ans.recommendations, 1):
                safe_action = rec.action.replace("\u2192", "->").replace("•", "*")
                lines.append(f"   [{idx}] [{rec.priority}] Action: {safe_action}")
                lines.append(f"       Basis: {rec.basis} (Evidence: {rec.evidence_id or 'General Plant Safety'})")
            lines.append("")

        lines.append(border)
        return "\n".join(lines)
