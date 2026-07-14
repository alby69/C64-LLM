import os
import sys
import time
import logging
import argparse
from pathlib import Path

# Set up logging
logger = logging.getLogger("nanoGPT_Eval")
logging.basicConfig(level=logging.INFO)

# Standard C64 evaluation queries
EVAL_QUERIES = [
    {
        "id": "basic_border",
        "category": "BASIC",
        "query": "Scrivi una riga in BASIC V2 per impostare il colore del bordo a nero.",
        "expected_keywords": ["POKE", "53280", "0"]
    },
    {
        "id": "assembly_delay",
        "category": "Assembly",
        "query": "Scrivi un ciclo di ritardo (delay loop) in Assembly 6502 usando i registri X e Y.",
        "expected_keywords": ["LDX", "LDY", "DEX", "DEY", "BNE"]
    },
    {
        "id": "raster_interrupt",
        "category": "Interrupt",
        "query": "Come si configura un raster interrupt a riga 100 in Assembly 6502?",
        "expected_keywords": ["$D012", "$D01A", "0314", "RTI"]
    }
]


def evaluate_backend(backend_name, backend_instance, queries):
    """
    Evaluates a specific model backend on the standard queries.
    """
    logger.info(f"Avvio valutazione per il backend: {backend_name}")
    results = []

    for q in queries:
        query_text = q["query"]
        logger.info(f"Query [{q['id']}]: '{query_text}'")

        start_time = time.time()

        # Generation
        try:
            generated_text = backend_instance.generate(
                query_text,
                max_new_tokens=256,
                temperature=0.3
            )
        except Exception as e:
            logger.error(f"Errore durante la generazione: {e}")
            generated_text = f"ERRORE: {e}"

        elapsed = time.time() - start_time

        # Estimate token count (roughly 1 token = 4 chars for English/code)
        estimated_tokens = len(generated_text) / 4.0
        tokens_per_sec = estimated_tokens / elapsed if elapsed > 0 else 0.0

        # Check syntactic and keyword coverage
        passed_keywords = [kw for kw in q["expected_keywords"] if kw.lower() in generated_text.lower()]
        coverage_score = len(passed_keywords) / len(q["expected_keywords"])

        results.append({
            "query_id": q["id"],
            "category": q["category"],
            "elapsed_sec": round(elapsed, 3),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "coverage_score": round(coverage_score * 100, 1),
            "passed_keywords": passed_keywords,
            "response_preview": generated_text[:60].replace("\n", " ") + "..."
        })

    return results


def print_comparison_table(all_results):
    """
    Prints a beautiful CLI table comparing the evaluated backends.
    """
    print("\n" + "=" * 100)
    print("       RISULTATI DELLA VALUTAZIONE COMPARATIVA DEI BACKEND (C64-LLM)")
    print("=" * 100)

    header = f"{'Backend':20s} | {'Query ID':15s} | {'Tempo (s)':10s} | {'Velocità (tok/s)':18s} | {'Aderenza Sintassi (%)':22s}"
    print(header)
    print("-" * 100)

    for backend, results in all_results.items():
        for res in results:
            row = (
                f"{backend:20s} | "
                f"{res['query_id']:15s} | "
                f"{res['elapsed_sec']:10.3f} | "
                f"{res['tokens_per_sec']:18.2f} | "
                f"{res['coverage_score']:22.1f}%"
            )
            print(row)

    print("=" * 100)


def main():
    parser = argparse.ArgumentParser(description="Script di valutazione comparativa e benchmark per i backend C64-LLM")
    parser.add_argument("--backend", default="all", choices=["qwen", "nanogpt", "all"], help="Backend da testare")
    parser.add_argument("--model-path", default="data/models/c64-micron.pt", help="Percorso checkpoint nanoGPT")

    args = parser.parse_args()

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from agent.model_backend import LlamaCppBackend, NanoGPTBackend

    backends_to_test = {}

    if args.backend in ["qwen", "all"]:
        # Mock/simulated Qwen or base llama.cpp model
        logger.info("Inizializzazione backend Qwen/Llama.cpp (Mock/Simulated)...")
        backends_to_test["Qwen-1.5B (GGUF)"] = LlamaCppBackend("data/models/qwen.Q4_K_M.gguf")

    if args.backend in ["nanogpt", "all"]:
        logger.info("Inizializzazione backend nanoGPT (Locale)...")
        backends_to_test["nanoGPT (Custom)"] = NanoGPTBackend(args.model_path)

    all_results = {}

    for name, b_instance in backends_to_test.items():
        all_results[name] = evaluate_backend(name, b_instance, EVAL_QUERIES)

    print_comparison_table(all_results)


if __name__ == "__main__":
    main()
