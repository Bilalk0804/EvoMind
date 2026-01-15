"""
Simplified AI Assistant - Single LLM with KG/Vector Context
Clean, natural conversation without constant questioning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from KG.kg_builder import RobustKnowledgeGraphBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """Holds conversation state for a session."""
    session_id: str = ""
    messages: List[Dict[str, str]] = field(default_factory=list)
    kg_builder: Optional[Any] = None

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_history(self, max_turns: int = 10) -> str:
        """Return recent conversation history as formatted string."""
        recent = self.messages[-(max_turns * 2):]
        lines = []
        for msg in recent:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        return "\n".join(lines)


class SimpleChatBot:
    """Single LLM chatbot with KG context retrieval."""

    SYSTEM_PROMPT = """You are a helpful, friendly AI assistant. Your goal is to have natural, 
flowing conversations while providing accurate and useful information.

Guidelines:
- Be conversational and warm, not robotic
- Give direct answers, don't ask excessive questions
- Use the provided context when relevant, but don't force it
- If you don't know something, say so honestly
- Keep responses concise but complete

{context_section}"""

    def __init__(self, groq_api_key: str, kg_builder: Optional[RobustKnowledgeGraphBuilder] = None):
        self.llm = ChatGroq(
            api_key=groq_api_key,
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        self.kg_builder = kg_builder
        logger.info("SimpleChatBot initialized")

    def _get_kg_context(self, query: str, session: ChatSession) -> str:
        """Retrieve relevant context from Knowledge Graph."""
        if not self.kg_builder:
            return ""

        # Query the graph for relevant patterns
        context_query = """
        MATCH (n)
        WHERE n.text CONTAINS $keyword OR n.id CONTAINS $keyword
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN n.id as node, type(r) as rel, m.id as connected
        LIMIT 10
        """
        
        # Extract keywords from query
        keywords = [w for w in query.lower().split() if len(w) > 3]
        
        results = []
        for keyword in keywords[:3]:
            rows = self.kg_builder.graph.query(context_query, {"keyword": keyword})
            results.extend(rows)

        if not results:
            return ""

        # Format context
        context_lines = ["Relevant information from knowledge base:"]
        seen = set()
        for row in results[:8]:
            node = row.get("node", "")
            if node and node not in seen:
                seen.add(node)
                rel = row.get("rel", "")
                connected = row.get("connected", "")
                if rel and connected:
                    context_lines.append(f"- {node} → {rel} → {connected}")
                else:
                    context_lines.append(f"- {node}")

        return "\n".join(context_lines) if len(context_lines) > 1 else ""

    def chat(self, user_message: str, session: ChatSession) -> str:
        """Generate a response to the user message."""
        # Get KG context
        kg_context = self._get_kg_context(user_message, session)
        
        # Build context section
        context_section = ""
        if kg_context:
            context_section = f"\n\nContext:\n{kg_context}"

        # Build the prompt
        system_content = self.SYSTEM_PROMPT.format(context_section=context_section)
        
        # Build messages list
        messages = [SystemMessage(content=system_content)]
        
        # Add conversation history
        for msg in session.messages[-(10):]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current message
        messages.append(HumanMessage(content=user_message))

        # Generate response
        response = self.llm.invoke(messages)
        assistant_reply = response.content if hasattr(response, "content") else str(response)

        # Update session
        session.add_message("user", user_message)
        session.add_message("assistant", assistant_reply)

        return assistant_reply


def init_chatbot() -> tuple:
    """Initialize the chatbot with environment credentials."""
    load_dotenv()
    
    groq_key = os.getenv("GROQ_API_KEY")
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_pass = os.getenv("NEO4J_PASSWORD")

    if not groq_key:
        raise RuntimeError("GROQ_API_KEY is required")

    kg_builder = None
    if all([neo4j_uri, neo4j_user, neo4j_pass]):
        kg_builder = RobustKnowledgeGraphBuilder(groq_key, neo4j_uri, neo4j_user, neo4j_pass)
        logger.info("Knowledge Graph connected")
    else:
        logger.warning("Neo4j credentials missing - running without KG")

    chatbot = SimpleChatBot(groq_key, kg_builder)
    return chatbot, kg_builder


def main() -> None:
    """CLI interface for testing the chatbot."""
    chatbot, kg_builder = init_chatbot()
    
    session = ChatSession(session_id=f"cli_{int(datetime.utcnow().timestamp())}")
    session.kg_builder = kg_builder

    print("\n🤖 AI Assistant ready! Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        response = chatbot.chat(user_input, session)
        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    main()
