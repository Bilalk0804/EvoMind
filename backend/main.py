from langchain_core.messages import HumanMessage, AIMessage
import sys
import threading
import re
import json
import os
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

def execute_mcp_tools(response_text: str, state) -> str:
    """Execute MCP tools when AI requests them and return updated response"""
    try:
        # Import MCP tools
        from local_mcp.tools.notion_tools import NotionClientWrapper
        from local_mcp.tools.planning_tools import plan_tasks_tool, add_event_tool
        from datetime import datetime, timedelta
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        notion_token = os.getenv("NOTION_API_KEY")
        default_db = os.getenv("NOTION_DEFAULT_DATABASE_ID")
        
        # Ensure all required attributes exist (backward compatibility)
        state.ensure_attributes()
        
        updated_response = response_text
        
        # Check for ROOT CAUSE ACTION MODE triggers
        root_cause_triggers = [
            "root cause", "core issue", "underlying pattern", "learned very young", 
            "that little child", "stemming from", "childhood", "family patterns",
            "past experience", "early experience"
        ]
        
        has_root_cause = any(trigger in response_text.lower() for trigger in root_cause_triggers)
        conversation_length_trigger = len(state.qa_pairs) >= 6  # After 7-8 exchanges
        
        # Only trigger action mode if not already triggered and conditions are met
        if (has_root_cause or conversation_length_trigger) and not state.action_mode_triggered and "Now that we've identified" not in response_text:
            # AUTO-TRIGGER ACTION MODE when root cause is identified
            action_text = "\n\nNow that we've identified the core issue, let me help you take action:\n"
            
            # Create relevant task based on the root cause context
            if notion_token:
                notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
                
                # Determine task based on context
                if "boundary" in response_text.lower() or "say no" in response_text.lower():
                    task_title = "Practice Boundary Setting"
                    task_content = "Start with small, low-stakes situations to practice saying no. Build confidence gradually."
                elif "childhood" in response_text.lower() or "parent" in response_text.lower():
                    task_title = "Inner Child Work"
                    task_content = "Reflect on childhood patterns and how they show up in current situations."
                elif "perfectionism" in response_text.lower():
                    task_title = "Challenge Perfectionist Thoughts"
                    task_content = "Notice perfectionist thoughts and practice self-compassion."
                else:
                    task_title = "Self-Awareness Practice"
                    task_content = "Daily reflection on patterns identified in our conversation."
                
                # Create task in temporary storage (no database needed)
                task_id = f"task_{len(state.temp_tasks) + 1}"
                temp_task = {
                    "id": task_id,
                    "title": task_title,
                    "content": task_content,
                    "created": datetime.now().isoformat(),
                    "status": "pending"
                }
                state.temp_tasks.append(temp_task)
                
                # Schedule follow-up in temporary storage
                follow_up_date = datetime.now() + timedelta(days=7)
                event_id = f"event_{len(state.temp_events) + 1}"
                temp_event = {
                    "id": event_id,
                    "title": "Follow-up Session - Check Progress",
                    "start": follow_up_date.isoformat(),
                    "end": (follow_up_date + timedelta(hours=1)).isoformat(),
                    "description": f"Review progress on {task_title} and continue therapeutic work",
                    "created": datetime.now().isoformat()
                }
                state.temp_events.append(temp_event)
                
                # Display created items
                action_text += f"✅ Created task: '{task_title}'\n"
                action_text += f"✅ Scheduled follow-up session for {follow_up_date.strftime('%B %d')}\n\n"
                
                # Show task details
                action_text += "📋 **Your New Task:**\n"
                action_text += f"• **{task_title}**\n"
                action_text += f"• {task_content}\n\n"
                
                action_text += "📅 **Upcoming Session:**\n"
                action_text += f"• Follow-up on {follow_up_date.strftime('%B %d at %I:%M %p')}\n"
                action_text += f"• Focus: Review progress on {task_title.lower()}\n\n"
                
                action_text += "💡 **Note:** These items are stored temporarily in this session. "
                
                # Try Notion if configured, but don't fail if not
                if notion_token and default_db and default_db != "YOUR_DATABASE_ID_HERE":
                    try:
                        notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
                        if notion.enabled:
                            notion_result = notion.create_page_tool(title=task_title, content=task_content)
                            if notion_result.get("status") == "created":
                                action_text += "Also saved to your Notion workspace! 🎉"
                            else:
                                action_text += "Notion sync failed, but task is saved in session."
                        else:
                            action_text += "Configure Notion database to sync permanently."
                    except Exception as e:
                        action_text += "Configure Notion database to sync permanently."
                else:
                    action_text += "Configure Notion database to sync permanently."
                
                action_text += "\n\nTake your time with these steps. Real change happens gradually. 💙"
                updated_response += action_text
                # Mark that action mode has been triggered to prevent repetition
                state.action_mode_triggered = True
        
        # Handle user responses after action mode
        user_confirmation_phrases = [
            "yes", "ok", "okay", "sure", "yes create", "yes please", "go ahead", 
            "create the tasks", "create them", "do it", "proceed", "fine"
        ]
        
        user_modification_phrases = [
            "modify", "change", "different", "adjust", "update", "edit", "revise",
            "i want to change", "can we modify", "let's adjust", "different tasks"
        ]
        
        user_continue_phrases = [
            "talk more", "discuss more", "continue", "explore further", "tell me more",
            "can we discuss", "i want to talk", "let's continue", "more questions"
        ]
        
        user_end_phrases = [
            "i'm done", "we're done", "that's enough", "i think we're finished",
            "end conversation", "goodbye", "thanks", "thank you"
        ]
        
        # Check if user wants to modify tasks
        if any(phrase in response_text.lower() for phrase in user_modification_phrases) and state.action_mode_triggered:
            updated_response = "Of course! I'd be happy to help you modify those tasks. What changes would you like to make? We can adjust the tasks, add new ones, or take a different approach entirely. What feels right for you?"
            # Reset action mode to allow new modifications
            state.reset_action_mode()
        
        # Check if user wants to continue conversation
        elif any(phrase in response_text.lower() for phrase in user_continue_phrases) and state.action_mode_triggered:
            updated_response = "Absolutely! I'm here to listen and help you explore this further. What would you like to discuss? Whether it's about the tasks we created, the patterns we discovered, or something else entirely - I'm ready to dive deeper with you."
            # Keep action mode triggered but allow normal conversation
        
        # Check if user wants to end conversation
        elif any(phrase in response_text.lower() for phrase in user_end_phrases):
            updated_response = "I'm really glad we could work through this together. You've shown such courage in exploring these patterns and taking steps toward change. Remember, this journey takes time and you're already making important progress. Take care of yourself, and know that I'm here whenever you need to talk. You're not alone in this. 💙"
        
        # Check if user is confirming task creation
        elif any(phrase in response_text.lower() for phrase in user_confirmation_phrases) and state.action_mode_triggered:
            # User confirmed, actually create the tasks
            if notion_token and state.temp_tasks:
                notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
                created_tasks = []
                for task in state.temp_tasks:
                    if task.get("status") == "pending":
                        result = notion.create_page_tool(title=task["title"], content=task["content"])
                        if result.get("status") == "created":
                            task["status"] = "created"
                            task["notion_id"] = result.get("page_id")
                            created_tasks.append(task["title"])
                
                if created_tasks:
                    updated_response = f"✅ Perfect! I've created {len(created_tasks)} tasks in your Notion workspace:\n"
                    for task_title in created_tasks:
                        updated_response += f"• {task_title}\n"
                    updated_response += "\nYou can find them in your Notion database. How are you feeling about taking these first steps?"
                else:
                    updated_response = "I tried to create the tasks but encountered an issue. Let me know if you'd like to try a different approach."
            else:
                updated_response = "I'd be happy to create those tasks, but I need to set up the Notion connection first. For now, here are the tasks we discussed:\n"
                for task in state.temp_tasks:
                    updated_response += f"• {task['title']}: {task['content']}\n"
                updated_response += "\nHow does this plan feel to you?"
        
        # Handle explicit MCP tool calls
        elif "create_notion_task(" in response_text:
            if notion_token:
                notion = NotionClientWrapper(auth_token=notion_token, default_database_id=default_db)
                title = "Task from AI Chat"
                content = "Task created during conversation"
                result = notion.create_page_tool(title=title, content=content)
                if result.get("status") == "created":
                    updated_response = response_text.replace("create_notion_task(", "✅ Created task in Notion! ")
                else:
                    updated_response = response_text.replace("create_notion_task(", "❌ Failed to create task: ")
            else:
                updated_response = response_text.replace("create_notion_task(", "❌ Notion not configured: ")
        
        elif "plan_tasks(" in response_text:
            goal = "Goal from AI conversation"
            result = plan_tasks_tool(goal=goal, max_steps=5)
            updated_response = response_text.replace("plan_tasks(", f"✅ Created plan with {len(result.get('tasks', []))} steps: ")
        
        elif "add_event(" in response_text:
            now = datetime.now()
            result = add_event_tool(
                title="Event from AI Chat",
                start=now.isoformat(),
                end=(now + timedelta(hours=1)).isoformat(),
                description="Event created during conversation"
            )
            updated_response = response_text.replace("add_event(", "✅ Added event to schedule: ")
        
        return updated_response
        
    except Exception as e:
        print(f"❌ Error executing MCP tools: {e}")
        return response_text

