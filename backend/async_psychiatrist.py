#!/usr/bin/env python3
"""
Async Psychiatrist System
LLM1 (Counselor) and LLM2 (Analyst) work simultaneously for real-time conversation.
"""
import asyncio
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

from models.llm import llm
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from vector_db.vector_manager import get_vector_db_manager

@dataclass
class ConversationState:
    """Shared state between LLM1 and LLM2"""
    messages: List[Any] = field(default_factory=list)
    qa_pairs: List[Dict[str, str]] = field(default_factory=list)
    original_question: str = ""
    
    # LLM2 Analysis Results
    root_problem_found: bool = False
    root_problem: str = ""
    confidence: float = 0.0
    psychological_pattern: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    
    # Control flags
    conversation_active: bool = True
    llm2_analyzing: bool = False
    
    def add_qa_pair(self, question: str, answer: str):
        """Add Q&A pair and trigger LLM2 analysis"""
        self.qa_pairs.append({"question": question, "answer": answer})
        print(f"📝 Added Q&A pair #{len(self.qa_pairs)}")

class CounselorQuestion(BaseModel):
    question: str = Field(..., description="One empathetic counselor question")

class PsychologicalAnalysis(BaseModel):
    root_problem: str = Field(..., description="Root psychological problem if found")
    problem_discovered: bool = Field(..., description="Whether root problem found with 85%+ confidence")
    confidence: float = Field(..., description="Confidence level 0.0-1.0")
    psychological_pattern: str = Field(..., description="Psychological pattern identified")
    supporting_evidence: List[str] = Field(..., description="Evidence from conversation")

class AsyncPsychiatrist:
    """Async psychiatrist with LLM1 and LLM2 working simultaneously"""
    
    def __init__(self):
        self.state = ConversationState()
        self.llm2_thread = None
        self.vector_db = None
        
    def initialize(self):
        """Initialize the system"""
        try:
            self.vector_db = get_vector_db_manager()
            print("✅ Async Psychiatrist System initialized")
        except Exception as e:
            print(f"⚠️ Vector DB initialization failed: {e}")
            self.vector_db = None
    
    def start_llm2_background_analysis(self):
        """Start LLM2 in background thread"""
        if self.llm2_thread and self.llm2_thread.is_alive():
            return
            
        self.llm2_thread = threading.Thread(target=self._llm2_background_worker, daemon=True)
        self.llm2_thread.start()
        print("🧠 LLM2 background analyst started")
    
    def _llm2_background_worker(self):
        """LLM2 background worker - analyzes conversation continuously"""
        last_analyzed_count = 0
        
        while self.state.conversation_active:
            try:
                # Check if new Q&A pairs to analyze
                current_count = len(self.state.qa_pairs)
                
                if current_count > last_analyzed_count and current_count >= 2:
                    print(f"🔍 LLM2 analyzing {current_count} Q&A pairs...")
                    self.state.llm2_analyzing = True
                    
                    # Analyze current conversation
                    analysis = self._analyze_conversation()
                    
                    if analysis and analysis.problem_discovered and analysis.confidence >= 0.85:
                        # Root problem found!
                        self.state.root_problem_found = True
                        self.state.root_problem = analysis.root_problem
                        self.state.confidence = analysis.confidence
                        self.state.psychological_pattern = analysis.psychological_pattern
                        self.state.supporting_evidence = analysis.supporting_evidence
                        
                        print(f"🎯 LLM2 FOUND ROOT PROBLEM: {analysis.root_problem} (Confidence: {analysis.confidence:.0%})")
                        break
                    else:
                        print(f"🔍 LLM2: Not confident yet (Confidence: {analysis.confidence:.0%})")
                    
                    last_analyzed_count = current_count
                    self.state.llm2_analyzing = False
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"❌ LLM2 analysis error: {e}")
                self.state.llm2_analyzing = False
                time.sleep(2)
    
    def _analyze_conversation(self) -> Optional[PsychologicalAnalysis]:
        """LLM2 analyzes the current conversation"""
        if len(self.state.qa_pairs) < 2:
            return None
            
        # Build context from Q&A pairs
        context = f"Original question: {self.state.original_question}\n\n"
        context += "Conversation analysis:\n"
        for i, qa in enumerate(self.state.qa_pairs, 1):
            context += f"{i}. Q: {qa['question']}\n"
            context += f"   A: {qa['answer']}\n\n"
        
        try:
            psychology_llm = llm.with_structured_output(PsychologicalAnalysis)
            
            result = psychology_llm.invoke([{
                "role": "system",
                "content": f"""
                You are LLM2, a psychological analyst. Analyze this conversation to find the ROOT PSYCHOLOGICAL PROBLEM.
                
                CRITICAL RULES:
                1. Only mark as discovered if confidence >= 0.85 (be very strict)
                2. Look for psychological patterns: anxiety, depression, trauma, attachment issues
                3. If not 85%+ confident, return problem_discovered=False
                
                Conversation to analyze:
                {context}
                
                Examples of root problems:
                - Attachment anxiety from childhood abandonment
                - Depression from unprocessed grief  
                - Social anxiety from past trauma
                - Perfectionism masking fear of rejection
                
                Be strict - only diagnose when very confident.
                """
            }])
            
            return result
            
        except Exception as e:
            print(f"❌ LLM2 analysis failed: {e}")
            return None
    
    def ask_next_question(self, user_input: str = None) -> str:
        """LLM1 asks the next counselor question"""
        if user_input:
            # Add user's answer to the last question
            if self.state.qa_pairs:
                # This is an answer to previous question
                last_qa = self.state.qa_pairs[-1]
                if "answer" not in last_qa or not last_qa["answer"]:
                    last_qa["answer"] = user_input
            else:
                # This is the original question
                self.state.original_question = user_input
        
        # Check if LLM2 found the root problem
        if self.state.root_problem_found:
            return self._generate_final_diagnosis()
        
        # Generate next question with LLM1
        try:
            counselor_llm = llm.with_structured_output(CounselorQuestion)
            
            # Build conversation context
            conversation_context = ""
            if self.state.qa_pairs:
                conversation_context = "\nPrevious conversation:\n"
                for i, qa in enumerate(self.state.qa_pairs, 1):
                    conversation_context += f"Q{i}: {qa.get('question', '')}\n"
                    conversation_context += f"A{i}: {qa.get('answer', '')}\n"
            
            result = counselor_llm.invoke([{
                "role": "system", 
                "content": f"""
                You are LLM1, a professional psychiatrist. Ask ONE empathetic question to understand the user's psychological state.
                
                Original concern: {self.state.original_question}
                {conversation_context}
                
                Ask ONE therapeutic question that builds on previous answers to uncover the psychological root cause.
                Be empathetic, professional, and focus on emotions and psychological patterns.
                """
            }])
            
            # Add question to conversation
            question = result.question
            self.state.qa_pairs.append({"question": question, "answer": ""})
            
            return question
            
        except Exception as e:
            return f"I'm having trouble generating the next question. Can you tell me more about how you're feeling?"
    
    def _generate_final_diagnosis(self) -> str:
        """Generate final psychiatric diagnosis and advice"""
        try:
            prompt = f"""
            You are LLM1, a psychiatrist delivering a diagnosis. LLM2 found the root psychological problem.
            
            DIAGNOSIS FROM LLM2:
            Root Problem: {self.state.root_problem}
            Psychological Pattern: {self.state.psychological_pattern}
            Confidence: {self.state.confidence:.0%}
            Evidence: {', '.join(self.state.supporting_evidence)}
            
            Deliver this like a real psychiatric consultation:
            1. "Based on our conversation, I've identified..."
            2. Explain the psychological pattern
            3. Provide 3-5 specific therapeutic tasks/exercises
            4. Offer hope and reassurance
            
            Be professional, empathetic, and actionable.
            """
            
            response = llm.invoke([{"role": "system", "content": prompt}])
            self.state.conversation_active = False
            return response.content
            
        except Exception as e:
            return f"Based on our conversation, you appear to be dealing with {self.state.root_problem}. I recommend seeking professional help to work through this together."

