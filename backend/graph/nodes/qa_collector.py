#!/usr/bin/env python3
"""
Q&A Collector
Collects user responses to clarifying questions and forms Q&A pairs.
"""
from typing import Any, Dict, List
from datetime import datetime

def collect_qa_pairs(state: dict[str, Any]) -> dict[str, Any]:
    """
    Collects user responses to clarifying questions and forms Q&A pairs.
    Updates conversation memory with the latest Q&A interaction.
    """
    try:
        # Get the latest user message (their response to questions)
        latest_message = state["messages"][-1].content
        clarifying_questions = state.get("clarifying_questions", [])
        original_question = state.get("original_question", "")
        conversation_memory = state.get("conversation_memory", {})
        answered_questions = state.get("answered_questions", [])
        current_question_index = state.get("current_question_index", 1)
        
        # Determine which question was just answered
        question_index = current_question_index - 1  # Since we incremented after asking
        if question_index >= 0 and question_index < len(clarifying_questions):
            current_question = clarifying_questions[question_index]
            
            # Add this Q&A to answered_questions for memory
            new_qa = {
                "question": current_question,
                "answer": latest_message,
                "index": question_index
            }
            answered_questions.append(new_qa)
        
        # Create comprehensive Q&A pairs for storage
        qa_pairs = []
        
        if clarifying_questions and latest_message:
            # Create a single Q&A pair with the original question
            # and the user's comprehensive response
            qa_pair = {
                "question": original_question,
                "answer": latest_message,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "num_clarifying_questions": str(len(clarifying_questions)),
                    "response_type": "clarifying_response",
                    "question_index": str(question_index)
                }
            }
            qa_pairs.append(qa_pair)
            
            # Create individual Q&A pair for the current question
            if question_index >= 0 and question_index < len(clarifying_questions):
                individual_qa = {
                    "question": clarifying_questions[question_index],
                    "answer": latest_message,
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "question_index": str(question_index),
                        "original_question": str(original_question),
                        "response_type": "individual_clarification"
                    }
                }
                qa_pairs.append(individual_qa)
        
        # Update conversation memory
        updated_memory = {
            **conversation_memory,
            "last_answer": latest_message,
            "answers_collected": len(answered_questions),
            "context_updated": datetime.now().isoformat()
        }
        
        return {
            **state,
            "qa_pairs": qa_pairs,
            "qa_collected": True,
            "answered_questions": answered_questions,
            "conversation_memory": updated_memory
        }
        
    except Exception as e:
        print(f"Error collecting Q&A pairs: {e}")
        return {
            **state,
            "qa_pairs": [],
            "qa_collected": False,
            "error": str(e)
        }

def _split_response(response: str, num_questions: int) -> List[str]:
    """
    Split user response into parts corresponding to each clarifying question.
    This is a simple heuristic approach.
    """
    if num_questions <= 1:
        return [response]
    
    # Try to split by common patterns
    # Look for numbered responses (1., 2., 3., etc.)
    import re
    
    # Pattern for numbered responses
    numbered_pattern = r'\d+\.\s*'
    numbered_parts = re.split(numbered_pattern, response)
    
    if len(numbered_parts) > 1:
        # Remove empty first part if it exists
        if not numbered_parts[0].strip():
            numbered_parts = numbered_parts[1:]
        return numbered_parts[:num_questions]
    
    # Try splitting by line breaks
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    if len(lines) >= num_questions:
        return lines[:num_questions]
    
    # Try splitting by sentences
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    if len(sentences) >= num_questions:
        return sentences[:num_questions]
    
    # Fallback: split by length
    words = response.split()
    words_per_part = len(words) // num_questions
    parts = []
    
    for i in range(num_questions):
        start_idx = i * words_per_part
        if i == num_questions - 1:  # Last part gets remaining words
            end_idx = len(words)
        else:
            end_idx = (i + 1) * words_per_part
        
        part = ' '.join(words[start_idx:end_idx])
        parts.append(part)
    
    return parts
