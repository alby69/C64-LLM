import os
import re
import sys
import pickle
import json
import logging
from pathlib import Path
import numpy as np

# Set up logging
logger = logging.getLogger("nanoGPT_Prepper")
logging.basicConfig(level=logging.INFO)

class NanoGPTPrepper:
    """
    Prepares and pre-tokenizes the Commodore 64 Knowledge Base
    for pre-training or fine-tuning with Andrej Karpathy's nanoGPT.
    Supports both BPE (GPT-2 tiktoken) and Character-level tokenization.
    """

    def __init__(self, output_dir="data/nanogpt_c64", val_ratio=0.1):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.val_ratio = val_ratio

    def gather_c64_corpus(self):
        """
        Scans all source directories in C64-LLM and compiles
        a unified text corpus.
        """
        logger.info("Gathering text corpus from C64 Knowledge Base sources...")
        corpus_parts = []

        # 1. Scan markdown files in knowledge_base/, data/kb/, and C64-KB-Agent submodule
        kb_paths = [
            Path("knowledge_base"),
            Path("data/kb"),
            Path("docs"),
            Path("C64-KB-Agent/data/docs"),
            Path("C64-KB-Agent/knowledge_base")
        ]
        for kb_path in kb_paths:
            if kb_path.exists():
                logger.info(f"Scanning markdown files in: {kb_path}")
                for md_file in kb_path.glob("**/*.md"):
                    try:
                        with open(md_file, 'r', encoding='utf-8', errors='replace') as f:
                            text = f.read()
                        # Add document boundary marker (standard GPT-2 endoftext token representation)
                        corpus_parts.append(f"\n\n--- DOCUMENT: {md_file.name} ---\n\n{text}\n<|endoftext|>\n")
                    except Exception as e:
                        logger.error(f"Error reading {md_file}: {e}")

        # 2. Scan source code files (.asm, .bas, .txt) in data/src/ and data/input/
        code_paths = [Path("data/src"), Path("data/input")]
        for code_path in code_paths:
            if code_path.exists():
                logger.info(f"Scanning code files in: {code_path}")
                for code_file in code_path.glob("**/*"):
                    if code_file.suffix.lower() in [".asm", ".bas", ".txt"]:
                        try:
                            with open(code_file, 'r', encoding='utf-8', errors='replace') as f:
                                text = f.read()
                            corpus_parts.append(f"\n\n--- SOURCE: {code_file.name} ---\n\n{text}\n<|endoftext|>\n")
                        except Exception as e:
                            logger.error(f"Error reading {code_file}: {e}")

        # 3. Incorporate generated QA distillation dataset (if present)
        distill_file = Path("data/output/distill_dataset.jsonl")
        if distill_file.exists():
            logger.info(f"Adding synthetic QA pairs from: {distill_file}")
            try:
                qa_count = 0
                with open(distill_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            inst = data.get("instruction", "")
                            ctx = data.get("context", "")
                            out = data.get("output", "")
                            qa_text = f"\nUser: {inst}\nContext: {ctx}\nAssistant: {out}\n<|endoftext|>\n"
                            corpus_parts.append(qa_text)
                            qa_count += 1
                logger.info(f"Successfully integrated {qa_count} QA pairs.")
            except Exception as e:
                logger.error(f"Error parsing distillation file: {e}")

        unified_corpus = "".join(corpus_parts)
        logger.info(f"Corpus compiled. Total length: {len(unified_corpus)} characters.")
        return unified_corpus

    def tokenize_char(self, text):
        """
        Character-level tokenization (ideal for small custom GPT models
        trained from scratch with nanoGPT - shakespeare_char style).
        """
        logger.info("Using character-level tokenization...")
        chars = sorted(list(set(text)))
        vocab_size = len(chars)
        logger.info(f"Character vocabulary size: {vocab_size}")
        logger.info(f"Unique characters: {''.join(repr(c) for c in chars[:50])} ...")

        # Create mapping dictionaries
        char_to_int = {ch: i for i, ch in enumerate(chars)}
        int_to_char = {i: ch for i, ch in enumerate(chars)}

        def encode(s):
            return [char_to_int[c] for c in s]

        # Save metadata pickle file for nanoGPT decoding
        meta = {
            'vocab_size': vocab_size,
            'itos': int_to_char,
            'stoi': char_to_int,
        }
        meta_path = self.output_dir / "meta.pkl"
        with open(meta_path, 'wb') as f:
            pickle.dump(meta, f)
        logger.info(f"Saved character metadata to {meta_path}")

        # Tokenize entire corpus
        ids = encode(text)
        return ids, vocab_size

    def tokenize_bpe(self, text, model_type="gpt2"):
        """
        Byte-Pair Encoding (BPE) tokenization using tiktoken (GPT-2 style).
        """
        logger.info(f"Using BPE tokenization ({model_type})...")
        try:
            import tiktoken
        except ImportError:
            logger.warning("tiktoken package not installed. Installing tiktoken now...")
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "tiktoken"], check=True)
            import tiktoken

        enc = tiktoken.get_encoding(model_type)
        # We can encode with or without handling special tokens
        ids = enc.encode_ordinary(text)
        vocab_size = enc.n_vocab
        logger.info(f"BPE tokenization complete. Total tokens: {len(ids)}. Vocab size: {vocab_size}")
        return ids, vocab_size

    def prepare(self, tokenization_mode="gpt2"):
        """
        Runs the full pipeline to generate train.bin and val.bin.
        """
        corpus = self.gather_c64_corpus()
        if not corpus:
            logger.error("Empty corpus. Cannot proceed with nanoGPT preparation.")
            return False

        if tokenization_mode == "char":
            ids, vocab_size = self.tokenize_char(corpus)
        elif tokenization_mode == "gpt2":
            ids, vocab_size = self.tokenize_bpe(corpus)
        else:
            raise ValueError(f"Unknown tokenization mode: {tokenization_mode}")

        # Split into train/val
        n = len(ids)
        val_size = int(n * self.val_ratio)
        train_ids = ids[:-val_size]
        val_ids = ids[-val_size:]

        logger.info(f"Train set has {len(train_ids)} tokens.")
        logger.info(f"Val set has {len(val_ids)} tokens.")

        # Save to binary files (uint16 is sufficient for GPT-2 vocab size 50257)
        train_bin = np.array(train_ids, dtype=np.uint16)
        val_bin = np.array(val_ids, dtype=np.uint16)

        train_path = self.output_dir / "train.bin"
        val_path = self.output_dir / "val.bin"

        train_bin.tofile(train_path)
        val_bin.tofile(val_path)

        logger.info(f"Saved binary train data to: {train_path}")
        logger.info(f"Saved binary validation data to: {val_path}")

        self.print_nanogpt_instructions(tokenization_mode, vocab_size)
        return True

    def print_nanogpt_instructions(self, mode, vocab_size):
        """Prints copy-pasteable instructions for running Karpathy's nanoGPT."""
        instructions = f"""
======================================================================
🎉 SUCCESS: C64 KNOWLEDGE BASE COMPILED & PRE-TOKENIZED FOR nanoGPT!
======================================================================
Output Directory: {self.output_dir}
Tokenization Mode: {mode}

To train your specialized C64 Language Model using karpathy/nanoGPT:

1. Clone nanoGPT repository:
   $ git clone https://github.com/karpathy/nanoGPT.git
   $ cd nanoGPT

2. Copy the tokenized binary data to nanoGPT:
   $ mkdir -p data/c64_kb
   $ cp {self.output_dir}/* data/c64_kb/

3. Configure and Launch the Training!
"""
        if mode == "char":
            instructions += f"""   Since you used Character-level tokenization (vocab_size={vocab_size}):
   Create a training config (config/train_c64_char.py) or run directly:

   $ python train.py \\
       --dataset=c64_kb \\
       --n_layer=6 \\
       --n_head=6 \\
       --n_embd=384 \\
       --block_size=256 \\
       --batch_size=64 \\
       --learning_rate=1e-3 \\
       --max_iters=5000 \\
       --lr_decay_iters=5000 \\
       --vocab_size={vocab_size}
"""
        else:
            instructions += """   Since you used BPE (gpt2) tokenization:
   You can either fine-tune GPT-2 (124M) weights on C64 knowledge, or pre-train from scratch.

   To FINE-TUNE GPT-2 on C64 KB:
   $ python train.py config/finetune_shakespeare.py --dataset=c64_kb --max_iters=1000

   To PRE-TRAIN from scratch:
   $ python train.py \\
       --dataset=c64_kb \\
       --n_layer=12 \\
       --n_head=12 \\
       --n_embd=768 \\
       --block_size=1024 \\
       --batch_size=12 \\
       --gradient_accumulation_steps=5 \\
       --max_iters=10000
"""
        instructions += "======================================================================"
        print(instructions)

if __name__ == "__main__":
    mode = "gpt2"
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    prepper = NanoGPTPrepper()
    prepper.prepare(tokenization_mode=mode)