def main():
    """Main async psychiatrist conversation"""
    psychiatrist = AsyncPsychiatrist()
    psychiatrist.initialize()
    
    print("🧠 Async Psychiatrist System")
    print("=" * 50)
    print("LLM1 will ask questions while LLM2 analyzes in the background")
    print("=" * 50)
    
    # Get initial user input
    user_input = input("\n💬 What's on your mind today? ").strip()
    if not user_input:
        return
    
    # Start background analysis
    psychiatrist.start_llm2_background_analysis()
    
    # First question
    question = psychiatrist.ask_next_question(user_input)
    print(f"\n🤖 {question}")
    
    # Conversation loop
    while psychiatrist.state.conversation_active and not psychiatrist.state.root_problem_found:
        # Get user answer
        user_answer = input("\n💭 Your answer: ").strip()
        
        if user_answer.lower() in ['exit', 'quit', 'q']:
            break
        
        if not user_answer:
            print("Please provide an answer to continue.")
            continue
        
        # Update the last Q&A pair with the answer
        if psychiatrist.state.qa_pairs:
            psychiatrist.state.qa_pairs[-1]["answer"] = user_answer
        
        # Check if LLM2 found the problem
        if psychiatrist.state.root_problem_found:
            final_response = psychiatrist._generate_final_diagnosis()
            print(f"\n🎯 FINAL DIAGNOSIS:\n{final_response}")
            break
        
        # Ask next question
        next_question = psychiatrist.ask_next_question()
        print(f"\n🤖 {next_question}")
    
    print("\n👋 Session complete. Take care!")

if __name__ == "__main__":
    main()
