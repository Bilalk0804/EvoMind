from typing import Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from graph.nodes.classify_message import classify_message
from graph.nodes.kg_ingest import kg_ingest
from graph.nodes.problem_extractor import extract_root_problem, needs_more_info
from graph.nodes.proximity_checker import check_proximity, should_store_qa
from graph.nodes.response_generator import generate_response_with_insights, generate_simple_response, ask_more_questions
from graph.nodes.qa_collector import collect_qa_pairs

class State(TypedDict):
    messages: Annotated[list, add_messages]
    original_question: str | None
    clarifying_questions: List[str] | None
    current_question_index: int | None
    conversation_memory: Dict[str, Any] | None  # Memory for conversation context
    answered_questions: List[Dict[str, str]] | None  # Track Q&A pairs
    needs_more_info: bool | None
    similar_qa_pairs: List[Dict[str, Any]] | None
    qa_pairs: List[Dict[str, Any]] | None
    qa_collected: bool | None
    root_problem: str | None
    problem_discovered: bool | None
    confidence: float | None
    supporting_evidence: List[str] | None
    kg_context: str | None
    kg_confidence: float | None
    proximity_score: float | None
    proximity_level: str | None
    proximity_reasoning: str | None
    should_store_qa: bool | None
    storage_reason: str | None
    final_response: str | None
    response_type: str | None
    kg_ingested: bool | None

def build_graph():
    """
    Builds the new conversation flow graph with the following logic:
    
    1. User enters prompt
    2. System queries Vector Database
    3. LLM1 analyzes prompt and generates clarifying questions
    4. Questions shown to user, user provides responses
    5. Q&A pairs stored in Knowledge Graph
    6. LLM2 processes Knowledge Graph to extract root problem
    7. Decision 1: If root problem not discovered → ask for more info → loop back
    8. If root problem discovered → check proximity
    9. Decision 2: If proximity low → simple response (no storage)
    10. If proximity high → comprehensive response → store in Vector DB + update KG
    """
    graph_builder = StateGraph(State)

    # Add all nodes for psychiatrist flow
    graph_builder.add_node("classify_message", classify_message)  # LLM1: Ask first question
    graph_builder.add_node("ask_more_questions", ask_more_questions)  # LLM1: Ask follow-up questions
    graph_builder.add_node("collect_qa_pairs", collect_qa_pairs)  # Collect user responses
    graph_builder.add_node("kg_ingest", kg_ingest)  # Store Q&A pairs in KG
    graph_builder.add_node("extract_root_problem", extract_root_problem)  # LLM2: Analyze for root problem
    graph_builder.add_node("generate_comprehensive_response", generate_response_with_insights)  # Final diagnosis & advice

    # Define the flow
    graph_builder.add_edge(START, "classify_message")

    def initial_router(state: State):
        """Router after initial classification - LLM1 generates questions"""
        needs_more = state.get("needs_more_info", True)
        if needs_more:
            return "ask_more_questions"  # LLM1 asks questions
        else:
            # If no more info needed, go directly to KG ingestion then LLM2
            return "kg_ingest"

    graph_builder.add_conditional_edges("classify_message", initial_router, {
        "ask_more_questions": "ask_more_questions",
        "kg_ingest": "kg_ingest"
    })

    # After asking questions, collect user responses
    graph_builder.add_edge("ask_more_questions", "collect_qa_pairs")
    
    # After collecting Q&A pairs, ingest them
    graph_builder.add_edge("collect_qa_pairs", "kg_ingest")
    
    # After ingesting, extract root problem
    graph_builder.add_edge("kg_ingest", "extract_root_problem")

    def problem_discovery_router(state: State):
        """Router after LLM2 psychological analysis - Decision 1"""
        problem_discovered = state.get("problem_discovered", False)
        confidence = state.get("confidence", 0.0)
        
        # LLM2 must be 85%+ confident to proceed to diagnosis
        if not problem_discovered or confidence < 0.85:
            return "ask_more_questions"  # Continue asking questions until confident
        else:
            return "generate_comprehensive_response"  # Give final diagnosis and advice

    graph_builder.add_conditional_edges("extract_root_problem", problem_discovery_router, {
        "ask_more_questions": "ask_more_questions",
        "generate_comprehensive_response": "generate_comprehensive_response"
    })

    # Final diagnosis leads to END
    graph_builder.add_edge("generate_comprehensive_response", END)

    return graph_builder.compile()