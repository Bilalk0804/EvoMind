#!/usr/bin/env python3
"""
Response Generator
Generates final responses based on the analysis and decision flow.
"""
from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage
from models.llm import llm

def generate_response_with_insights(state: dict[str, Any]) -> dict[str, Any]:
    """
    FINAL DIAGNOSIS: LLM2 found the root psychological problem → LLM1 delivers diagnosis and therapeutic advice.
    This is when the psychiatrist tells the user what they discovered and gives tasks/advice.
    """
    try:
        original_question = state.get("original_question", "")
        root_problem = state.get("root_problem", "")
        psychological_pattern = state.get("psychological_pattern", "")
        supporting_evidence = state.get("supporting_evidence", [])
        recommended_approach = state.get("recommended_approach", "")
        confidence = state.get("confidence", 0.0)
        qa_pairs = state.get("qa_pairs", [])
        
        # Build comprehensive context for the final diagnosis
        context_parts = []
        
        if original_question:
            context_parts.append(f"Original Concern: {original_question}")
        
        if root_problem:
            context_parts.append(f"Root Psychological Problem: {root_problem}")
        
        if psychological_pattern:
            context_parts.append(f"Psychological Pattern: {psychological_pattern}")
        
        if supporting_evidence:
            context_parts.append("Evidence from our conversation:")
            for i, evidence in enumerate(supporting_evidence, 1):
                context_parts.append(f"{i}. {evidence}")
        
        if qa_pairs:
            context_parts.append("Our conversation analysis:")
            for i, qa_pair in enumerate(qa_pairs, 1):
                context_parts.append(f"{i}. Q: {qa_pair.get('question', '')}")
                context_parts.append(f"   A: {qa_pair.get('answer', '')}")
        
        full_context = "\n".join(context_parts)
        
        prompt = ChatPromptTemplate.from_template(
            '''
            You are LLM1, a professional psychiatrist/counselor. LLM2 (your psychological analyst) has identified the user's root psychological problem with high confidence.
            
            Now you must deliver the diagnosis and provide therapeutic guidance, just like a real psychiatrist would.
            
            LLM2's Psychological Analysis:
            {context}
            
            Confidence Level: {confidence}%
            
            Your role as LLM1 (Psychiatrist):
            1. EXPLAIN THE DIAGNOSIS: Tell the user what psychological issue you've identified
            2. VALIDATE THEIR EXPERIENCE: Show empathy and normalize their feelings
            3. EXPLAIN THE PATTERN: Help them understand how this problem manifests
            4. PROVIDE THERAPEUTIC TASKS: Give 3-5 specific, actionable therapeutic exercises or tasks
            5. OFFER HOPE: Reassure them this is treatable and they can improve
            
            Structure your response like a real psychiatric consultation:
            - "Based on our conversation, I've identified..."
            - "This is a common psychological pattern where..."
            - "Here's what I recommend you do to start healing..."
            - "These exercises will help you..."
            
            Be professional, empathetic, and provide concrete therapeutic interventions.
            '''
        )
        
        formatted_prompt = prompt.format_prompt(context=full_context, confidence=int(confidence*100))
        
        # Stream the response
        final_text_parts = []
        for chunk in llm.stream(formatted_prompt.to_messages()):
            text = getattr(chunk, "content", None) or getattr(chunk, "text", "") or ""
            if text:
                print(text, end="", flush=True)
                final_text_parts.append(text)
        print()  # newline after stream
        
        response = AIMessage(content="".join(final_text_parts))
        
        return {
            **state,
            "messages": state["messages"] + [response],
            "final_response": response.content,
            "response_type": "comprehensive_with_insights"
        }
        
    except Exception as e:
        print(f"Error generating comprehensive response: {e}")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=f"Error generating response: {str(e)}")],
            "final_response": f"Error: {str(e)}",
            "response_type": "error"
        }

