from typing import List, Optional
from src.generation.evidence import EvidencePackage, EvidenceItem
from src.generation.models import OperationalRecommendation


class RecommendationEngine:
    """
    Decoupled Operational Guidance Engine:
    Ensures operational recommendations are never conflated with factual answers.
    Recommendations are ONLY produced when:
      1. The user's information need requires actionable guidance (troubleshooting, safety protection).
      2. The recommendation is strictly anchored to a verified EvidenceItem.
    Pure factual queries (e.g. equipment dimensions, rated flow) return empty recommendations.
    """

    @classmethod
    def generate_recommendations(cls, package: EvidencePackage) -> List[OperationalRecommendation]:
        if not package.is_sufficient:
            return []

        intent = package.intent
        # Factual intents: No unsolicited operational recommendations
        if intent in ("equipment_information", "location"):
            return []

        recommendations: List[OperationalRecommendation] = []

        # 1. Protection Guidance
        if intent == "protection":
            rel_items = package.get_items_by_type("relationship")
            doc_items = [it for it in package.items if it.document_type in ("INTERLOCK", "PID")]
            ref_ev_id = rel_items[0].evidence_id if rel_items else (doc_items[0].evidence_id if doc_items else None)

            recommendations.append(
                OperationalRecommendation(
                    action="Verify that all interlock start permissives are satisfied in DCS prior to motor energization.",
                    basis="Mandatory start permissive interlock sequence.",
                    evidence_id=ref_ev_id,
                    priority="HIGH",
                    applicability="Pre-Startup Sequence"
                )
            )
            recommendations.append(
                OperationalRecommendation(
                    action="Do not defeat or bypass safety interlocks without approved Management of Change (MOC) documentation.",
                    basis="Plant process safety interlock integrity procedure.",
                    evidence_id=ref_ev_id,
                    priority="CRITICAL",
                    applicability="Abnormal Operations / Jumpering"
                )
            )

        # 2. Troubleshooting & Diagnostic Guidance
        elif intent == "troubleshooting":
            opl_items = [it for it in package.items if it.document_type == "OPL"]
            mnt_items = package.get_items_by_type("maintenance_event")

            if opl_items:
                recommendations.append(
                    OperationalRecommendation(
                        action="Perform local vibration and bearing temperature survey using calibrated field vibration analyzer.",
                        basis="OPL standardized diagnostic checklist for rotating equipment anomaly.",
                        evidence_id=opl_items[0].evidence_id,
                        priority="HIGH",
                        applicability="Vibration or Anomaly Investigation"
                    )
                )

            if mnt_items:
                ref_mnt = mnt_items[0]
                recommendations.append(
                    OperationalRecommendation(
                        action="Inspect mechanical seal flush and suction strainer for differential pressure accumulation.",
                        basis=f"Historical breakdown work order record ({ref_mnt.document_id}).",
                        evidence_id=ref_mnt.evidence_id,
                        priority="HIGH",
                        applicability="Suspected Misalignment or Seal Distress"
                    )
                )

        # 3. Failure History Review
        elif intent == "failure_history":
            mnt_items = package.get_items_by_type("maintenance_event")
            if mnt_items:
                recommendations.append(
                    OperationalRecommendation(
                        action="Review recurring component failure modes in SAP PM prior to major turnaround maintenance.",
                        basis="Historical maintenance work order pattern.",
                        evidence_id=mnt_items[0].evidence_id,
                        priority="MEDIUM",
                        applicability="Preventive Maintenance Planning"
                    )
                )

        # 4. Procedure Execution Guidance
        elif intent == "procedure":
            opl_items = [it for it in package.items if it.document_type in ("OPL", "SOP")]
            if opl_items:
                recommendations.append(
                    OperationalRecommendation(
                        action="Complete pre-startup valve lineup check sheet before energizing pump driver.",
                        basis="Approved One Point Lesson / SOP execution protocol.",
                        evidence_id=opl_items[0].evidence_id,
                        priority="HIGH",
                        applicability="Operating Procedure Execution"
                    )
                )

        return recommendations