from dotenv import load_dotenv
from KG.kg_builder import RobustKnowledgeGraphBuilder
from langchain_core.documents import Document
import shutil

class CounselorQuestion(BaseModel):
    question: str = Field(..., description="One empathetic counselor question")
    approach: str = Field(..., description="psychological or psychiatric")
    reasoning: str = Field(..., description="Why this approach was chosen")

class PsychologicalAnalysis(BaseModel):
    """Simplified LLM2 analysis - Root cause + Direction for LLM1"""
    root_cause: str = Field(..., description="The core root cause of the user's situation")
    problem_discovered: bool = Field(..., description="Whether root cause found with 90%+ confidence")
    confidence: float = Field(..., description="Confidence level 0.0-1.0")
    llm1_direction: str = Field(..., description="Clear direction for LLM1 on how to help the user with this root cause")

class AsyncState:
    """Shared state for async psychiatrist"""
    def __init__(self):
        self.qa_pairs = []
        self.original_question = ""
        self.conversation_active = True
        self.llm2_analyzing = False
        self.kg_builder = None
        self.session_id = None
        self.llm2_insights = None  # Store LLM2's analysis for LLM1 to use
        self.action_mode_triggered = False  # Track if action mode has been triggered
        self.temp_tasks = []  # Temporary tasks for Notion integration
        self.temp_events = []  # Temporary events for scheduling
    
    def ensure_attributes(self):
        """Ensure all required attributes exist (for backward compatibility)"""
        if not hasattr(self, 'action_mode_triggered'):
            self.action_mode_triggered = False
        if not hasattr(self, 'temp_tasks'):
            self.temp_tasks = []
        if not hasattr(self, 'temp_events'):
            self.temp_events = []
    
    def reset_action_mode(self):
        """Reset action mode to allow new task creation"""
        self.action_mode_triggered = False
        self.temp_tasks = []
        self.temp_events = []

