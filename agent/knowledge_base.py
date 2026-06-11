import os
import re
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class C64KnowledgeBase:
    def __init__(self, kb_path="knowledge_base", db_path="data/vectorstore"):
        self.kb_path = kb_path
        self.db_path = db_path
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vectorstore = None

    def build_index(self):
        if not os.path.exists(self.kb_path):
            os.makedirs(self.kb_path)

        # Create a sample file if empty
        if not os.listdir(self.kb_path):
            with open(os.path.join(self.kb_path, "c64_memory_map.md"), "w") as f:
                f.write("# C64 Memory Map\n\n$D020: Border Color\n$D021: Background Color\n$0400-$07E7: Screen Memory\n")

        # Carica sia Markdown che i file di testo puliti dalla pipeline
        documents = []

        # Markdown con parsing frontmatter
        for root, _, files in os.walk(self.kb_path):
            for file in files:
                if file.endswith(".md"):
                    path = os.path.join(root, file)
                    with open(path, 'r') as f:
                        post = frontmatter.load(f)
                        # Combiniamo metadati e contenuto per l'indicizzazione
                        content = post.content
                        if post.metadata:
                            tags = post.metadata.get('tags', [])
                            if isinstance(tags, list):
                                content += "\nTags: " + ", ".join(tags)
                            elif isinstance(tags, str):
                                content += "\nTags: " + tags

                        documents.append(Document(page_content=content, metadata={"source": path, **post.metadata}))

        # Cleaned text from pipeline
        clean_txt = "data/output/clean.txt"
        if os.path.exists(clean_txt):
            loader_txt = TextLoader(clean_txt)
            documents.extend(loader_txt.load())

        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)

        self.vectorstore = FAISS.from_documents(docs, self.embeddings)
        self.vectorstore.save_local(self.db_path)
        print(f"Index built with {len(docs)} chunks.")

    def load_index(self):
        if os.path.exists(self.db_path):
            self.vectorstore = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            print("Index not found. Building it...")
            self.build_index()

    def extract_links(self, text):
        """Estrae link in formato Obsidian [[Note Name]]."""
        return re.findall(r'\[\[(.*?)\]\]', text)

    def query(self, text, k=3, follow_links=True):
        if not self.vectorstore:
            self.load_index()

        # Ricerca vettoriale iniziale
        docs = self.vectorstore.similarity_search(text, k=k)

        if not follow_links:
            return docs

        # Navigazione del grafo (semplice): cerca i documenti linkati nei risultati
        all_docs = list(docs)
        linked_queries = []
        for doc in docs:
            links = self.extract_links(doc.page_content)
            linked_queries.extend(links)

        # Se abbiamo trovato dei link, facciamo una ricerca anche per quelli
        # per arricchire il contesto
        for link_query in list(set(linked_queries))[:2]: # Limitiamo a 2 link per non esplodere il contesto
            link_docs = self.vectorstore.similarity_search(link_query, k=1)
            all_docs.extend(link_docs)

        return all_docs

if __name__ == "__main__":
    kb = C64KnowledgeBase()
    kb.build_index()
    results = kb.query("What is at $D020?")
    for res in results:
        print(f"Found: {res.page_content}")
