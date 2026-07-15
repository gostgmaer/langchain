import os
from typing import Any, List
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyMuPDFLoader,
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    Docx2txtLoader,
    JSONLoader,
)
from langchain_community.document_loaders.excel import UnstructuredExcelLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from pathlib import Path
import hashlib

def load_all_documents(data_dir:str)->List[Any]:
    """
    Load all documents from the specified directory. and Convert Documents Structure Support :PDF,TXT,CSV,Excel,DOCX,JSON,WORD
    """
    # use project root data folder
    