def generate_simple_response(state: dict[str, Any]) -> dict[str, Any]:
    """
    LOW PROXIMITY: LLM1 generates a simple response without LLM2 insights.
    This response will NOT be stored.
    """
    try:
        original_question = state.get("original_question", "")
        root_problem = state.get("root_problem", "")
        
        prompt = ChatPromptTemplate.from_template(
            '''
            You are LLM1. LLM2 has determined that the root problem ({root_problem}) has LOW PROXIMITY to the user's original question.
            
            Since the proximity is low, provide a direct, simple response without using LLM2's detailed analysis.
            
            Original Question: {question}
            
            Guidelines for LLM1 (Low Proximity):
            - Answer the question directly and simply
            - Be concise and helpful
            - Don't reference the root problem analysis (it's not relevant)
            - Keep it focused on the original question only
            - Provide basic, general advice
            
            Provide a clear, direct response that addresses their question without complex analysis.
            '''
        )
        
        formatted_prompt = prompt.format_prompt(
            question=original_question,
            root_problem=root_problem or "N/A"
        )
        
        # Stream the response
        final_text_parts = []
        for chunk in llm.stream(formatted_prompt.to_messages()):
            text = getattr(chunk, "content", None) or getattr(chunk, "text", "") or ""
            if text:
                print(text, end="", flush=True)
                final_text_parts.append(text)
        print()  # newline after stream
        
        response = AIMessage(content="".join(final_text_parts))
        
        return {
            **state,
            "messages": state["messages"] + [response],
            "final_response": response.content,
            "response_type": "simple_direct"
        }
        
    except Exception as e:
        print(f"Error generating simple response: {e}")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=f"Error generating response: {str(e)}")],
            "final_response": f"Error: {str(e)}",
            "response_type": "error"
        }

def ask_more_questions(state: dict[str, Any]) -> dict[str, Any]:
    """
    LLM1: Asks ONE question at a time when LLM2 requests more information.
    Uses memory to maintain context and ensure questions are connected.
    """
    try:
        clarifying_questions = state.get("clarifying_questions", [])
        original_question = state.get("original_question", "")
        current_question_index = state.get("current_question_index", 0)
        conversation_memory = state.get("conversation_memory", {})
        answered_questions = state.get("answered_questions", [])
        
        # Build context from previous answers
        context_summary = ""
        if answered_questions:
            context_summary = "\n\nBased on what you've shared so far:\n"
            for i, qa in enumerate(answered_questions, 1):
                context_summary += f"• {qa['question']}: {qa['answer'][:100]}...\n"
        
        if clarifying_questions and current_question_index < len(clarifying_questions):
            # Ask only the current question with context
            current_question = clarifying_questions[current_question_index]
            
            if current_question_index == 0:
                # First question
                response_text = f"""I'd like to better understand your question: "{original_question}"

{current_question}

Please provide your answer, and I'll ask follow-up questions to help you better."""
            else:
                # Subsequent questions with context
                response_text = f"""Thank you for sharing that information.{context_summary}

Now, {current_question.lower()}

This will help me understand your situation better."""
            
            # Update memory and state
            updated_memory = {
                **conversation_memory,
                "current_question": current_question,
                "questions_asked": current_question_index + 1,
                "total_questions": len(clarifying_questions)
            }
            
            new_state = {
                **state,
                "current_question_index": current_question_index + 1,
                "conversation_memory": updated_memory
            }
        else:
            # If we've asked all questions or no questions exist
            if answered_questions:
                response_text = f"""Thank you for all your responses.{context_summary}

Based on everything you've shared, let me provide you with some helpful guidance."""
            else:
                response_text = f"""I'd like to better understand your question: "{original_question}"

Could you tell me more about what specific aspect you'd like help with?

This will help me give you a more accurate and helpful response."""
            
            new_state = {
                **state,
                "current_question_index": 0
            }
        
        response = AIMessage(content=response_text)
        
        return {
            **new_state,
            "messages": state["messages"] + [response],
            "final_response": response_text,
            "response_type": "asking_for_more_info"
        }
        
    except Exception as e:
        print(f"Error asking for more questions: {e}")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=f"Error: {str(e)}")],
            "final_response": f"Error: {str(e)}",
            "response_type": "error"
        }
