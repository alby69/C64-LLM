
import os
from agent.knowledge_base import C64KnowledgeBase

def list_sources():
    kb = C64KnowledgeBase()
    kb.load_index()

    # Accessing internal FAISS/LangChain documents is tricky,
    # but we can try to get them if we have the documents or just query for everything.
    # Since we can't easily list all docs from FAISS without the original docs,
    # let's just check the files we EXPECT to be there.

    expected_files = []
    for root, _, files in os.walk("knowledge_base"):
        for f in files:
            if f.endswith(".md"):
                expected_files.append(os.path.join(root, f))

    for root, _, files in os.walk("docs"):
        for f in files:
            if f.endswith(".md"):
                expected_files.append(os.path.join(root, f))

    for root, _, files in os.walk("data/output"):
        for f in files:
            if f.endswith(".txt"):
                expected_files.append(os.path.join(root, f))

    print(f"Total expected source files: {len(expected_files)}")

    for f in expected_files:
        # Try to query for something specific from this file
        results = kb.query(f"source:{f}", k=1)
        # This might not work as expected because "source:path" isn't a special syntax in FAISS
        # unless it was indexed that way.

        # Let's just do a similarity search for the filename
        results = kb.vectorstore.similarity_search(os.path.basename(f), k=1)
        if results and os.path.basename(f).lower() in results[0].metadata.get('source', '').lower():
            print(f"[OK] {f} seems to be indexed.")
        else:
            print(f"[??] {f} might be missing or not top result for its own name.")

if __name__ == "__main__":
    list_sources()
