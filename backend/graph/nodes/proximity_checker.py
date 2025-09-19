#!/usr/bin/env python3
"""
Proximity Checker
Checks the proximity between the original question and the discovered root problem.
"""
from typing import Any, Dict
from pydantic import BaseModel, Field
from models.llm import llm

class ProximityAnalysis(BaseModel):
    proximity_score: float = Field(
        ...,
        description="Proximity score between 0.0 and 1.0 (1.0 = high proximity)"
    )
    proximity_level: str = Field(
        ...,
        description="Proximity level: 'high', 'medium', or 'low'"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of the proximity assessment"
    )

def check_proximity(state: dict[str, Any]) -> dict[str, Any]:
    """
    Checks the proximity between the original question and the discovered root problem.
    
    Returns:
        - proximity_score: float between 0.0 and 1.0
        - proximity_level: 'high', 'medium', or 'low'
        - reasoning: explanation of the assessment
    """
    try:
        original_question = state.get("original_question", "")
        root_problem = state.get("root_problem", "")
        
        if not original_question or not root_problem:
            return {
                **state,
                "proximity_score": 0.0,
                "proximity_level": "low",
                "reasoning": "Missing original question or root problem for comparison"
            }
        
        # Use LLM to analyze proximity
        proximity_llm = llm.with_structured_output(ProximityAnalysis)
        
        analysis_prompt = f"""
        You are a proximity analyzer. Your task is to assess how closely related the original user question is to the discovered root problem.
        
        Original Question: {original_question}
        
        Discovered Root Problem: {root_problem}
        
        Your task:
        1. Analyze the semantic relationship between the original question and the root problem
        2. Determine if they are addressing the same underlying issue
        3. Provide a proximity score (0.0 to 1.0) where:
           - 1.0 = Directly related, same core issue
           - 0.7-0.9 = Highly related, closely connected
           - 0.4-0.6 = Moderately related, some connection
           - 0.1-0.3 = Loosely related, minimal connection
           - 0.0 = Unrelated, different issues
        4. Classify as 'high' (>=0.7), 'medium' (0.4-0.6), or 'low' (<0.4)
        5. Provide clear reasoning for your assessment
        
        Consider:
        - Are they asking about the same domain/topic?
        - Do they share similar intent or goals?
        - Is the root problem a natural evolution of the original question?
        - Are the solutions likely to be similar?
        
        Be objective and precise in your assessment.
        """
        
        result = proximity_llm.invoke([
            {"role": "system", "content": analysis_prompt}
        ])
        
        return {
            **state,
            "proximity_score": result.proximity_score,
            "proximity_level": result.proximity_level,
            "proximity_reasoning": result.reasoning
        }
        
    except Exception as e:
        print(f"Error in proximity checking: {e}")
        return {
            **state,
            "proximity_score": 0.0,
            "proximity_level": "low",
            "proximity_reasoning": f"Error in proximity analysis: {str(e)}"
        }

def should_store_qa(state: dict[str, Any]) -> dict[str, Any]:
    """
    Determines whether to store the Q&A pair based on proximity.
    High proximity = store in Vector DB and update Knowledge Graph
    Low proximity = send response only, no storage
    """
    proximity_score = state.get("proximity_score", 0.0)
    proximity_level = state.get("proximity_level", "low")
    
    # High proximity (>=0.7) means we should store the Q&A pair
    should_store = proximity_score >= 0.7
    
    return {
        **state,
        "should_store_qa": should_store,
        "storage_reason": f"Proximity {proximity_level} (score: {proximity_score:.2f})"
    }
