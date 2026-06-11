
import unittest
from unittest.mock import MagicMock
from agent.researcher import ResearcherAgent
from agent.coder import CoderAgent
from agent.validator import ValidatorAgent
from agent.orchestrator import OrchestratorAgent

class TestMultiAgentSystem(unittest.TestCase):
    def setUp(self):
        self.mock_model = MagicMock()
        self.mock_tokenizer = MagicMock()
        self.mock_model.device = "cpu"

    def test_researcher_init(self):
        researcher = ResearcherAgent(self.mock_model, self.mock_tokenizer)
        self.assertIsNotNone(researcher.kb)
        self.assertEqual(researcher.model, self.mock_model)

    def test_coder_init(self):
        coder = CoderAgent(self.mock_model, self.mock_tokenizer)
        self.assertEqual(coder.model, self.mock_model)

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

if __name__ == "__main__":
    unittest.main()
