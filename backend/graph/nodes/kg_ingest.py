from typing import Any
from langchain_core.documents import Document
from threading import Thread
from vector_db.vector_manager import get_vector_db_manager

_BUILDER = None


def _get_builder():
    global _BUILDER
    if _BUILDER is None:
        try:
            from KG.kg_builder import RobustKnowledgeGraphBuilder, get_credentials_from_env
        except Exception as e:
            raise RuntimeError(f"Failed importing KG builder: {e}")

        groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
        _BUILDER = RobustKnowledgeGraphBuilder(
            groq_api_key=groq_api_key,
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
        )
    return _BUILDER


def _ingest_qa_pair_async(question: str, answer: str, metadata: dict = None) -> None:
    """Ingest Q&A pair into both Knowledge Graph and Vector Database."""
    try:
        # Store in vector database
        vector_db = get_vector_db_manager()
        vector_db.store_qa_pair(question, answer, metadata)
        
        # Also ingest into Knowledge Graph for relationship analysis
        builder = _get_builder()
        qa_content = f"Question: {question}\nAnswer: {answer}"
        doc = Document(
            page_content=qa_content, 
            metadata={
                "source": "qa_pair", 
                "question": question,
                "answer": answer,
                "type": "conversation"
            }
        )
        enhanced_docs = builder._enhance_document_content([doc])
        chunks = builder.text_splitter.split_documents(enhanced_docs)
        graph_docs = builder._create_enhanced_graph_documents(chunks)
        if graph_docs:
            builder.graph.add_graph_documents(graph_docs)
            builder.graph.refresh_schema()
    except Exception as e:
        # Log error but don't fail the main flow
        print(f"Warning: Failed to ingest Q&A pair: {e}")


def _ingest_content_async(message_text: str) -> None:
    """Legacy function for ingesting general content."""
    try:
        builder = _get_builder()
        doc = Document(page_content=message_text, metadata={"source": "chat", "role": "user"})
        enhanced_docs = builder._enhance_document_content([doc])
        chunks = builder.text_splitter.split_documents(enhanced_docs)
        graph_docs = builder._create_enhanced_graph_documents(chunks)
        if graph_docs:
            builder.graph.add_graph_documents(graph_docs)
            builder.graph.refresh_schema()
    except Exception:
        # Intentionally swallow errors to avoid impacting the user flow
        pass


def kg_ingest(state: dict[str, Any]) -> dict[str, Any]:
    """
    Ingest Q&A pairs into both Knowledge Graph and Vector Database.
    This runs after the user provides answers to clarifying questions.
    """
    # Check if we have Q&A pairs to ingest
    qa_pairs = state.get("qa_pairs", [])
    
    if qa_pairs:
        # Ingest each Q&A pair
        for qa_pair in qa_pairs:
            question = qa_pair.get("question", "")
            answer = qa_pair.get("answer", "")
            metadata = qa_pair.get("metadata", {})
            
            if question and answer:
                Thread(
                    target=_ingest_qa_pair_async, 
                    args=(question, answer, metadata), 
                    daemon=True
                ).start()
    
    # Also ingest the original question if it exists
    original_question = state.get("original_question", "")
    if original_question and not qa_pairs:
        Thread(target=_ingest_content_async, args=(original_question,), daemon=True).start()

    return {
        "messages": state["messages"], 
        "clarifying_questions": state.get("clarifying_questions", []),
        "needs_more_info": state.get("needs_more_info", False),
        "similar_qa_pairs": state.get("similar_qa_pairs", []),
        "original_question": state.get("original_question", ""),
        "qa_pairs": qa_pairs,
        "kg_ingested": True
    }


