import os
import re
import pickle
import frontmatter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import numpy as np
import faiss


class C64KnowledgeBase:
    SKIP_EXTS = {
        ".gz",
        ".gzip",
        ".zip",
        ".png",
        ".jpg",
        ".gif",
        ".pdf",
        ".d64",
        ".g64",
        ".prg",
    }

    def __init__(self, kb_path="knowledge_base", db_path="data/vectorstore"):
        self.kb_path = kb_path
        self.db_path = db_path
        self._load_embedder()
        self.vectorstore = None
        self.docstore = []
        self.reranker = None
        self.rerank_k = 30
        self.use_reranker = True

    def _load_embedder(self):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self._dim = 384

    def build_index(self):
        import time as _time
        # Ensure the real path of kb_path is a directory, not a file.
        # This handles cases where kb_path is a symlink (broken or valid).
        real_kb_path = os.path.realpath(self.kb_path)
        if os.path.exists(real_kb_path) and not os.path.isdir(real_kb_path):
            os.remove(real_kb_path)
        _t0 = _time.time()
        if not os.path.exists(real_kb_path):
            os.makedirs(real_kb_path, exist_ok=True)

        if not os.listdir(real_kb_path):
            with open(os.path.join(real_kb_path, "c64_memory_map.md"), "w") as f:
                f.write(
                    "# C64 Memory Map\n\n$D020: Border Color\n$D021: Background Color\n$0400-$07E7: Screen Memory\n"
                )

        documents = []

        print(f"  [{_time.time() - _t0:.1f}s] KB markdown...", flush=True)
        kb_walk_paths = []
        if self.kb_path:
            kb_walk_paths.append(os.path.realpath(self.kb_path))
        if os.path.exists("data/kb"):
            abs_kb = os.path.realpath("data/kb")
            if abs_kb not in kb_walk_paths:
                kb_walk_paths.append(abs_kb)

        for walk_path in kb_walk_paths:
            for root, _, files in os.walk(walk_path):
                for fname in files:
                    if not fname.endswith(".md"):
                        continue
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            post = frontmatter.load(f)
                        content = f"Source: {fname}\n\n" + post.content
                        if post.metadata:
                            tags = post.metadata.get("tags", [])
                            if isinstance(tags, list):
                                content += "\nTags: " + ", ".join(str(t) for t in tags)
                            elif isinstance(tags, str):
                                content += "\nTags: " + tags
                        documents.append(
                            Document(
                                page_content=content,
                                metadata={"source": path, **post.metadata},
                            )
                        )
                    except Exception as e:
                        print(f"  Skipping {path}: {e}")

        print(f"  [{_time.time() - _t0:.1f}s] PDF outputs...", flush=True)
        if not os.environ.get("SKIP_PDF"):
            self._include_pdf_outputs(documents)

        print(f"  [{_time.time() - _t0:.1f}s] docs/...", flush=True)
        if os.path.exists("docs"):
            for root, _, files in os.walk("docs"):
                for fname in files:
                    if fname.endswith(".md"):
                        path = os.path.join(root, fname)
                        try:
                            with open(path, encoding="utf-8", errors="replace") as f:
                                post = frontmatter.load(f)
                            content = post.content
                            content = f"Internal Document: {fname}\n\n" + content
                            if post.metadata:
                                content += "\nMetadata: " + str(post.metadata)
                            documents.append(
                                Document(
                                    page_content=content,
                                    metadata={"source": path, **post.metadata},
                                )
                            )
                        except Exception as e:
                            print(f"  Skipping {path}: {e}")

        print(f"  [{_time.time() - _t0:.1f}s] data/input + data/src...", flush=True)
        for dirname in ["data/input", "data/src"]:
            if os.path.exists(dirname):
                for root, _, files in os.walk(dirname):
                    for fname in files:
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in self.SKIP_EXTS:
                            continue
                        if not (fname.endswith((".bas.txt", ".ml.txt", ".asm"))):
                            continue
                        path = os.path.join(root, fname)
                        sz = os.path.getsize(path)
                        if fname.endswith(".asm") and sz > 500 * 1024:
                            continue
                        if fname.endswith(".asm") and re.search(
                            r"\.(pdf|html|htm|png|jpg|jpeg|gif|zip|gz|lzh|jed|vhd|ucf|sch|brd)(?:_[a-f0-9]+)?\.asm$",
                            fname,
                        ):
                            continue
                        try:
                            with open(path, encoding="utf-8", errors="replace") as f:
                                content = f.read()
                            label = (
                                "Source Code"
                                if ".asm" in fname
                                else f"Source Code: {fname}"
                            )
                            content = f"{label}\n\n{content}"
                            documents.append(
                                Document(
                                    page_content=content, metadata={"source": path}
                                )
                            )
                        except Exception as e:
                            print(f"  Skipping {fname}: {e}")

        print(
            f"  [{_time.time() - _t0:.1f}s] {len(documents)} docs, splitting...",
            flush=True,
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000, chunk_overlap=200, separators=["\n\n", "\n", ".", " ", ""]
        )
        docs = text_splitter.split_documents(documents)
        print(
            f"  [{_time.time() - _t0:.1f}s] {len(docs)} chunks, embedding...",
            flush=True,
        )

        texts = [d.page_content for d in docs]
        metadatas = [d.metadata for d in docs]

        batch_size = 512
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            emb = self._model.encode(batch, show_progress_bar=False)
            all_embeddings.append(emb)
            elapsed = _time.time() - _t0
            print(
                f"  [{elapsed:.0f}s] embed batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}",
                flush=True,
            )

        if len(all_embeddings) == 1:
            embeddings = all_embeddings[0]
        else:
            embeddings = np.concatenate(all_embeddings, axis=0)

        print(
            f"  [{_time.time() - _t0:.1f}s] embeddings {embeddings.shape}, building FAISS...",
            flush=True,
        )
        index = faiss.IndexFlatL2(self._dim)
        index.add(embeddings.astype(np.float32))

        print(f"  [{_time.time() - _t0:.1f}s] saving...", flush=True)
        os.makedirs(self.db_path, exist_ok=True)
        faiss.write_index(index, os.path.join(self.db_path, "index.faiss"))
        with open(os.path.join(self.db_path, "docstore.pkl"), "wb") as f:
            pickle.dump({"texts": texts, "metadatas": metadatas}, f)
        print(
            f"  [{_time.time() - _t0:.1f}s] Index built with {len(docs)} chunks.",
            flush=True,
        )

    def load_index(self):
        faiss_path = os.path.join(self.db_path, "index.faiss")
        pkl_path = os.path.join(self.db_path, "docstore.pkl")
        if os.path.exists(faiss_path) and os.path.exists(pkl_path):
            self.index = faiss.read_index(faiss_path)
            with open(pkl_path, "rb") as f:
                data = pickle.load(f)
            self.docstore = data["texts"]
            self.docstore_meta = data["metadatas"]
        else:
            print("Index not found. Building it...")
            self.build_index()
            self.load_index()

    def _load_reranker(self):
        try:
            from sentence_transformers import CrossEncoder

            self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except ImportError:
            print(
                "sentence-transformers CrossEncoder not available; disabling reranker."
            )
            self.use_reranker = False

    def _include_pdf_outputs(self, documents):
        output_dir = "data/output"
        if not os.path.exists(output_dir):
            return

        TECH_KEYWORDS = [
            "lda",
            "sta",
            "ldx",
            "stx",
            "jsr",
            "rts",
            "poke",
            "peek",
            "$d020",
            "$d021",
            "$d000",
            "vic",
            "sid",
            "raster",
            "6502",
            "6510",
            "sprite",
            "kernal",
            "cia",
            "assembler",
            "codice macchina",
            "linguaggio macchina",
            "opcode",
            "mnemonico",
            "accumulatore",
            "programmer",
            "reference",
            "programmazione",
        ]

        for fname in sorted(os.listdir(output_dir)):
            path = os.path.join(output_dir, fname)
            sz = os.path.getsize(path)

            if fname.endswith(".md"):
                if sz < 512:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    content_lower = content.lower()
                    keyword_count = sum(
                        1 for kw in TECH_KEYWORDS if kw in content_lower
                    )
                    if keyword_count < 15:
                        continue
                    labeled = f"Source: {fname}\n\n{content}"
                    documents.append(
                        Document(
                            page_content=labeled,
                            metadata={"source": path, "type": "marker_md"},
                        )
                    )
                    print(f"  Incluso (marker): {fname} ({keyword_count} keyword)")
                except Exception as e:
                    print(f"  Skipping {fname}: {e}")
                continue

            if fname.endswith("_clean.txt"):
                if sz < 1024:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    content_lower = content.lower()
                    keyword_count = sum(
                        1 for kw in TECH_KEYWORDS if kw in content_lower
                    )
                    if keyword_count < 15:
                        continue
                    labeled = f"Source: {fname}\n\n{content}"
                    documents.append(
                        Document(
                            page_content=labeled,
                            metadata={"source": path, "type": "pdf_manual"},
                        )
                    )
                    print(f"  Incluso: {fname} ({keyword_count} keyword tecniche)")
                except Exception as e:
                    print(f"  Skipping {fname}: {e}")

    def _source_boost(self, source):
        source = source or ""
        if "knowledge_base/" in source:
            return 3.0
        if "data/src/" in source:
            return 2.0
        if "docs/" in source:
            return 1.5
        if source and (source.endswith(".md") or "marker_md" in str(source)):
            return 1.2
        if "data/output/" in source:
            return 0.3
        return 1.0

    def query(self, text, k=10, follow_links=True):
        if not hasattr(self, "index"):
            self.load_index()

        fetch_k = min(k * 6, len(self.docstore))
        emb = self._model.encode([text])
        scores, idxs = self.index.search(emb.astype(np.float32), fetch_k)

        scored = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0:
                continue
            src = self.docstore_meta[idx].get("source", "")
            boost = self._source_boost(src)
            scored.append((score * boost, idx))

        scored.sort(key=lambda x: -x[0])

        try:
            if self.use_reranker:
                if self.reranker is None:
                    self._load_reranker()
                if self.reranker is not None:
                    rerank_n = min(self.rerank_k, len(scored))
                    candidates = scored[:rerank_n]
                    pairs = [(text, self.docstore[idx]) for _, idx in candidates]
                    rerank_scores = self.reranker.predict(pairs)
                    reranked = sorted(
                        zip(rerank_scores, [idx for _, idx in candidates]),
                        key=lambda x: -x[0],
                    )
                    scored = [
                        (
                            rs
                            * self._source_boost(
                                self.docstore_meta[idx].get("source", "")
                            ),
                            idx,
                        )
                        for rs, idx in reranked
                    ]
        except Exception as e:
            print(f"Reranker failed, falling back to FAISS scoring: {e}")

        scored.sort(key=lambda x: -x[0])
        results = []
        for _, idx in scored[:k]:
            results.append(
                Document(
                    page_content=self.docstore[idx],
                    metadata=self.docstore_meta[idx],
                )
            )

        # Follow Obsidian links
        if follow_links:
            seen = set()
            for doc in list(results):
                links = re.findall(r"\[\[(.*?)\]\]", doc.page_content)
                for link in links[:2]:
                    if link in seen:
                        continue
                    seen.add(link)
                    emb2 = self._model.encode([link])
                    s2, i2 = self.index.search(emb2.astype(np.float32), 1)
                    if i2[0][0] >= 0:
                        results.append(
                            Document(
                                page_content=self.docstore[i2[0][0]],
                                metadata=self.docstore_meta[i2[0][0]],
                            )
                        )

        return results


if __name__ == "__main__":
    kb = C64KnowledgeBase()
    kb.build_index()
    results = kb.query("What is at $D020?")
    for res in results:
        print(f"Found: {res.page_content[:200]}")
