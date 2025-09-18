from typing import Any, Optional
from langchain_core.messages import HumanMessage

# Lazy import to avoid heavy init at import time
_QUERY_SYSTEM = None


def _get_query_system():
    global _QUERY_SYSTEM
    if _QUERY_SYSTEM is None:
        try:
            from KG.kg_query import RobustKnowledgeGraphQuery, get_credentials_from_env
        except Exception as e:
            raise RuntimeError(f"Failed importing KG query system: {e}")

        groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
        _QUERY_SYSTEM = RobustKnowledgeGraphQuery(
            groq_api_key=groq_api_key,
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
        )
    return _QUERY_SYSTEM


def kg_retrieve(state: dict[str, Any]) -> dict[str, Any]:
    """Query the Knowledge Graph and enrich the state with concise context.

    Adds 'kg_context' to state for downstream grounding in the logical agent.
    """
    user_question = state["messages"][-1].content

    query_system = _get_query_system()
    result = query_system.query(user_question)

    # Build a compact context string for grounding
    answer_text: str = result.get("answer", "")
    confidence: float = float(result.get("confidence", 0.0))
    sources = result.get("sources", [])

    compact_sources: list[str] = []
    for s in sources[:5]:
        if isinstance(s, dict):
            node_id = s.get("node_id") or s.get("data", {}).get("node_id") or ""
            node_type = s.get("node_type") or s.get("data", {}).get("node_type") or ""
            if node_id or node_type:
                compact_sources.append(f"{node_type}:{node_id}")

    context_lines = [
        f"KG_CONFIDENCE={confidence:.2f}",
        "KG_ANSWER=\n" + answer_text.strip(),
    ]
    if compact_sources:
        context_lines.append("KG_SOURCES=" + ", ".join(compact_sources))

    kg_context = "\n".join(context_lines)

    return {
        "messages": state["messages"],
        "message_type": state.get("message_type"),
        "kg_context": kg_context,
    }


