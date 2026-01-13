"""
Cleaned and refactored Async Psychiatrist system
- Removed redundant if/else and excessive try/except blocks
- Reorganized into clear functions with minimal, intentional error handling
- Uses threading.Event to stop background worker cleanly
- Uses dataclasses and logging
- Keeps original functionality (LLM1 asks, LLM2 analyzes KG) but is more maintainable

Notes:
- This file assumes `RobustKnowledgeGraphBuilder` provides methods used below.
- LLM objects must implement a simple `invoke(messages: List[dict]) -> Any` interface
  where the returned object has `.content` or is a string.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Dict, Optional
import logging
import os
import shutil
import threading
import time

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# LLM & KG imports (keep them dynamic for easier testing)
try:
    from langchain_groq import ChatGroq
    from KG.kg_builder import RobustKnowledgeGraphBuilder
except Exception:
    ChatGroq = None
    RobustKnowledgeGraphBuilder = None

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# --- Data models ---
class CounselorQuestion(BaseModel):
    question: str = Field(..., description="One empathetic counselor question")
    approach: str = Field(..., description="psychological or psychiatric")
    reasoning: str = Field(..., description="Why this approach was chosen")


class PsychologicalAnalysis(BaseModel):
    root_cause: str
    problem_discovered: bool
    confidence: float
    llm1_direction: str


@dataclass
class AsyncState:
    session_id: str = ""
    original_question: str = ""
    qa_pairs: List[Dict[str, Any]] = field(default_factory=list)
    conversation_active: bool = False
    llm2_analyzing: bool = False
    kg_builder: Optional[Any] = None
    llm2_insights: Optional[Dict[str, Any]] = None
    action_mode_triggered: bool = False
    stop_event: threading.Event = field(default_factory=threading.Event)

    def reset(self) -> None:
        self.qa_pairs.clear()
        self.llm2_insights = None
        self.action_mode_triggered = False
        self.stop_event.clear()


# --- Utilities ---

def safe_invoke(llm: Any, messages: List[Dict[str, str]]) -> str:
    """Call LLM and return the textual content in a robust way."""
    if not llm:
        raise RuntimeError("LLM is not initialized")

    result = llm.invoke(messages)
    if hasattr(result, "content"):
        return result.content
    if isinstance(result, str):
        return result
    # Fallback: try to stringify
    return str(result)


# --- KG helpers ---

def store_single_qa_in_kg(state: AsyncState, qa_pair: Dict[str, Any], qa_number: int) -> None:
    if not state.kg_builder:
        return
    state.kg_builder.store_therapy_qa_pair(
        session_id=state.session_id,
        qa_number=qa_number,
        question=qa_pair.get("question", ""),
        answer=qa_pair.get("answer", ""),
        original_concern=state.original_question,
        user_id="default_user",
    )


def analyze_entire_kg_for_patterns(state: AsyncState, llm: Any) -> None:
    if not state.kg_builder or not llm:
        return

    min_exchanges = 3
    if len([q for q in state.qa_pairs if q.get("answer")]) < min_exchanges:
        logger.debug("LLM2: waiting for more context")
        return

    kg_context = state.kg_builder.analyze_therapy_patterns(state.session_id, state.qa_pairs, user_id="default_user")
    if not kg_context:
        return

    prompt = f"""
You are **LLM2 – a Root Cause Analysis Engine**.

Your role is NOT to counsel or comfort the user.
Your role is to analyze patterns and relationships in the Knowledge Graph
and infer whether a *single dominant root cause* exists.

━━━━━━━━━━━━━━━━━━━━━━
INPUT: KNOWLEDGE GRAPH
━━━━━━━━━━━━━━━━━━━━━━
{kg_context}

━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━
1. Analyze recurring themes, emotional patterns, relationships, and timelines.
2. Identify the **most probable underlying root cause** driving the user's situation.
3. Decide whether this root cause is discovered with **high confidence**.

