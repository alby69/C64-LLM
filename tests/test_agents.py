import unittest
from unittest.mock import MagicMock
from agent.researcher import ResearcherAgent
from agent.coder import CoderAgent
from agent.validator import ValidatorAgent
from agent.orchestrator import OrchestratorAgent
from agent.memory_advisor import MemoryAdvisor
from agent.model_backend import BaseModelBackend, ModelBackend, LlamaCppBackend, NanoGPTBackend

class TestMultiAgentSystem(unittest.TestCase):
    def setUp(self):
        self.mock_model = MagicMock()
        self.mock_tokenizer = MagicMock()
        self.mock_model.device = "cpu"

    def test_researcher_init(self):
        researcher = ResearcherAgent()
        self.assertIsNotNone(researcher.kb)

    def test_coder_init(self):
        coder = CoderAgent(self.mock_model, self.mock_tokenizer)
        self.assertIsNotNone(coder.backend)

    def test_validator_basic(self):
        validator = ValidatorAgent()
        # Test BASIC identification (should skip emulator)
        success, msg = validator.validate("```\n10 PRINT \"HELLO\"\n20 GOTO 10\n```")
        self.assertTrue(success)
        self.assertIn("BASIC", msg)

    def test_orchestrator_init(self):
        orchestrator = OrchestratorAgent(self.mock_model, self.mock_tokenizer)
        self.assertIsInstance(orchestrator.researcher, ResearcherAgent)
        self.assertIsInstance(orchestrator.coder, CoderAgent)
        self.assertIsInstance(orchestrator.validator, ValidatorAgent)

    def test_orchestrator_dependency_injection(self):
        mock_researcher = MagicMock()
        mock_coder = MagicMock()
        mock_validator = MagicMock()
        mock_memory_advisor = MagicMock()
        mock_pm = MagicMock()

        orchestrator = OrchestratorAgent(
            researcher=mock_researcher,
            coder=mock_coder,
            validator=mock_validator,
            memory_advisor=mock_memory_advisor,
            pm=mock_pm,
        )

        self.assertEqual(orchestrator.researcher, mock_researcher)
        self.assertEqual(orchestrator.coder, mock_coder)
        self.assertEqual(orchestrator.validator, mock_validator)
        self.assertEqual(orchestrator.memory_advisor, mock_memory_advisor)
        self.assertEqual(orchestrator.pm, mock_pm)

    def test_backend_abc_and_lora_support(self):
        model_backend = ModelBackend(self.mock_model, self.mock_tokenizer)
        self.assertTrue(model_backend.supports_lora)

        llama_backend = LlamaCppBackend(model_path=None)
        self.assertFalse(llama_backend.supports_lora)
        with self.assertRaises(NotImplementedError):
            llama_backend.load_lora("dummy/path")

        nanogpt_backend = NanoGPTBackend(model_path=None)
        self.assertFalse(nanogpt_backend.supports_lora)
        with self.assertRaises(NotImplementedError):
            nanogpt_backend.load_lora("dummy/path")

if __name__ == "__main__":
    unittest.main()
