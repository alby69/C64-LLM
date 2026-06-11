import os
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

        # Markdown
        if any(f.endswith(".md") for f in os.listdir(self.kb_path)):
            loader_md = DirectoryLoader(self.kb_path, glob="**/*.md", loader_cls=TextLoader)
            documents.extend(loader_md.load())

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

    def query(self, text, k=3):
        if not self.vectorstore:
            self.load_index()
        docs = self.vectorstore.similarity_search(text, k=k)
        return docs

if __name__ == "__main__":
    kb = C64KnowledgeBase()
    kb.build_index()
    results = kb.query("What is at $D020?")
    for res in results:
        print(f"Found: {res.page_content}")
