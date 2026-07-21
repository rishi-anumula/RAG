import chromadb
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Initialize Persistent Chroma Client
try:
    from chromadb.config import Settings
    
    # Custom dummy embedding function to prevent ChromaDB from loading
    # the heavy default ONNX/SentenceTransformer models at startup, saving RAM.
    class DummyEmbeddingFunction:
        def __call__(self, input: List[str]) -> List[List[float]]:
            return []

    chroma_client = chromadb.PersistentClient(
        path=settings.CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    # Get or create collection
    collection = chroma_client.get_or_create_collection(
        name="kb_documents",
        metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        embedding_function=DummyEmbeddingFunction()
    )
    logger.info("Successfully connected to ChromaDB persistent storage.")
except Exception as e:
    logger.critical(f"Failed to initialize ChromaDB: {e}", exc_info=True)
    raise e

def add_document_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks: List[str],
    embeddings: List[List[float]],
    start_page: List[int],
    chunk_indices: List[int]
) -> bool:
    """
    Inserts chunks, metadata, and generated vector embeddings into ChromaDB.
    """
    try:
        if not chunks:
            logger.warning("Empty chunks list passed to add_document_chunks.")
            return True

        ids = [f"{document_id}_{i}" for i in range(len(chunks))]
        
        metadatas = []
        for i in range(len(chunks)):
            metadatas.append({
                "user_id": user_id,
                "document_id": document_id,
                "filename": filename,
                "page": int(start_page[i]),
                "chunk_number": int(chunk_indices[i])
            })
            
        logger.info(f"Adding {len(chunks)} chunks for document {document_id} ({filename}) to ChromaDB.")
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=chunks
        )
        logger.info(f"Successfully added document {document_id} chunks to ChromaDB.")
        return True
    except Exception as e:
        logger.error(f"Error adding chunks to ChromaDB for doc {document_id}: {e}", exc_info=True)
        return False

def search_similar_chunks(
    user_id: str,
    query_embedding: List[float],
    document_ids: Optional[List[str]] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Queries ChromaDB for the top_k most similar chunks, filtered by user_id and optionally document_ids.
    """
    try:
        # Build filter query
        filter_query = {"user_id": user_id}
        
        if document_ids and len(document_ids) > 0:
            if len(document_ids) == 1:
                filter_query = {
                    "$and": [
                        {"user_id": user_id},
                        {"document_id": document_ids[0]}
                    ]
                }
            else:
                filter_query = {
                    "$and": [
                        {"user_id": user_id},
                        {"document_id": {"$in": document_ids}}
                    ]
                }
                
        logger.info(f"Querying ChromaDB for user_id={user_id}, filter={filter_query}")
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_query,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted_results = []
        if results and results["documents"] and len(results["documents"][0]) > 0:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for doc, meta, dist in zip(documents, metadatas, distances):
                # Convert cosine distance to cosine similarity: similarity = 1 - distance
                # ChromaDB cosine distance range is [0, 2], where 0 is identical
                similarity = 1.0 - float(dist)
                formatted_results.append({
                    "chunk": doc,
                    "metadata": meta,
                    "similarity": round(max(0.0, min(1.0, similarity)), 4)
                })
        
        logger.info(f"ChromaDB returned {len(formatted_results)} results.")
        return formatted_results
    except Exception as e:
        logger.error(f"Error searching ChromaDB: {e}", exc_info=True)
        return []

def delete_document_chunks(user_id: str, document_id: str) -> bool:
    """
    Deletes all chunks belonging to a document.
    """
    try:
        logger.info(f"Deleting chunks for document {document_id} of user {user_id}")
        collection.delete(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"document_id": document_id}
                ]
            }
        )
        logger.info(f"Successfully deleted document {document_id} chunks from ChromaDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete document {document_id} chunks: {e}", exc_info=True)
        return False
