"""
vector_db.py — Retriever factory for the Alpha-Guide RAG pipeline.

Provides five retrieval strategies, all backed by the same document corpus
(docs/QuestionsOfLife.pdf):

    naive           – plain vector-similarity search via Qdrant
    bm25            – sparse keyword search (BM25 / Okapi)
    parent_document – child-chunk lookup that returns the broader parent chunk
    multi_query     – LLM rewrites the user question into variants for recall
"""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models


# ---------------------------------------------------------------------------
# Document loading  (resolved relative to *this* file so it works from any cwd)
# ---------------------------------------------------------------------------
_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
_PDF_PATH = _DOCS_DIR / "QuestionsOfLife.pdf"

_loader = PyPDFLoader(str(_PDF_PATH))
_raw_docs = _loader.load()

# Shared embeddings instance (text-embedding-3-small → 1536 dims)
_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Pre-split documents used by most retrievers
_text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
_split_docs = _text_splitter.split_documents(_raw_docs)



# ---------------------------------------------------------------------------
# Individual retriever factories
# ---------------------------------------------------------------------------
""" def create_naive_retriever(k: int = 4):
    vectorstore = create_qdrant_vectorstore("wellness_naive")
    vectorstore.add_documents(_split_docs)
    return vectorstore.as_retriever(search_kwargs={"k": k})
 """

def create_bm25_retriever(k: int = 4):
    """Sparse keyword retriever — no embeddings, pure BM25 scoring."""
    return BM25Retriever.from_documents(_split_docs, k=k)


def create_parent_document_retriever(store, vectorstore):
    """
    Indexes small *child* chunks for matching accuracy, but returns the
    larger *parent* chunk so the LLM gets more surrounding context.
    """
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=200
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400, chunk_overlap=50
    )

    
    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )
    retriever.add_documents(_raw_docs, ids=None)
    return retriever




""" def create_multi_query_retriever(chat_model, k: int = 4):
    Uses the LLM to rephrase the user question into several variants,
    runs each through the base vector retriever, and merges the results.
    base_retriever = create_naive_retriever(k=k)
    return MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=chat_model,
    ) """


# ---------------------------------------------------------------------------
# Public entry-point: build every retriever in one call
# ---------------------------------------------------------------------------
def build_all_retrievers(chat_model) -> dict:
    """
    Construct and return all available retrieval strategies.

    Parameters
    ----------
    chat_model : BaseChatModel
        The LLM used by retrieval strategies that need one (multi_query).

    Returns
    -------
    dict[str, BaseRetriever]
        Mapping of strategy name → retriever instance.
    """
    return {
        #"naive": create_naive_retriever(),
        "bm25": create_bm25_retriever(),
        "parent_document": create_parent_document_retriever(),
        #"multi_query": create_multi_query_retriever(chat_model),
    }