━━━━━━━━━━━━━━━━━━━━━━
DECISION RULES
━━━━━━━━━━━━━━━━━━━━━━
• Set `problem_discovered = true` ONLY if confidence ≥ 0.90  
• If multiple competing causes exist, choose the strongest ONE  
• If evidence is insufficient or ambiguous, set:
  - problem_discovered = false
  - confidence < 0.90

━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━
Return a SINGLE JSON object with EXACTLY these fields:

{
  "root_cause": "<clear, specific psychological root cause OR 'insufficient evidence'>",
  "problem_discovered": <true | false>,
  "confidence": <number between 0.0 and 1.0>,
  "llm1_direction": "<clear, concrete guidance for LLM1 on how to help the user>"
}

━━━━━━━━━━━━━━━━━━━━━━
GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━
• Be specific, not vague (avoid phrases like “stress”, “issues”, “problems”)
• Root cause should explain *most* observed patterns
• `llm1_direction` must be actionable and strategic, not emotional
• Do NOT include extra text, explanations, or markdown
• Do NOT mention that this analysis came from a knowledge graph
• Do NOT mention yourself or LLM2 in the output
"""


    response_text = safe_invoke(llm, [{"role": "user", "content": prompt}])

    # For safety, attempt to parse JSON from the response; otherwise store as raw insight
    parsed = None
    try:
        parsed = json_safe_parse(response_text)
    except Exception:
        parsed = None

    if parsed and parsed.get("problem_discovered") and parsed.get("confidence", 0) >= 0.9:
        state.llm2_insights = {
            "root_cause": parsed.get("root_cause"),
            "confidence": parsed.get("confidence"),
            "llm1_direction": parsed.get("llm1_direction"),
            "analysis_complete": True,
        }
        logger.info("LLM2: root cause detected: %s (%.0f%%)", state.llm2_insights["root_cause"], state.llm2_insights["confidence"] * 100)
    else:
        # keep lightweight insights even when not confident
        state.llm2_insights = {"raw": response_text}


def json_safe_parse(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse JSON from an LLM response, return dict or None."""
    import re, json

    # Try direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract JSON-like substring
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# --- Background worker ---

def llm2_background_worker(state: AsyncState, llm: Any, interval: float = 1.0) -> None:
    logger.info("LLM2 background worker started")
    processed_ids = set()

    while not state.stop_event.is_set():
        # collect new answered QA pairs
        for idx, qa in enumerate(state.qa_pairs, 1):
            qa_id = f"{idx}:{(qa.get('question') or '')[:40]}"
            if qa.get("answer") and qa_id not in processed_ids:
                store_single_qa_in_kg(state, qa, idx)
                processed_ids.add(qa_id)

        # analyze patterns when enough answered pairs
        answered_count = len([q for q in state.qa_pairs if q.get("answer")])
        if answered_count >= 3:
            state.llm2_analyzing = True
            analyze_entire_kg_for_patterns(state, llm)
            state.llm2_analyzing = False

        state.stop_event.wait(interval)

    logger.info("LLM2 background worker stopped")


# --- Visualization & cleanup ---

def generate_kg_visualization(graph: Any, out_path: str = "kg_visualization.html") -> None:
    """Create a minimal HTML visualization from a Neo4j-like graph object."""
    if not graph:
        return

    query = "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50"
    records = graph.query(query)

    parts = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>KG</title></head><body>",
        "<h1>Therapy Knowledge Graph (recent)</h1>",
    ]

    for rec in records:
        parts.append(f"<div><pre>{rec}</pre></div><hr>")

    parts.append("</body></html>")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    logger.info("KG visualization written to %s", out_path)


def clear_knowledge_graph(kg_builder: Any) -> None:
    if not kg_builder or not hasattr(kg_builder, "graph"):
        return
    kg_builder.graph.query("MATCH (n) DETACH DELETE n")
    logger.info("Knowledge graph cleared")


