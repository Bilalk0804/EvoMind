#!/usr/bin/env python3
"""
LLM2: Problem Extractor
LLM2 processes the Knowledge Graph to try to extract the root problem from Q&A pairs.
Makes Decision 1: If root problem not discovered → asks for more info → LLM1 generates more questions.
If root problem discovered → checks proximity between problem and original question.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from models.llm import llm
from KG.kg_query import RobustKnowledgeGraphQuery, get_credentials_from_env

# Lazy import to avoid heavy init at import time
_QUERY_SYSTEM = None

class PsychologicalAnalysis(BaseModel):
    root_problem: str = Field(
        ...,
        description="The core psychological/emotional root problem identified from the Q&A pairs"
    )
    problem_discovered: bool = Field(
        ...,
        description="Whether a clear psychological root problem was discovered with high confidence"
    )
    confidence: float = Field(
        ...,
        description="Confidence level (0.0-1.0) in the psychological problem identification. Must be >= 0.85 to be considered discovered"
    )
    psychological_pattern: str = Field(
        ...,
        description="The underlying psychological pattern or mental health aspect identified"
    )
    supporting_evidence: List[str] = Field(
        ...,
        description="List of evidence from the conversation that supports this psychological analysis"
    )
    recommended_approach: str = Field(
        default="",
        description="Brief therapeutic approach or intervention type recommended"
    )

def _get_query_system():
    """Get or create the Knowledge Graph query system."""
    global _QUERY_SYSTEM
    if _QUERY_SYSTEM is None:
        try:
            groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
            _QUERY_SYSTEM = RobustKnowledgeGraphQuery(
                groq_api_key=groq_api_key,
                neo4j_uri=neo4j_uri,
                neo4j_username=neo4j_username,
                neo4j_password=neo4j_password,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize KG query system: {e}")
    return _QUERY_SYSTEM

def extract_root_problem(state: dict[str, Any]) -> dict[str, Any]:
    """
    LLM2: Processes the Knowledge Graph to extract the root problem.
    
    This function:
    1. Queries the Knowledge Graph for relevant information from Q&A pairs
    2. Uses LLM2 to analyze the data and identify the root problem
    3. Returns whether a problem was discovered and with what confidence
    """
    try:
        # Get Q&A pairs from state
        qa_pairs = state.get("qa_pairs", [])
        original_question = state.get("original_question", "")
        
        if not qa_pairs:
            # No Q&A pairs to analyze
            return {
                **state,
                "root_problem": "",
                "problem_discovered": False,
                "confidence": 0.0,
                "supporting_evidence": []
            }
        
        # Query Knowledge Graph for relevant information
        query_system = _get_query_system()
        
        # Create a comprehensive query from all Q&A pairs
        combined_context = f"Original question: {original_question}\n\n"
        combined_context += "Q&A pairs to analyze:\n"
        for i, qa_pair in enumerate(qa_pairs, 1):
            combined_context += f"{i}. Q: {qa_pair.get('question', '')}\n"
            combined_context += f"   A: {qa_pair.get('answer', '')}\n\n"
        
        # Query the Knowledge Graph for related information
        kg_result = query_system.query(combined_context)
        kg_context = kg_result.get("answer", "")
        kg_confidence = kg_result.get("confidence", 0.0)
        
        # Validate input before sending to LLM2
        if not combined_context.strip() or len(combined_context.strip()) < 10:
            return {
                **state,
                "root_problem": "",
                "problem_discovered": False,
                "confidence": 0.0,
                "supporting_evidence": [],
                "error": "Insufficient context for problem analysis"
            }
        
        # Use LLM2 to analyze and extract the root psychological problem
        psychology_llm = llm.with_structured_output(PsychologicalAnalysis)
        
        analysis_prompt = f"""
        You are LLM2, a professional psychological analyst AI. Your role is to analyze conversation patterns and identify the ROOT PSYCHOLOGICAL PROBLEM.
        
        CRITICAL RULES:
        1. You are looking for PSYCHOLOGICAL/EMOTIONAL root causes, not surface problems
        2. Only mark as "discovered" if confidence >= 0.85 (be very strict)
        3. Focus on mental health patterns, emotional triggers, psychological defense mechanisms
        4. Look for underlying trauma, attachment issues, cognitive distortions, or behavioral patterns
        5. If you're not 85%+ confident, return problem_discovered=False
        
        Your analysis approach:
        - Identify emotional patterns and triggers
        - Look for signs of anxiety, depression, trauma, attachment issues
        - Analyze coping mechanisms and defense strategies
        - Identify cognitive distortions or limiting beliefs
        - Look for relationship patterns and social dynamics
        - Consider developmental or childhood influences
        
        Q&A Conversation Analysis:
        {combined_context}
        
        Knowledge Graph Context:
        {kg_context if kg_context else "No additional psychological context available"}
        
        Knowledge Graph Confidence: {kg_confidence}
        
        IMPORTANT: Only set problem_discovered=True if you can identify a clear psychological root cause with 85%+ confidence. 
        If you need more information to understand the psychological pattern, set problem_discovered=False.
        
        Examples of psychological root problems:
        - Attachment anxiety from childhood abandonment
        - Perfectionism masking fear of rejection
        - Depression stemming from unprocessed grief
        - Social anxiety from past trauma or bullying
        - Codependency patterns in relationships
        - Imposter syndrome from low self-worth
        
        Be a strict psychological analyst - only diagnose when you're very confident.
        """
        
        # Validate prompt content
        if not analysis_prompt.strip():
            raise ValueError("Empty analysis prompt generated")
        
        result = psychology_llm.invoke([
            {"role": "system", "content": analysis_prompt}
        ])
        
        # Enforce strict confidence threshold
        problem_discovered = result.problem_discovered and result.confidence >= 0.85
        
        return {
            **state,
            "root_problem": result.root_problem,
            "problem_discovered": problem_discovered,
            "confidence": result.confidence,
            "psychological_pattern": result.psychological_pattern,
            "supporting_evidence": result.supporting_evidence,
            "recommended_approach": result.recommended_approach,
            "kg_context": kg_context,
            "kg_confidence": kg_confidence
        }
        
    except Exception as e:
        print(f"Error in problem extraction: {e}")
        return {
            **state,
            "root_problem": "",
            "problem_discovered": False,
            "confidence": 0.0,
            "supporting_evidence": [],
            "error": str(e)
        }

def needs_more_info(state: dict[str, Any]) -> dict[str, Any]:
    """
    Determines if more information is needed based on psychological problem discovery.
    This is used in the decision flow - LLM1 continues asking until LLM2 is confident.
    """
    problem_discovered = state.get("problem_discovered", False)
    confidence = state.get("confidence", 0.0)
    
    # If psychological problem is not discovered or confidence is below 85%, we need more info
    needs_more = not problem_discovered or confidence < 0.85
    
    return {
        **state,
        "needs_more_info": needs_more
    }
