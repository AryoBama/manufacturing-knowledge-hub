import pytest
from src.adapters.llm import (
    LLMAdapter,
    DeepSeekAdapter,
    GeminiAdapter,
    OpenAIAdapter,
    OfflineMockAdapter,
    get_llm_adapter,
)
from src.query.llm_intent_classifier import LLMIntentClassifier
from src.generation.llm_adapter import LLMAnswerAdapter
from src.generation.evidence import EvidencePackage
from src.retrieval.models import SufficiencyStatus


class DummyTestAdapter(LLMAdapter):
    """Custom mock adapter for unit tests."""
    def complete(self, prompt: str, system_prompt: str = "", json_mode: bool = False, temperature: float = 0.0) -> str:
        if json_mode:
            return '{"intent": "troubleshooting", "confidence": "HIGH", "reason_code": "test_mock"}'
        return "Grounded test response from mock adapter."


def test_offline_mock_adapter():
    adapter = OfflineMockAdapter()
    text = adapter.complete("test query")
    assert "offline" in text.lower()

    json_text = adapter.complete("test query", json_mode=True)
    assert "general_information" in json_text


def test_factory_returns_mock_when_offline(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    adapter = get_llm_adapter("deepseek")
    assert isinstance(adapter, OfflineMockAdapter)


def test_factory_returns_deepseek_when_configured(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "false")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-deepseek-key")
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    adapter = get_llm_adapter()
    assert isinstance(adapter, DeepSeekAdapter)
    assert adapter.model == "deepseek-chat"


def test_intent_classifier_with_injected_adapter():
    dummy = DummyTestAdapter()
    classifier = LLMIntentClassifier(adapter=dummy)
    res = classifier.classify("Random question about equipment")
    assert res.intent == "troubleshooting"
    assert res.confidence == "HIGH"
    assert res.reason_code == "test_mock"


def test_answer_adapter_with_injected_adapter():
    dummy = DummyTestAdapter()
    ans_adapter = LLMAnswerAdapter(adapter=dummy)
    pkg = EvidencePackage(
        query="What is the rated flow?",
        equipment_tag="GA-1201A",
        intent="equipment_information",
        sufficiency=SufficiencyStatus.SUFFICIENT,
        sufficiency_reason="Valid datasheet evidence located",
    )
    ans = ans_adapter.generate(pkg)
    assert ans.summary_answer == "Grounded test response from mock adapter."
