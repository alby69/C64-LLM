import os
import frontmatter
from langchain_core.documents import Document
from agent.data/kb/manuali import C64KnowledgeBase

class EcosystemKnowledgeBase(C64KnowledgeBase):
    """
    Estensione della Knowledge Base per supportare percorsi multipli
    dall'ecosistema C64 Intelligence SDK.
    """

    def __init__(self, kb_path="data/kb/manuali", db_path="data/db/faiss", extra_paths=None):
        super().__init__(kb_path, db_path)
        self.extra_paths = extra_paths or []
        # Aggiunge automaticamente la cartella tutorial se presente (Docker/Submodule)
        if os.path.exists("/app/tutorial"):
            self.extra_paths.append("/app/tutorial")

    def build_index(self):
        # Chiama il build standard
        super().build_index()

        # Aggiunge i documenti dai percorsi extra
        documents = []
        for path in self.extra_paths:
            if os.path.exists(path):
                print(f"Indicizzazione percorso extra: {path}")
                self._index_directory(path, documents)

        # Qui andrebbe la logica per aggiornare l'indice FAISS con i nuovi documenti
        # Per brevità in questo esempio, mostriamo solo come raccoglierli.
        print(f"Raccolti {len(documents)} documenti extra dall'ecosistema.")

    def _index_directory(self, directory, documents):
        for root, _, files in os.walk(directory):
            for fname in files:
                if fname.endswith((".md", ".asm", ".bas")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            if fname.endswith(".md"):
                                post = frontmatter.load(f)
                                content = post.content
                            else:
                                content = f.read()

                        documents.append(Document(
                            page_content=f"Ecosystem Knowledge ({fname}):\n\n{content}",
                            metadata={"source": fpath, "ecosystem": True}
                        ))
                    except Exception as e:
                        print(f"Errore extra path {fpath}: {e}")