def clear_vector_database(paths: List[str] = None) -> None:
    if paths is None:
        paths = ["vector_db", "chroma_db", "vectorstore.db", "embeddings.db", "chroma.sqlite3"]
    for p in paths:
        if os.path.exists(p):
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
            logger.info("Cleared %s", p)


# --- Conversation logic ---

def ask_counselor_question(state: AsyncState, llm: Any, user_input: Optional[str] = None) -> str:
    # attach answer to last QA if applicable
    if user_input and state.qa_pairs:
        state.qa_pairs[-1]["answer"] = user_input

    conversation_context = "\n".join([
        f"Q{i+1}: {q.get('question')}\nA{i+1}: {q.get('answer')}"
        for i, q in enumerate(state.qa_pairs)
    ])

    llm2_note = ""
    if state.llm2_insights and state.llm2_insights.get("analysis_complete"):
        llm2_note = (
            f"LLM2 root cause: {state.llm2_insights['root_cause']}\n"
            f"Direction: {state.llm2_insights['llm1_direction']}\n"
        )

    prompt = (
        "You are a skilled counselor. Balance empathy with one strategic question.\n"
        f"User said: {user_input or state.original_question}\n"
        f"Context:\n{conversation_context}\n{llm2_note}\n"
        "Respond with one short paragraph and one follow-up question."
    )

    response_text = safe_invoke(llm, [{"role": "user", "content": prompt}])

    # append to QA pairs
    state.qa_pairs.append({
        "question": user_input or state.original_question,
        "answer": response_text,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return response_text


# --- Initialization helpers ---

def init_llm_and_kg() -> (Any, Any):
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not (groq_api_key and neo4j_uri and neo4j_username and neo4j_password):
        raise RuntimeError("Missing required environment variables for LLM or Neo4j")

    if ChatGroq is None or RobustKnowledgeGraphBuilder is None:
        raise RuntimeError("Required libraries (langchain_groq or KG.kg_builder) are not importable")

    llm = ChatGroq(api_key=groq_api_key, model="gemma2-9b-it", temperature=0.7)
    kg_builder = RobustKnowledgeGraphBuilder(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)

    return llm, kg_builder


# --- Main ---

def main() -> None:
    try:
        llm, kg_builder = init_llm_and_kg()
    except Exception as exc:
        logger.error("Initialization failed: %s", exc)
        return

    clear_knowledge_graph(kg_builder)
    clear_vector_database()

    state = AsyncState()
    state.kg_builder = kg_builder

    # Start LLM2 thread
    llm2_thread = threading.Thread(target=llm2_background_worker, args=(state, llm), daemon=True)
    state.conversation_active = True
    llm2_thread.start()

    try:
        while True:
            user_input = input("What's on your mind? ").strip()
            if not user_input:
                print("Tell me something so we can start.")
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                break

            state.original_question = user_input
            state.session_id = f"session_{int(time.time())}"

            # seed the conversation with user's initial answer
            state.qa_pairs.append({"question": "What brings you here today?", "answer": user_input, "timestamp": datetime.utcnow().isoformat()})

            # ask first counselor question
            reply = ask_counselor_question(state, llm, None)
            print("\nCounselor:\n", reply)

            # continue conversation until user types exit or reaches a soft limit
            for _ in range(20):
                user_reply = input("Your answer: ").strip()
                if not user_reply:
                    print("Please type an answer to continue.")
                    continue
                if user_reply.lower() in {"exit", "quit", "q"}:
                    state.stop_event.set()
                    break

                reply = ask_counselor_question(state, llm, user_reply)
                print("\nCounselor:\n", reply)

            # finalize session
            generate_kg_visualization(state.kg_builder.graph, out_path="kg_session.html")
            state.reset()

    finally:
        # ensure background worker stops
        state.stop_event.set()
        llm2_thread.join(timeout=2)
        logger.info("Session ended")


if __name__ == "__main__":
    main()
