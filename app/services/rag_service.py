# app/services/rag_service.py
import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

_retriever = None

def process_and_load_pdf(pdf_file_path: str):
    global _retriever
    print(f"--- Starting processing for: {pdf_file_path} ---")
    loader = PyPDFLoader(pdf_file_path)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(docs, embeddings)
    _retriever = db.as_retriever()
    print("--- ✅ PDF processed and retriever is ready ---")

def query_rag(question: str) -> str:
    """Queries the currently active FAISS retriever and returns ONLY the context."""
    global _retriever
    if _retriever is None:
        return "No document has been uploaded and processed yet. Please upload a PDF first."

    docs = _retriever.invoke(question)
    # Return only the joined page content
    return "\n---\n".join([doc.page_content for doc in docs])