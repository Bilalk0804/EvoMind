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

class ProblemAnalysis(BaseModel):
    root_problem: str = Field(
        ...,
        description="The core root problem identified from the Q&A pairs"
    )
    problem_discovered: bool = Field(
        ...,
        description="Whether a clear root problem was discovered"
    )
    confidence: float = Field(
        ...,
        description="Confidence level (0.0-1.0) in the problem identification"
    )
    supporting_evidence: List[str] = Field(
        ...,
        description="List of evidence from the Knowledge Graph that supports this problem"
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
        
        # Use LLM2 to analyze and extract the root problem
        problem_llm = llm.with_structured_output(ProblemAnalysis)
        
        analysis_prompt = f"""
        You are LLM2, responsible for analyzing Q&A pairs and Knowledge Graph data to identify the root problem.
        
        Your task:
        1. Analyze the Q&A pairs and Knowledge Graph context
        2. Identify the underlying root problem the user is trying to solve
        3. Determine if the problem is clearly identifiable
        4. Provide confidence level and supporting evidence
        
        Q&A Analysis Context:
        {combined_context}
        
        Knowledge Graph Context:
        {kg_context if kg_context else "No additional context available"}
        
        Knowledge Graph Confidence: {kg_confidence}
        
        Guidelines:
        - Look for patterns, themes, and underlying issues in the Q&A pairs
        - Consider the original question and how the answers relate to it
        - Identify the core problem that the user is trying to address
        - Be specific and actionable in your problem identification
        - Only mark as "discovered" if you have high confidence (>=0.7)
        - Provide concrete evidence from the data that supports your analysis
        
        Focus on finding the real underlying issue, not just surface-level questions.
        """
        
        # Validate prompt content
        if not analysis_prompt.strip():
            raise ValueError("Empty analysis prompt generated")
        
        result = problem_llm.invoke([
            {"role": "system", "content": analysis_prompt}
        ])
        
        return {
            **state,
            "root_problem": result.root_problem,
            "problem_discovered": result.problem_discovered,
            "confidence": result.confidence,
            "supporting_evidence": result.supporting_evidence,
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
    Determines if more information is needed based on problem discovery.
    This is used in the decision flow.
    """
    problem_discovered = state.get("problem_discovered", False)
    confidence = state.get("confidence", 0.0)
    
    # If problem is not discovered or confidence is low, we need more info
    needs_more = not problem_discovered or confidence < 0.7
    
    return {
        **state,
        "needs_more_info": needs_more
    }
