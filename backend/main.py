from graph.agent import build_graph
from langchain_core.messages import HumanMessage
import sys

def main():
    """
    Main entry point for the new conversation flow system.
    
    The system follows this flow:
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
    print("🚀 Starting Enhanced Conversation System")
    print("=" * 50)
    print("This system will:")
    print("1. Analyze your question and ask clarifying questions")
    print("2. Extract the root problem from your responses")
    print("3. Provide either a simple or comprehensive answer based on relevance")
    print("4. Store relevant Q&A pairs for future reference")
    print("=" * 50)
    print()
    
    # Build the conversation graph
    try:
        graph = build_graph()
        print("✅ Conversation graph initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize conversation graph: {e}")
        sys.exit(1)
    
    # Initialize conversation state
    conversation_state = {
        "messages": [],
        "original_question": None,
        "clarifying_questions": None,
        "needs_more_info": None,
        "similar_qa_pairs": None,
        "qa_pairs": None,
        "qa_collected": None,
        "root_problem": None,
        "problem_discovered": None,
        "confidence": None,
        "supporting_evidence": None,
        "kg_context": None,
        "kg_confidence": None,
        "proximity_score": None,
        "proximity_level": None,
        "proximity_reasoning": None,
        "should_store_qa": None,
        "storage_reason": None,
        "final_response": None,
        "response_type": None,
        "kg_ingested": None
    }
    
    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("\n💬 Your question: ").strip()
            
            if not user_input:
                print("Please enter a question.")
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            
            # Add user message to conversation
            conversation_state["messages"].append(HumanMessage(content=user_input))
            
            print("\n🤔 Processing your question...")
            print("🔍 Analyzing with LLM1 and querying vector database...")
            
            # Interactive conversation flow
            current_state = conversation_state
            max_questions = 5
            questions_asked = 0
            
            while questions_asked < max_questions:
                # Run one step of the graph
                try:
                    result_state = graph.invoke(current_state)
                    
                    # Check if we got a response that needs user input
                    if result_state.get("response_type") == "asking_for_more_info":
                        # Display the question to user
                        if result_state.get("messages"):
                            last_message = result_state["messages"][-1]
                            print(f"\n🤖 {last_message.content}")
                        
                        # Get user's answer
                        user_answer = input("\n💭 Your answer: ").strip()
                        
                        if user_answer.lower() in ['exit', 'quit', 'q']:
                            print("👋 Goodbye!")
                            return
                        
                        if not user_answer:
                            print("Please provide an answer to continue.")
                            continue
                        
                        # Add user's answer to conversation
                        result_state["messages"].append(HumanMessage(content=user_answer))
                        current_state = result_state
                        questions_asked += 1
                        
                    else:
                        # We got a final response, break out of question loop
                        current_state = result_state
                        break
                        
                except Exception as e:
                    print(f"❌ Error during conversation: {e}")
                    break
            
            # Display the final response
            if current_state.get("messages") and len(current_state["messages"]) > 0:
                final_message = current_state["messages"][-1]
                if current_state.get("response_type") != "asking_for_more_info":
                    print(f"\n🤖 Final Response: {final_message.content}")
            
            # Show system insights (for debugging/transparency)
            if current_state.get("response_type"):
                print(f"\n📊 Response Type: {current_state['response_type']}")
            
            if current_state.get("root_problem"):
                print(f"🎯 Root Problem: {current_state['root_problem']}")
            
            if current_state.get("proximity_score") is not None:
                print(f"🔗 Proximity Score: {current_state['proximity_score']:.2f} ({current_state.get('proximity_level', 'unknown')})")
            
            if current_state.get("should_store_qa"):
                print(f"💾 Stored in database: {current_state.get('storage_reason', 'High proximity')}")
            else:
                print("📝 Not stored (low proximity to original question)")
            
            # Reset for next conversation
            conversation_state = {
                "messages": [],
                "original_question": None,
                "clarifying_questions": None,
                "current_question_index": 0,
                "conversation_memory": None,
                "answered_questions": None,
                "needs_more_info": None,
                "similar_qa_pairs": None,
                "qa_pairs": None,
                "qa_collected": None,
                "root_problem": None,
                "problem_discovered": None,
                "confidence": None,
                "supporting_evidence": None,
                "kg_context": None,
                "kg_confidence": None,
                "proximity_score": None,
                "proximity_level": None,
                "proximity_reasoning": None,
                "should_store_qa": None,
                "storage_reason": None,
                "final_response": None,
                "response_type": None,
                "kg_ingested": None
            }
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("Please try again with a different question.")
            continue

if __name__ == "__main__":
    main()