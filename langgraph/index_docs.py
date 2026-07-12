import os
import time
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from services.model import embedding
from config.setting import DOC_LIMIT, EMBEDDING_BATCH_SIZE

def index_documents(docs_dir, save_path):
    print(f"Loading documents from {docs_dir}...")
    loader = DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    documents = loader.load()
    
    # Read limits from configuration
    doc_limit = DOC_LIMIT
    batch_size = EMBEDDING_BATCH_SIZE
    
    if doc_limit > 0:
        documents = documents[:doc_limit]
        print(f"Limited to {doc_limit} documents.")
    
    print(f"Loaded {len(documents)} documents. Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    
    print(f"Creating FAISS vector store with {len(docs)} chunks...")
    
    vectorstore = None
    
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(docs) + batch_size - 1)//batch_size} (Chunks {i} to {i+len(batch)})...")
        
        if vectorstore is None:
            vectorstore = FAISS.from_documents(batch, embedding)
        else:
            vectorstore.add_documents(batch)
            
        if i + batch_size < len(docs):
            print(f"Waiting 60 seconds to respect rate limits ({batch_size} per minute)...")
            time.sleep(60)
            
    print(f"Saving vector store to {save_path}...")
    if vectorstore:
        vectorstore.save_local(save_path)
    print("Done!")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    save_path = os.path.join(base_dir, "faiss_index")
    index_documents(docs_dir, save_path)
