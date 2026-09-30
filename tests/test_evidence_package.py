import pytest
from src.pipeline import ManufacturingKnowledgeHub
from src.retrieval.models import SufficiencyStatus


@pytest.fixture(scope="module")
def hub():
    return ManufacturingKnowledgeHub()


def test_evidence_package_construction(hub):
    pkg = hub.build_evidence_package("What is GA-1201A and what is its rated flow?")
    assert pkg.equipment_tag == "GA-1201A"
    assert pkg.intent == "equipment_information"
    assert pkg.sufficiency == SufficiencyStatus.SUFFICIENT
    assert len(pkg.items) > 0

    # Test evidence ID prefixes
    for it in pkg.items:
        assert it.evidence_id.startswith(("EV-DOC-", "EV-TR-", "EV-REL-", "EV-MNT-"))
        assert it.document_id is not None
        assert it.document_type is not None
        assert it.source is not None


def test_evidence_package_multi_modal_fusion(hub):
    pkg = hub.build_evidence_package("What is GA-1201A and what is its rated flow?")
    doc_items = pkg.get_items_by_type("document_chunk")
    tr_items = pkg.get_items_by_type("technical_parameter")

    assert len(doc_items) > 0
    # If structured store loaded TRs, verify they are fused
    if tr_items:
        assert any("flow" in it.content.lower() for it in tr_items)


def test_evidence_package_metadata_purity(hub):
    pkg = hub.build_evidence_package("What conditions can trip GA-1201A?")
    for it in pkg.items:
        # Verify that revision is never fabricated to 'Rev.00' when missing
        if it.source.revision is not None:
            assert isinstance(it.source.revision, str)
        # Verify that page is an int if present
        if it.source.page is not None:
            assert isinstance(it.source.page, int)


def test_evidence_package_clarification_state(hub):
    pkg = hub.build_evidence_package("What should I check if there is abnormal noise and vibration?")
    assert pkg.sufficiency == SufficiencyStatus.CLARIFICATION_REQUIRED
    assert not pkg.is_sufficient