def llm2_background_worker(state: AsyncState, llm=None):
    """LLM2 stores Q&A in KG instantly and analyzes ENTIRE KG for patterns"""
    processed_qa_pairs = set()  # Track which Q&A pairs have been stored
    
    while state.conversation_active:
        try:
            current_count = len(state.qa_pairs)
            
            # Check ALL Q&A pairs for new answers (not just new pairs)
            newly_stored = False
            
            for i, qa in enumerate(state.qa_pairs):
                qa_id = f"{i+1}_{qa.get('question', '')[:20]}"  # Unique ID for each Q&A
                
                # If this Q&A has an answer and hasn't been stored yet
                if qa.get('answer') and qa_id not in processed_qa_pairs:
                    # Quietly store Q&A pair in KG
                    store_single_qa_in_kg(state, qa, i+1)
                    processed_qa_pairs.add(qa_id)
                    newly_stored = True
            
            # Run pattern analysis if we stored new Q&A pairs and have at least 2 total
            answered_pairs = len([qa for qa in state.qa_pairs if qa.get('answer')])
            if newly_stored and answered_pairs >= 2:
                state.llm2_analyzing = True
                analyze_entire_kg_for_patterns(state, llm)
                state.llm2_analyzing = False
            
            time.sleep(1)  # Check every second
            
        except Exception as e:
            print(f"❌ LLM2 worker error: {e}")
            time.sleep(2)

def store_single_qa_in_kg(state: AsyncState, qa_pair: dict, qa_number: int):
    """Store single Q&A pair in KG instantly when user answers"""
    if not state.kg_builder:
        return
    
    try:
        # Use the enhanced kg_builder method with structured schema
        success = state.kg_builder.store_therapy_qa_pair(
            session_id=state.session_id,
            qa_number=qa_number,
            question=qa_pair.get('question', ''),
            answer=qa_pair.get('answer', ''),
            original_concern=state.original_question,
            user_id="default_user"  # Add user_id parameter
        )
        
        if success:
            pass  # Silently stored in KG
        
    except Exception as e:
        print(f"❌ Error storing Q&A in KG: {e}")

