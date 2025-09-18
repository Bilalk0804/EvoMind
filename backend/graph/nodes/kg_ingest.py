from typing import Any
from langchain.schema import Document
from threading import Thread

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


def _ingest_content_async(message_text: str) -> None:
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
    """Kick off background ingestion of the latest user message into the KG.

    Runs asynchronously so it doesn't block the user response path.
    """
    message_text = state["messages"][-1].content
    if not message_text or not message_text.strip():
        return {"messages": state["messages"], "message_type": state.get("message_type"), "kg_context": state.get("kg_context"), "kg_ingested": False}

    Thread(target=_ingest_content_async, args=(message_text,), daemon=True).start()

    return {"messages": state["messages"], "message_type": state.get("message_type"), "kg_context": state.get("kg_context"), "kg_ingested": True}


