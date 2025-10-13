# scripts/process_docs.py
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

PDF_FILE_PATH = os.path.join('data', 'quarterly_report.pdf')
FAISS_INDEX_PATH = os.path.join('data', 'faiss_index')

def main():
    if not os.path.exists(PDF_FILE_PATH):
        print(f"PDF file not found at {PDF_FILE_PATH}. Please add it.")
        return

    print("--- Starting Document Processing ---")

    print(f"Loading document: {PDF_FILE_PATH}")
    loader = PyPDFLoader(PDF_FILE_PATH)
    documents = loader.load()

    print("Splitting document into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_documents(documents)

    print("Loading local embedding model (will download if it's the first time)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print("Creating FAISS vector store...")
    db = FAISS.from_documents(docs, embeddings)

    print(f"Saving FAISS index to: {FAISS_INDEX_PATH}")
    db.save_local(FAISS_INDEX_PATH)

    print("--- ✅ Document Processing Complete ---")

if __name__ == "__main__":
    main()
