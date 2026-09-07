"""Optional vector retrieval over canonical chunks; never imported by document parsing."""

import gc
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from chromadb import PersistentClient
from comproscanner._logging import setup_logger
from .embeddings import MultiModelEmbeddings

logger = setup_logger("comproscanner.log", module_name="rag")


class VectorDatabaseManager:
    """Leak-safe, auto-persisting ChromaDB handler for multiple vector databases."""

    def __init__(self, rag_config):
        self.rag_config = rag_config
        self.enabled = getattr(rag_config, "enabled", True)
        self.rag_db_path = Path(rag_config.rag_db_path)
        if not self.enabled:
            self.embeddings = None
            self.client = None
            return
        self.embeddings = MultiModelEmbeddings(rag_config)
        self.client = PersistentClient(path=str(self.rag_db_path))

    def create_chunk_database(self, db_name: str, chunks) -> None:
        """Index canonical TextChunks without applying a second text splitter.

        Rule matching and vector retrieval can therefore refer to the same
        ``chunk_id`` and the same source text.
        """
        if not self.enabled:
            raise RuntimeError("Vector retrieval is disabled for this processing run")
        if not db_name:
            raise ValueError("Database name is required")
        chunks = list(chunks)
        if not chunks:
            raise ValueError("At least one canonical text chunk is required")
        db_location = self.rag_db_path / db_name
        db_location.mkdir(parents=True, exist_ok=True)
        docs = []
        for chunk in chunks:
            metadata = {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "section": chunk.section,
                "ordinal": chunk.ordinal,
            }
            if chunk.page_start is not None:
                metadata["page_start"] = chunk.page_start
            if chunk.page_end is not None:
                metadata["page_end"] = chunk.page_end
            docs.append(Document(page_content=chunk.content, metadata=metadata))
        vectordb = Chroma.from_documents(
            documents=docs,
            embedding=self.embeddings,
            persist_directory=str(db_location),
            ids=[chunk.chunk_id for chunk in chunks],
        )
        self._release_vector_database(vectordb)
        logger.info("Canonical chunk database auto-persisted at %s", db_location)

    def query_chunks(self, db_name: str, query: str, top_k: int = 5) -> list[dict]:
        """Return vector matches keyed by canonical ``chunk_id``."""
        results = self.query_database(db_name=db_name, query=query, top_k=top_k)
        matches = []
        for document, score in results:
            chunk_id = document.metadata.get("chunk_id")
            if not chunk_id:
                logger.warning("Ignoring legacy vector result without chunk_id")
                continue
            matches.append(
                {
                    "chunk_id": chunk_id,
                    "score": float(score),
                    "content": document.page_content,
                    "metadata": dict(document.metadata),
                }
            )
        return matches

    def _release_vector_database(self, vectordb) -> None:
        """Release Chroma and optional CUDA resources consistently."""
        self.client.clear_system_cache()
        del vectordb
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def query_database(self, db_name: str, query: str, top_k: int = 5):
        """Query the persisted ChromaDB database."""
        if not self.enabled:
            raise RuntimeError("Vector retrieval is disabled for this processing run")
        db_location = self.rag_db_path / db_name
        if not db_location.exists():
            raise ValueError(f"Database {db_name} not found at {db_location}")
        vectordb = Chroma(
            persist_directory=str(db_location), embedding_function=self.embeddings
        )
        results = vectordb.similarity_search_with_score(query, k=top_k)
        self.client.clear_system_cache()
        del vectordb
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info(f"Retrieved {len(results)} results from {db_name}")
        return results

    def database_exists(self, db_name: str) -> bool:
        """Check if a vector database exists."""
        if not self.enabled:
            return True
        db_location = self.rag_db_path / db_name
        return db_location.exists()
