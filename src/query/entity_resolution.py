import re
from typing import Optional, Dict, Any, Tuple, List
from src.query.models import ResolutionMetadata, ResolutionSource, ResolutionConfidence
from src.query.parser import extract_equipment_tags, PLANT_EQUIPMENT_REGISTRY


def _extract_tag_from_history(history: List[Dict[str, Any]]) -> Optional[str]:
    # Iterate backwards through chat history
    for msg in reversed(history):
        content = msg.get("content", "")
        tags = extract_equipment_tags(content)
        if tags:
            return tags[0]
    return None


def resolve_equipment_entity(
    query: str,
    explicit_tag: Optional[str] = None,
    session_context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], ResolutionMetadata, bool, Optional[str]]:
    """
    Phase 2C Entity Resolution:
    Determines the intended equipment tag across 4 context tiers:
    1. Explicit in parameter or query text
    2. UI context
    3. Conversation context (recent tag or chat history traversal)
    4. Generic category inference or clarification
    """
    ctx = session_context or {}

    # Tier 1a: Explicit parameter passed
    if explicit_tag:
        tag = explicit_tag.upper()
        return (
            tag,
            ResolutionMetadata(source=ResolutionSource.EXPLICIT_QUERY, confidence=ResolutionConfidence.HIGH, candidate_tags=[tag]),
            False,
            None
        )

    # Tier 1b: Explicit equipment tag or full alias detected in query text
    tags_in_query = extract_equipment_tags(query)
    if len(tags_in_query) == 1:
        tag = tags_in_query[0]
        return (
            tag,
            ResolutionMetadata(source=ResolutionSource.EXPLICIT_QUERY, confidence=ResolutionConfidence.HIGH, candidate_tags=[tag]),
            False,
            None
        )
    elif len(tags_in_query) > 1:
        return (
            None,
            ResolutionMetadata(source=ResolutionSource.EXPLICIT_QUERY, confidence=ResolutionConfidence.LOW, candidate_tags=tags_in_query),
            True,
            f"Multiple equipment candidates found: {', '.join(tags_in_query)}. Please specify which one to inspect."
        )

    # Tier 2: UI Context
    ui_tag = ctx.get("ui_selected_tag") or ctx.get("current_equipment")
    if ui_tag:
        tag = str(ui_tag).upper()
        return (
            tag,
            ResolutionMetadata(source=ResolutionSource.UI_CONTEXT, confidence=ResolutionConfidence.HIGH, candidate_tags=[tag]),
            False,
            None
        )

    # Tier 3: Conversation Context
    conv_tag = ctx.get("last_mentioned_tag") or ctx.get("previous_equipment")
    if not conv_tag and "conversation_history" in ctx and isinstance(ctx["conversation_history"], list):
        conv_tag = _extract_tag_from_history(ctx["conversation_history"])

    if conv_tag:
        tag = str(conv_tag).upper()
        return (
            tag,
            ResolutionMetadata(source=ResolutionSource.CONVERSATION_CONTEXT, confidence=ResolutionConfidence.HIGH, candidate_tags=[tag]),
            False,
            None
        )

    # Tier 4: Category Keyword Inference (e.g. "pump" -> GA-1201A, "dryer" -> YD-2301)
    q_lower = query.lower()
    inferred_candidates = []
    for tag, info in PLANT_EQUIPMENT_REGISTRY.items():
        # Find key category nouns (length >= 3, skipping suffixes like 'A', 'B', '(Standby)')
        words = [w.strip("().") for w in info["name"].lower().split() if len(w.strip("().")) >= 3]
        category_noun = words[-1] if words else ""
        if category_noun and re.search(r"\b" + re.escape(category_noun) + r"\b", q_lower):
            inferred_candidates.append(tag)

    if len(inferred_candidates) == 1:
        tag = inferred_candidates[0]
        return (
            tag,
            ResolutionMetadata(source=ResolutionSource.INFERRED, confidence=ResolutionConfidence.MEDIUM, candidate_tags=[tag]),
            False,
            None
        )
    elif len(inferred_candidates) > 1:
        return (
            None,
            ResolutionMetadata(source=ResolutionSource.INFERRED, confidence=ResolutionConfidence.LOW, candidate_tags=inferred_candidates),
            True,
            f"Multiple equipment candidates match your description: {', '.join(inferred_candidates)}. Please specify the exact tag."
        )

    # Tier 5: None / Unknown
    return (
        None,
        ResolutionMetadata(source=ResolutionSource.NONE, confidence=ResolutionConfidence.NONE, candidate_tags=[]),
        True,
        "No equipment tag specified. Please mention the target equipment tag (e.g. GA-1201A)."
    )
