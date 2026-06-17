
import os
import sys
from agent.researcher import ResearcherAgent

class MockBackend:
    def generate(self, prompt, **kwargs):
        # Semplice mock che restituisce termini tecnici basati sul prompt
        prompt_lower = prompt.lower()
        # Expansion: system prompt usually mentions "registri", "chip", "opcode" or "espandi"
        if any(x in prompt_lower for x in ["expand", "espandere", "registri", "chip", "expansion"]):
            if "border" in prompt_lower or "bordo" in prompt_lower:
                return "C64 memory map border color $D020"
            if "cia" in prompt_lower:
                return "MOS 6526 CIA registers $DC00 $DD00"
            return "C64 technical details"
        if "language_detection" in prompt_lower or "rilevamento linguaggio" in prompt_lower:
            return "assembly"
        # HyDE: system prompt usually mentions "paragrafo tecnico" or "esperto"
        if any(x in prompt_lower for x in ["hyde", "paragrafo", "hypothetical"]):
            if "border" in prompt_lower or "bordo" in prompt_lower:
                return "The border color in C64 is controlled by register $D020."
            if "cia" in prompt_lower:
                return "The CIA chips (6526) at $DC00 and $DD00 handle I/O."
        return "C64 technical info"

def test_rag_qna():
    print("Initializing ResearcherAgent with MockBackend...")
    mock_backend = MockBackend()
    researcher = ResearcherAgent(model=mock_backend)

    queries = [
        ("How do I change the border color?", "English"),
        ("Come cambio il colore del bordo?", "Italian"),
        ("What are the CIA registers?", "English"),
        ("Quali sono i registri CIA?", "Italian")
    ]

    for query, lang in queries:
        print(f"\n--- Testing Query ({lang}): {query} ---")
        # Increasing k to 10 for testing to find info in a dense index
        # We simulate the researcher calling kb.query with k=10
        expanded_query = researcher.expand_query(query)
        docs = researcher.kb.query(expanded_query, k=10)
        context = "\n".join([d.page_content for r in docs for d in (r if isinstance(r, list) else [r])])
        print("Retrieved Context Fragment:")
        # Print first 200 chars of context for brevity
        print(context[:500] + "...")

        # Verification
        if "border" in query.lower() or "bordo" in query.lower():
            if "$D020" in context:
                print("SUCCESS: Found $D020 in context.")
            else:
                print("FAILURE: $D020 not found in context.")

        if "cia" in query.lower():
            if "$DC00" in context or "$DD00" in context or "6526" in context:
                print("SUCCESS: Found CIA technical details in context.")
            else:
                print("FAILURE: CIA technical details not found in context.")

if __name__ == "__main__":
    test_rag_qna()
