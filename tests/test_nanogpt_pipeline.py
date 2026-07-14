import os
import unittest
from pathlib import Path
from pipeline.nanogpt_prepper import NanoGPTPrepper
from pipeline.nanogpt_trainer import NanoGPTTrainer
from agent.model_backend import NanoGPTBackend

class TestNanoGPTPipeline(unittest.TestCase):
    def setUp(self):
        self.output_dir = "data/test_nanogpt_output"
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_prepper_custom_bpe(self):
        prepper = NanoGPTPrepper(output_dir=self.output_dir)
        text = "LDA #$01 STA $D020 JSR $FFD2 <|endoftext|> POKE 53280, 0"

        ids, vocab_size = prepper.tokenize_custom_bpe(text)
        self.assertGreater(vocab_size, 0)
        self.assertGreater(len(ids), 0)

        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "tokenizer_c64.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "meta.pkl")))

    def test_trainer_resume_config(self):
        trainer = NanoGPTTrainer(data_dir=self.output_dir, output_dir=self.output_dir)
        config_text = trainer.write_config(
            model_size="124M",
            init_from="resume",
            batch_size=4,
            max_iters=100
        )
        self.assertIn("init_from = 'resume'", config_text)
        self.assertIn("batch_size = 4", config_text)
        self.assertIn("max_iters = 100", config_text)

    def test_nanogpt_backend_fallback(self):
        backend = NanoGPTBackend(model_path="data/models/non_existent.pt")
        response = backend.generate("test prompt")
        self.assertIn("simulato dal backend nanoGPT", response)
        self.assertIn("Prompt ricevuto: test prompt", response)
