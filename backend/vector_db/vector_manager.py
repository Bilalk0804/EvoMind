#!/usr/bin/env python3
"""
Vector Database Manager for storing and retrieving Q&A pairs.
Uses ChromaDB for efficient similarity search and storage.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    from langchain_community.embeddings.fake import FakeEmbeddings
    import numpy as np
except ImportError as e:
    raise RuntimeError(f"Vector database dependencies not installed: {e}")

from config.settings import settings


class VectorDBManager:
    """
    Manages vector database operations for Q&A pairs storage and retrieval.
    """
    
    def __init__(self, collection_name: str = "qa_pairs"):
        self.logger = self._setup_logging()
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embeddings = None
        self.vectorstore = None
        
        self._initialize_vector_db()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for vector database operations."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _initialize_vector_db(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Initialize simple embeddings using fake embeddings (no external API)
            self.embeddings = FakeEmbeddings(size=384)  # Standard embedding size
            self.logger.info("✅ Using fake embeddings (no external API)")
            
            # Initialize ChromaDB client
            self.client = chromadb.Client(Settings(
                persist_directory="./chroma_db",
                anonymized_telemetry=False
            ))
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                self.logger.info(f"✅ Connected to existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Q&A pairs for conversation context"}
                )
                self.logger.info(f"✅ Created new collection: {self.collection_name}")
            
            # Initialize LangChain vectorstore
            self.vectorstore = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
            
            self.logger.info("Vector database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector database: {e}")
            raise
    
    def store_qa_pair(self, question: str, answer: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store a Q&A pair in the vector database.
        
        Args:
            question: The user's question
            answer: The system's answer
            metadata: Additional metadata (e.g., timestamp, session_id)
            
        Returns:
            Document ID of the stored pair
        """
        try:
            # Create document content
            content = f"Question: {question}\nAnswer: {answer}"
            
            # Prepare metadata
            doc_metadata = {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "type": "qa_pair"
            }
            
            if metadata:
                doc_metadata.update(metadata)
            
            # Generate unique document ID
            doc_id = str(uuid.uuid4())
            
            # Create document
            document = Document(
                page_content=content,
                metadata=doc_metadata
            )
            
            # Add to vectorstore
            self.vectorstore.add_documents([document], ids=[doc_id])
            
            self.logger.info(f"Stored Q&A pair with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Failed to store Q&A pair: {e}")
            raise
    
    def search_similar_qa(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar Q&A pairs based on query.
        
        Args:
            query: Search query
            k: Number of similar results to return
            
        Returns:
            List of similar Q&A pairs with metadata
        """
        try:
            # Perform similarity search
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            
            # Format results
            similar_pairs = []
            for doc, score in results:
                similar_pairs.append({
                    "question": doc.metadata.get("question", ""),
                    "answer": doc.metadata.get("answer", ""),
                    "similarity_score": float(score),
                    "metadata": doc.metadata,
                    "content": doc.page_content
                })
            
            self.logger.info(f"Found {len(similar_pairs)} similar Q&A pairs")
            return similar_pairs
            
        except Exception as e:
            self.logger.error(f"Failed to search similar Q&A pairs: {e}")
            return []
    
    def get_qa_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific Q&A pair by document ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Q&A pair data or None if not found
        """
        try:
            # Get document by ID
            results = self.vectorstore.get(ids=[doc_id])
            
            if results and results['documents']:
                doc = results['documents'][0]
                metadata = results['metadatas'][0] if results['metadatas'] else {}
                
                return {
                    "question": metadata.get("question", ""),
                    "answer": metadata.get("answer", ""),
                    "metadata": metadata,
                    "content": doc
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Q&A by ID {doc_id}: {e}")
            return None
    
    def get_all_qa_pairs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all Q&A pairs from the collection.
        
        Args:
            limit: Maximum number of pairs to return
            
        Returns:
            List of all Q&A pairs
        """
        try:
            # Get all documents
            results = self.vectorstore.get(limit=limit)
            
            qa_pairs = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    qa_pairs.append({
                        "id": results['ids'][i] if results['ids'] else None,
                        "question": metadata.get("question", ""),
                        "answer": metadata.get("answer", ""),
                        "metadata": metadata,
                        "content": doc
                    })
            
            self.logger.info(f"Retrieved {len(qa_pairs)} Q&A pairs")
            return qa_pairs
            
        except Exception as e:
            self.logger.error(f"Failed to get all Q&A pairs: {e}")
            return []
    
    def delete_qa_pair(self, doc_id: str) -> bool:
        """
        Delete a Q&A pair by document ID.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.vectorstore.delete(ids=[doc_id])
            self.logger.info(f"Deleted Q&A pair with ID: {doc_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete Q&A pair {doc_id}: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """
        Clear all Q&A pairs from the collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all document IDs
            results = self.vectorstore.get()
            if results and results['ids']:
                self.vectorstore.delete(ids=results['ids'])
                self.logger.info(f"Cleared {len(results['ids'])} Q&A pairs from collection")
            else:
                self.logger.info("Collection is already empty")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear collection: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            results = self.vectorstore.get()
            
            stats = {
                "total_documents": len(results['ids']) if results['ids'] else 0,
                "collection_name": self.collection_name,
                "embedding_model": "Google Generative AI" if isinstance(self.embeddings, GoogleGenerativeAIEmbeddings) else "OpenAI"
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


# Global instance
_vector_db_manager = None

def get_vector_db_manager() -> VectorDBManager:
    """Get or create global vector database manager instance."""
    global _vector_db_manager
    if _vector_db_manager is None:
        _vector_db_manager = VectorDBManager()
    return _vector_db_manager


if __name__ == "__main__":
    # Test the vector database manager
    print("🚀 Testing Vector Database Manager...")
    
    manager = get_vector_db_manager()
    
    # Test storing a Q&A pair
    test_question = "What is the capital of France?"
    test_answer = "The capital of France is Paris."
    
    doc_id = manager.store_qa_pair(test_question, test_answer, {"test": True})
    print(f"✅ Stored Q&A pair with ID: {doc_id}")
    
    # Test searching
    similar_pairs = manager.search_similar_qa("capital city of France", k=3)
    print(f"✅ Found {len(similar_pairs)} similar pairs")
    
    # Test retrieval by ID
    retrieved_pair = manager.get_qa_by_id(doc_id)
    if retrieved_pair:
        print(f"✅ Retrieved Q&A pair: {retrieved_pair['question']}")
    
    # Get stats
    stats = manager.get_collection_stats()
    print(f"✅ Collection stats: {stats}")
    
    print("🎉 Vector Database Manager test completed!")
