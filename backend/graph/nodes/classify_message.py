from models.llm import llm 
from pydantic import BaseModel, Field
from typing import Any, List
from vector_db.vector_manager import get_vector_db_manager
from langchain_core.messages import AIMessage

class CounselorQuestion(BaseModel):
    question: str = Field(
        ...,
        description="A single empathetic counselor-style question to understand the user's emotional state"
    )
    needs_more_info: bool = Field(
        default=True,
        description="Whether more information is needed (always True until root problem found)"
    )

def classify_message(state: dict[str, Any]) -> dict[str, Any]:
    """
    LLM1: Acts as a psychiatrist/counselor, asking ONE empathetic question at a time.
    This is the initial analysis of the user's message.
    """
    last_message = state["messages"][-1].content
    
    # Query vector database for similar Q&A pairs
    try:
        vector_db = get_vector_db_manager()
        similar_pairs = vector_db.search_similar_qa(last_message, k=3)
    except Exception as e:
        print(f"Vector DB error: {e}")
        similar_pairs = []
    
    # Get conversation history for context
    qa_pairs = state.get("qa_pairs", [])
    conversation_context = ""
    
    if qa_pairs:
        conversation_context = "\n\nPrevious conversation in this session:\n"
        for i, qa in enumerate(qa_pairs, 1):
            conversation_context += f"Q{i}: {qa.get('question', '')}\n"
            conversation_context += f"A{i}: {qa.get('answer', '')}\n\n"
    
    # Generate ONE empathetic question using LLM1
    counselor_llm = llm.with_structured_output(CounselorQuestion)
    
    # Build context from similar Q&A pairs
    context = ""
    if similar_pairs:
        context = "\n\nSimilar previous conversations:\n"
        for i, pair in enumerate(similar_pairs, 1):
            context += f"{i}. Q: {pair['question']}\n   A: {pair['answer'][:100]}...\n"
    
    result = counselor_llm.invoke([
        {    
            "role":"system",
            "content":f"""
                You are LLM1, a professional psychiatrist/counselor AI. Your role is to ask ONE empathetic question at a time to understand the user's emotional and psychological state.
                
                IMPORTANT RULES:
                1. Ask ONLY ONE question per response
                2. Be empathetic, warm, and professional like a real therapist
                3. Focus on emotions, feelings, and psychological aspects
                4. Build on previous answers to go deeper
                5. Try to understand the ROOT CAUSE of their emotional state
                6. Use therapeutic questioning techniques
                
                Your questioning approach:
                - Start with understanding their current emotional state
                - Explore when/how these feelings started
                - Understand triggers and patterns
                - Explore relationships and social context
                - Identify coping mechanisms they've tried
                - Look for underlying beliefs or traumas
                
                Current conversation context:{conversation_context}
                
                Similar past conversations:{context}
                
                Ask ONE thoughtful, empathetic question that will help uncover the psychological root of their issue.
            """
        },
        {"role":"user","content":last_message}
    ])
    
    # Add the question to messages so it gets displayed
    question_message = AIMessage(content=result.question)
    
    return {
        "messages": state["messages"] + [question_message], 
        "current_question": result.question,
        "conversation_memory": {
            "original_question": last_message,
            "context_summary": f"User is asking about: {last_message}",
            "session_start": True
        },
        "qa_pairs": qa_pairs,
        "needs_more_info": True,  # Always True until LLM2 finds root problem
        "similar_qa_pairs": similar_pairs,
        "original_question": last_message,
        "response_type": "asking_for_more_info"
    }