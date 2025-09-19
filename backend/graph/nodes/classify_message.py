from models.llm import llm 
from pydantic import BaseModel, Field
from typing import Any, List
from vector_db.vector_manager import get_vector_db_manager

class ClarifyingQuestions(BaseModel):
    questions: List[str] = Field(
        ...,
        description="List of exactly 5 clarifying questions to better understand the user's needs"
    )
    needs_more_info: bool = Field(
        ...,
        description="Whether the user's message needs more clarification"
    )
    current_question_index: int = Field(
        default=0,
        description="Index of the current question being asked (0-4)"
    )

def classify_message(state: dict[str, Any]) -> dict[str, Any]:
    """
    LLM1: Analyzes the user prompt and generates clarifying questions.
    Also queries Vector Database for similar Q&A pairs.
    """
    last_message = state["messages"][-1].content
    
    # Query vector database for similar Q&A pairs
    vector_db = get_vector_db_manager()
    similar_pairs = vector_db.search_similar_qa(last_message, k=3)
    
    # Generate clarifying questions using LLM1
    questions_llm = llm.with_structured_output(ClarifyingQuestions)
    
    # Build context from similar Q&A pairs
    context = ""
    if similar_pairs:
        context = "\n\nSimilar previous conversations:\n"
        for i, pair in enumerate(similar_pairs, 1):
            context += f"{i}. Q: {pair['question']}\n   A: {pair['answer'][:100]}...\n"
    
    result = questions_llm.invoke([
        {    
            "role":"system",
            "content":f"""
                You are LLM1, a counselor-style AI responsible for analyzing user prompts and generating contextual clarifying questions.
                
                Your task:
                1. Analyze the user's message to understand what they're asking
                2. Generate exactly 5 specific, helpful clarifying questions that build on each other
                3. Ensure questions flow logically and create a conversation-like experience
                4. Determine if more information is needed
                
                Guidelines for counselor-style questions:
                - Start with broad understanding, then get more specific
                - Each question should naturally lead to the next
                - Focus on emotions, context, and personal experience
                - Ask about feelings, situations, attempts made, and desired outcomes
                - Make questions empathetic and supportive
                - Consider the context from similar conversations if provided
                
                Example flow for relationship/emotional topics:
                1. Understanding feelings and duration
                2. Context and circumstances 
                3. Current situation and interactions
                4. Previous attempts or coping strategies
                5. Desired outcome or specific help needed
                
                Context from similar conversations:{context}
            """
        },
        {"role":"user","content":last_message}
    ])
    
    return {
        "messages": state["messages"], 
        "clarifying_questions": result.questions,
        "current_question_index": 0,
        "conversation_memory": {
            "original_question": last_message,
            "context_summary": f"User is asking about: {last_message}",
            "session_start": True
        },
        "answered_questions": [],
        "needs_more_info": result.needs_more_info,
        "similar_qa_pairs": similar_pairs,
        "original_question": last_message
    }