def analyze_entire_kg_for_patterns(state: AsyncState, llm=None):
    """LLM2 analyzes ENTIRE KG to find psychological patterns - ONLY after sufficient context is gathered"""
    if not state.kg_builder:
        return
    
    # WAIT FOR SUFFICIENT CONTEXT BEFORE ANALYZING
    min_exchanges = 3  # Minimum number of Q&A exchanges before LLM2 analyzes
    if len(state.qa_pairs) < min_exchanges:
        print(f"🔍 LLM2 waiting for more context ({len(state.qa_pairs)}/{min_exchanges} exchanges)")
        return
    
    try:
        # Use the enhanced kg_builder method to get KG context with structured schema
        kg_context = state.kg_builder.analyze_therapy_patterns(state.session_id, state.qa_pairs, user_id="default_user")
        
        if not kg_context:
            return
        
        # ENHANCED LLM2: Powerful Knowledge Graph Analyst
        psychology_llm = llm.with_structured_output(PsychologicalAnalysis)
        result = psychology_llm.invoke([{
            "role": "user",
            "content": f"""
            You are LLM2, the ROOT CAUSE ANALYST. Your job is simple:
            
            1. FIND THE ROOT CAUSE: Analyze the Knowledge Graph to identify the core issue behind the user's situation
            2. GUIDE LLM1: Tell LLM1 exactly how to help the user address this root cause
            
            KNOWLEDGE GRAPH ANALYSIS:
            {kg_context}
            
            YOUR ANALYSIS:
            🔍 Look at all the conversation patterns, emotions, and relationships in the Knowledge Graph
            🧠 Identify the ONE core root cause that's driving the user's problems
            🎯 Give LLM1 clear, specific direction on how to help the user with this root cause
            
            REQUIREMENTS:
            - Only mark discovered=True if confidence >= 0.90
            - Be specific about the root cause (not vague)
            - Give LLM1 clear direction on what to focus on and how to help
            - Keep it simple and actionable
            """
        }])
        
        if result.problem_discovered and result.confidence >= 0.90:
            # Store LLM2's simplified insights for LLM1 to follow
            state.llm2_insights = {
                "root_cause": result.root_cause,
                "confidence": result.confidence,
                "llm1_direction": result.llm1_direction,
                "analysis_complete": True
            }
            print(f"🎯 LLM2 ROOT CAUSE: {result.root_cause}")
            print(f"🧭 LLM1 DIRECTION: {result.llm1_direction}")
            print(f"📊 Confidence: {result.confidence:.0%}")
            # Continue analysis for updated insights as conversation progresses
        
    except Exception as e:
        print(f"❌ Error analyzing KG: {e}")

def generate_kg_visualization(graph):
    """Generate HTML visualization of the knowledge graph"""
    try:
        # Query recent therapy sessions (avoid property warnings)
        query = """
        MATCH (n)-[r]->(m) 
        RETURN n, r, m 
        LIMIT 50
        """
        
        result = graph.query(query)
        
        # Create simple HTML visualization
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Therapy Knowledge Graph</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .node { background: #e3f2fd; padding: 10px; margin: 5px; border-radius: 5px; }
                .relationship { background: #f3e5f5; padding: 5px; margin: 3px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🧠 Therapy Knowledge Graph</h1>
            <p>Recent therapy sessions and relationships:</p>
        """
        
        for record in result:
            html_content += f'<div class="node">Node: {record.get("n", {})}</div>'
            html_content += f'<div class="relationship">→ {record.get("r", {})} →</div>'
            html_content += f'<div class="node">Node: {record.get("m", {})}</div><hr>'
        
        html_content += """
        </body>
        </html>
        """
        
        # Save to file
        with open("d:/Gen-AI-Exc/backend/KG/.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print("📈 Knowledge Graph visualization updated at KG/.html")
        
    except Exception as e:
        print(f"❌ Error generating visualization: {e}")

def clear_knowledge_graph(kg_builder):
    """Clear all data from Knowledge Graph"""
    try:
        # Delete all nodes and relationships
        clear_query = "MATCH (n) DETACH DELETE n"
        kg_builder.graph.query(clear_query)
        print("✅ Knowledge Graph cleared successfully")
    except Exception as e:
        print(f"❌ Error clearing Knowledge Graph: {e}")

def clear_vector_database():
    """Clear all data from Vector Database"""
    try:
        # Clear vector_db directory
        vector_db_path = "vector_db"
        if os.path.exists(vector_db_path):
            shutil.rmtree(vector_db_path)
            print("✅ Vector Database cleared successfully")
        else:
            print("✅ Vector Database was already empty")
            
        # Also clear any ChromaDB persistent data
        chroma_db_path = "chroma_db"
        if os.path.exists(chroma_db_path):
            shutil.rmtree(chroma_db_path)
            print("✅ ChromaDB cleared successfully")
            
        # Clear any other vector database files
        for db_file in ["vectorstore.db", "embeddings.db", "chroma.sqlite3"]:
            if os.path.exists(db_file):
                os.remove(db_file)
                print(f"✅ {db_file} cleared successfully")
            
    except Exception as e:
        print(f"❌ Error clearing Vector Database: {e}")

def ask_counselor_question(state: AsyncState, user_input: str = None, llm=None) -> str:
    # Ensure all required attributes exist (backward compatibility)
    state.ensure_attributes()
    """LLM1 asks next question quickly, building on previous conversation"""
    
    # If this is a follow-up question, add the user's answer to the last Q&A pair
    if user_input and state.qa_pairs:
        state.qa_pairs[-1]["answer"] = user_input
    
    # Check if user is asking for advice/help
    user_asking_for_help = user_input and any(phrase in user_input.lower() for phrase in [
        "can u suggest", "what should i", "how should i", "tell me what", "give me advice", 
        "help me", "what do you think i should", "what would you recommend", "can u tell me",
        "give me plan", "tell me the plan", "what is the plan", "suggest me something",
        "suggest me", "what can i do", "can u sugeest", "what to do", "give suggestion"
    ])
    
    # Check if user is rejecting previous advice or indicating it won't work
    user_rejecting_advice = user_input and any(phrase in user_input.lower() for phrase in [
        "i cannot", "i can't", "they won't", "it won't work", "they said no", "they told me not to",
        "they previous told", "they would be angry", "they will shout", "that won't work",
        "i tried but", "failed", "same output", "same advice", "not working", "but many",
        "they are like", "will not help", "won't help", "doesn't work"
    ])
    
    # Check if user is providing NEW information about their situation
    user_providing_new_info = user_input and any(phrase in user_input.lower() for phrase in [
        "but", "however", "actually", "the thing is", "my main", "see my", "yes i can do this but",
        "the problem is", "what i really", "my real", "i actually", "to be honest"
    ])
    
    # Build detailed conversation context
    conversation_context = ""
    if state.qa_pairs:
        conversation_context = "\nOur conversation so far:\n"
        for i, qa in enumerate(state.qa_pairs, 1):
            conversation_context += f"Q{i}: {qa.get('question', '')}\n"
            conversation_context += f"A{i}: {qa.get('answer', '')}\n\n"
    
    try:
        # Use regular LLM call instead of structured output to avoid validation errors
        counselor_llm = llm
        
        # Check if LLM2 has provided root cause analysis
        llm2_guidance = ""
        if state.llm2_insights and state.llm2_insights.get('analysis_complete'):
            print(f"🧠 LLM2 ROOT CAUSE ANALYSIS available - Following guidance")
            llm2_guidance = f"""
        
        🧠 BACKGROUND INTELLIGENCE (LLM2 Analysis):
        
        Deep Understanding: {state.llm2_insights['root_cause']}
        Strategic Context: {state.llm2_insights['llm1_direction']}
        Confidence: {state.llm2_insights['confidence']:.0%}
        
        SUBCONSCIOUS GUIDANCE - Let this understanding naturally inform your responses:
        - This analysis provides deeper context about the user's situation
        - Use this insight to make your responses more targeted and helpful
        - Let this understanding guide the tone, direction, and focus of your response
        - Don't explicitly mention this analysis - just let it inform your natural response
        - Respond to the user's current message with this deeper understanding in mind
        - Your responses should feel more insightful because of this background knowledge
        """
        else:
            print("🔍 No LLM2 insights yet - LLM1 operating independently")
        
        # Create BALANCED CONVERSATIONAL prompt based on sample.txt style
        prompt_content = f"""
        You are a skilled counselor who balances insightful observations with strategic questions. Study this conversation style:

        EXAMPLE CONVERSATION FLOW:
        User: "I'm stressed about my engineering exam. I can't focus and feel like giving up."
        Counselor: "That level of stress sounds overwhelming. What happens when you think about not doing well on this exam?"
        User: "My parents will be disappointed. They've sacrificed so much for my coaching."
        Counselor: "It sounds like there's a lot of pressure around not letting your parents down. What would happen if you did disappoint them?"
        User: "They'd still love me, but they've always been proud when I do well in math. It's like that's how they see me."
        Counselor: "So part of this stress might be about maintaining that image of who they think you are. Is that the same image you have of yourself?"

        CURRENT CONVERSATION:
        User just said: "{user_input if user_input else state.original_question}"
        
        {conversation_context}
        {llm2_guidance}

        YOUR RESPONSE STYLE:
        
        🎯 BALANCE: Mix observations with questions (don't just ask questions!)
        
        GOOD PATTERNS:
        ✅ "That level of [emotion] sounds [acknowledgment]. [Strategic question]?"
        ✅ "It sounds like [deeper insight]. [Follow-up question]?"
        ✅ "So [reframe their situation]. [Explore contradiction/deeper layer]?"
        ✅ Make insightful observations that show you understand the deeper dynamics
        ✅ Ask questions that build logically on what they just revealed
        
        BAD PATTERNS:
        ❌ Just asking "How does that make you feel?"
        ❌ Staying surface-level on topics they've rejected
        ❌ Asking multiple questions in one response
        ❌ Being purely question-based without insights
        
        CONVERSATION STRATEGY:
        1. Start with empathetic observation that shows understanding
        2. Identify the deeper dynamic or pattern you're noticing
        3. Ask ONE strategic question that explores the root cause
        4. Build each response on their previous answer
        
        {"🚨 USER REJECTED TOPIC - EXPLORE THE DEEPER 'WHY' BEHIND THE REJECTION!" if user_rejecting_advice else ""}
        {"🚨 USER ASKED FOR HELP - GIVE CONCRETE ADVICE WITH UNDERSTANDING!" if user_asking_for_help else ""}
        
        BE CONVERSATIONAL, INSIGHTFUL, AND STRATEGIC - LIKE THE SAMPLE CONVERSATION.
        
        🔧 SMART ACTION INTEGRATION:
        When giving advice or suggestions, ALSO suggest specific actions:
        ✅ "Let me help you create a structured study plan in your Notion workspace..."
        ✅ "I can schedule specific study sessions for you based on this timeline..."
        ✅ "Would you like me to break this goal into actionable tasks you can track?"
        
        SUGGEST CONCRETE ACTIONS, NOT JUST INSIGHTS!
        
        💬 NATURAL CONVERSATION FLOW:
        - Be warm, empathetic, and human-like
        - Ask follow-up questions to deepen understanding
        - Validate their feelings and experiences
        - Use natural transitions between topics
        - End conversations warmly, not abruptly
        - If they want to change direction, go with them
        - If they want to end, give a supportive closing
        
        🤖 MCP TOOL INTEGRATION:
        When user asks for help with tasks, goals, or scheduling, you can trigger MCP tools:
        - If they want to create a task: Say "I'll create that task for you in Notion" then call create_notion_task()
        - If they want to plan something: Say "Let me break that down into steps" then call plan_tasks()
        - If they want to schedule: Say "I'll add that to your schedule" then call add_event()
        
        USE THESE FUNCTION CALLS WHEN APPROPRIATE:
        - create_notion_task(title, content)
        - plan_tasks(goal, deadline, max_steps)
        - add_event(title, start, end, description)
        
        🎯 AUTOMATIC ACTION MODE TRIGGERS:
        TRIGGER ACTION MODE in these situations:
        1. After 7-8 questions/responses from you (conversation getting long)
        2. When you identify root cause (childhood trauma, family patterns, etc.)
        3. When you mention: "root cause", "core issue", "underlying pattern", "learned very young", "that little child", "stemming from"
        
        ACTION MODE FLOW:
        1. Give your insightful response about the root cause
        2. Add: "Now that we've identified the core issue, let me help you take action:"
        3. Create specific tasks: create_notion_task("Work on boundary setting", "Practice saying no in low-stakes situations")
        4. Schedule follow-up: add_event("Follow-up session", "next week", "Check progress on boundary work")
        
        ⚠️ IMPORTANT: Only trigger action mode ONCE per conversation. After offering action, wait for user response.
        If user confirms (says "yes", "ok", "create them"), then actually create the tasks.
        If user declines or changes topic, continue normal conversation without repeating action offers.
        
        🔄 POST-ACTION MODE FLOW:
        After action mode is triggered and tasks are created/offered:
        1. If user wants to modify tasks: "I'd like to change the tasks" → Return to counselor mode, discuss modifications
        2. If user wants to talk more: "Can we discuss this further?" → Continue normal conversation
        3. If user wants to end: "I think we're done" → Give a warm, supportive closing
        4. If user asks new questions: Answer normally as a counselor, don't repeat action offers
        
        🎯 CONVERSATION ENDING:
        End conversations naturally and warmly:
        - "I'm glad we could work through this together. Remember, change takes time and you're taking important steps."
        - "You've shown real courage in exploring this. Take care of yourself."
        - "I'm here whenever you need to talk. You're not alone in this journey."
        - AVOID abrupt endings like "That's all" or "Goodbye"
        
        CONVERSATION LENGTH CHECK: You are currently on response #{len(state.qa_pairs) + 1}
        {"🚨 TRIGGER ACTION MODE - CONVERSATION IS LONG ENOUGH!" if len(state.qa_pairs) >= 6 and not state.action_mode_triggered else ""}
        {"✅ ACTION MODE ALREADY TRIGGERED - Continue normal conversation, don't repeat action offers." if state.action_mode_triggered else ""}
        """
        
        # LLM1 generates response (guided by LLM2 if available)
        result = counselor_llm.invoke([
            {"role": "user", "content": prompt_content}
        ])
        
        # AGGRESSIVE OVERRIDE: User explicitly asked for suggestions/advice
        if user_asking_for_help:
            print("🔧 OVERRIDE: User asked for help but got question - forcing generic advice response")
            
            # Generate TARGETED advice based on conversation context and LLM2 guidance
            llm2_context = ""
            if state.llm2_insights and state.llm2_insights.get('analysis_complete'):
                llm2_context = f"""
                LLM2 ROOT CAUSE ANALYSIS:
                Root Cause: {state.llm2_insights['root_cause']}
                Direction: {state.llm2_insights['llm1_direction']}
                """
            
            generic_advice_prompt = f"""
            The user is explicitly asking for practical advice/help. Based on the conversation context and LLM2's analysis, provide specific, actionable guidance.
            
            Conversation context:
            {conversation_context}
            
            {llm2_context}
            
            User's current request: {user_input}
            
            RESPONSE STRUCTURE:
            1. Acknowledge their request for help (1 sentence)
            2. Provide concrete, practical advice with specific steps (main part - be detailed!)
            3. End with ONE supportive question to continue the conversation
            
            Give actual actionable steps they can take right now. Be specific and helpful.
            """
            
            # Get generic advice from LLM
            advice_llm = llm
            advice_result = advice_llm.invoke([{"role": "user", "content": generic_advice_prompt}])
            question = advice_result.content
            approach = "PSYCHOLOGICAL"
        else:
            # Normal response flow
            result = counselor_llm.invoke([{"role": "user", "content": prompt_content}])
            question = result.content.strip()
            approach = "PSYCHOLOGICAL"
        
        response_text = result.content
        
        # Check if AI wants to use MCP tools and execute them
        if "create_notion_task(" in response_text:
            response_text = execute_mcp_tools(response_text, state)
        elif "plan_tasks(" in response_text:
            response_text = execute_mcp_tools(response_text, state)
        elif "add_event(" in response_text:
            response_text = execute_mcp_tools(response_text, state)
        
        # Store the Q&A pair
        state.qa_pairs.append({
            "question": user_input if user_input else state.original_question,
            "answer": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return response_text
        
        # Show approach indicator (brief)
        approach_icon = "🧠" if approach.lower() == "psychological" else "🏥"
        print(f"{approach_icon} [{approach.upper()}]")
        
        
    except Exception as e:
        print(f"❌ Error generating question: {e}")
        # Fallback question based on conversation length
        if len(state.qa_pairs) == 0:
            return "Can you tell me more about what's making you feel tired?"
        elif len(state.qa_pairs) == 1:
            return "When did you first start noticing these feelings?"
        else:
            return "What do you think might be contributing to how you're feeling?"

def generate_final_diagnosis(state: AsyncState) -> str:
    """Generate final diagnosis when LLM2 finds root problem"""
    try:
        prompt = f"""
        You are LLM1, delivering a psychiatric diagnosis. LLM2 found the root problem.
        
        DIAGNOSIS:
        Root Problem: {state.root_problem}
        Pattern: {state.psychological_pattern}
        Confidence: {state.confidence:.0%}
        
        Deliver like a real psychiatrist:
        1. "Based on our conversation, I've identified..."
        2. Explain the pattern
        3. Give 3-5 therapeutic tasks
        4. Offer hope
        """
        
        response = llm.invoke([{"role": "user", "content": prompt}])
        return response.content
        
    except Exception as e:
        return f"Based on our conversation, you're dealing with {state.root_problem}. I recommend working on this with therapeutic exercises."

def main():
    """
    Async Psychiatrist System - LLM1 asks questions while LLM2 analyzes in background
    """
    print("🧠 Universal AI Assistant System")
    print("=" * 50)
    print("LLM1 (Conversational AI) provides helpful guidance on ANY topic")
    print("LLM2 (Analyst) works in background to understand patterns and provide insights")
    print("System adapts to whatever the user needs help with")
    print("=" * 50)
    print()
    
    # Initialize KG builder and clear previous data
    try:
        load_dotenv()
        groq_api_key = os.getenv('GROQ_API_KEY')
        neo4j_uri = os.getenv('NEO4J_URI')
        neo4j_username = os.getenv('NEO4J_USERNAME')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        # Initialize LLM
        global llm
        llm = ChatGroq(
            api_key=groq_api_key,
            model="gemma2-9b-it",
            temperature=0.7
        )
        
        if all([groq_api_key, neo4j_uri, neo4j_username, neo4j_password]):
            try:
                # Use the enhanced KG builder from KG folder
                kg_builder = RobustKnowledgeGraphBuilder(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)
                print("✅ Enhanced KG Builder with Neo4j initialized")
                
                # Clear previous KG data
                print("🧹 Clearing previous Knowledge Graph data...")
                clear_knowledge_graph(kg_builder)
                print("📊 Knowledge Graph ready for therapy sessions")
                
            except Exception as kg_error:
                print(f"❌ Neo4j connection failed: {kg_error}")
                print("🚫 THERAPY SYSTEM REQUIRES KNOWLEDGE GRAPH - CANNOT CONTINUE")
                print("Please check your Neo4j connection and try again.")
                sys.exit(1)
            
        else:
            print("❌ KG credentials missing in .env file")
            print("🚫 THERAPY SYSTEM REQUIRES KNOWLEDGE GRAPH - CANNOT CONTINUE")
            print("Please add Neo4j credentials to .env file and try again.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ KG initialization failed: {e}")
        print("🚫 THERAPY SYSTEM REQUIRES KNOWLEDGE GRAPH - CANNOT CONTINUE")
        print("Please fix the issue and try again.")
        sys.exit(1)
    
    # Clear Vector Database
    print("🧹 Clearing previous Vector Database data...")
    clear_vector_database()
    
    # Initialize async state
    state = AsyncState()
    state.kg_builder = kg_builder
    
    # Main conversation loop
    while True:
        try:
            # Get initial user input
            user_input = input("\n💬 What's on your mind today? ").strip()
            
            if not user_input:
                print("Please tell me what's bothering you.")
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("👋 Take care!")
                break
            
            # Set original question and start background analysis
            state.original_question = user_input
            state.conversation_active = True
            state.root_problem_found = False
            state.session_id = f"session_{int(time.time())}"  # Generate unique session ID
            
            # Start LLM2 background worker
            llm2_thread = threading.Thread(target=llm2_background_worker, args=(state,), daemon=True)
            llm2_thread.start()
            
            # Generate first question based on user's initial input
            first_question = ask_counselor_question(state)
            print(f"\n🤖 {first_question}")
            
            # Record the user's initial input as answer to an implicit first question
            state.qa_pairs.insert(0, {"question": "What brings you here today?", "answer": user_input})
            
            # Conversation loop - LLM1 asks questions while LLM2 analyzes
            max_questions = 20  # Allow more questions for thorough deep analysis
            questions_asked = 1
            
            while questions_asked < max_questions and state.conversation_active:
                # Get user answer
                user_answer = input("\n💭 Your answer: ").strip()
                
                if user_answer.lower() in ['exit', 'quit', 'q']:
                    state.conversation_active = False
                    break
                
                if not user_answer:
                    print("Please provide an answer to continue.")
                    continue
                
                # LLM2 insights are now handled naturally by LLM1
                # No direct diagnosis output - conversation continues naturally
                
                # Ask next question from LLM1
                next_question = ask_counselor_question(state, user_answer)
                print(f"\n🤖 {next_question}")
                questions_asked += 1
            
            if questions_asked >= max_questions:
                print(f"\n⏰ We've had a thorough conversation. Let me provide some general guidance based on what you've shared.")
                if state.qa_pairs:
                    # Generate a general response
                    general_response = f"Based on our conversation, it seems you're dealing with some challenges. I recommend focusing on self-care and considering speaking with a professional counselor who can provide personalized support."
                    print(f"\n🤖 {general_response}")
            
            # Stop background worker
            state.conversation_active = False
            
            # Generate final KG visualization
            if state.kg_builder:
                print("\n📊 Updating Knowledge Graph visualization...")
                generate_kg_visualization(state.kg_builder.graph)
            
            # Reset for next session
            state = AsyncState()
            state.kg_builder = kg_builder
            
        except KeyboardInterrupt:
            print("\n\n👋 Session ended. Take care!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("Let's try again.")
            continue

if __name__ == "__main__":
    main()