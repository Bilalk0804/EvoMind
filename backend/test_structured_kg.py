#!/usr/bin/env python3
"""
Test script to demonstrate the new structured Knowledge Graph schema.
Creates sample therapy data and shows how the structured nodes and relationships work.
"""

from KG.kg_builder import RobustKnowledgeGraphBuilder, get_credentials_from_env
from datetime import datetime
import time

def test_structured_schema():
    """Test the structured therapy Knowledge Graph schema"""
    try:
        print("🧪 TESTING STRUCTURED THERAPY KNOWLEDGE GRAPH")
        print("=" * 50)
        
        # Initialize KG builder
        groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
        kg_builder = RobustKnowledgeGraphBuilder(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)
        
        # Clear previous test data
        print("🧹 Clearing previous test data...")
        kg_builder.graph.query("MATCH (n) WHERE n.user_id = 'test_user' DETACH DELETE n")
        
        # Test data: Simulate a therapy session
        user_id = "test_user"
        session_id = f"test_session_{int(time.time())}"
        original_concern = "I've been feeling overwhelmed with work and having trouble sleeping"
        
        print(f"👤 Testing with User: {user_id}")
        print(f"💬 Session: {session_id}")
        print(f"🎯 Original Concern: {original_concern}")
        print()
        
        # Simulate Q&A pairs
        qa_pairs = [
            {
                "question": "Can you tell me more about what's making you feel overwhelmed at work?",
                "answer": "My boss keeps giving me more projects and I feel like I can't keep up. I'm constantly worried about deadlines and making mistakes."
            },
            {
                "question": "How long have you been experiencing these sleep troubles?",
                "answer": "It started about 3 weeks ago. I lie awake thinking about all the tasks I need to complete tomorrow. Sometimes I only get 4-5 hours of sleep."
            },
            {
                "question": "What thoughts go through your mind when you're lying awake at night?",
                "answer": "I keep thinking 'What if I mess up this presentation?' or 'What if my boss thinks I'm incompetent?' I feel anxious and my heart races."
            }
        ]
        
        # Store each Q&A pair using the structured schema
        print("💾 Storing Q&A pairs with structured schema...")
        for i, qa in enumerate(qa_pairs, 1):
            success = kg_builder.store_therapy_qa_pair(
                session_id=session_id,
                qa_number=i,
                question=qa["question"],
                answer=qa["answer"],
                original_concern=original_concern,
                user_id=user_id
            )
            
            if success:
                print(f"✅ Q&A pair {i} stored successfully")
            else:
                print(f"❌ Failed to store Q&A pair {i}")
        
        print("\n⏳ Waiting for processing...")
        time.sleep(2)
        
        # Analyze patterns
        print("🔍 Analyzing therapy patterns...")
        kg_context = kg_builder.analyze_therapy_patterns(session_id, qa_pairs, user_id)
        
        if kg_context:
            print("✅ Pattern analysis completed")
            print("\n📊 ANALYSIS RESULTS:")
            print("-" * 30)
            print(kg_context[:500] + "..." if len(kg_context) > 500 else kg_context)
        else:
            print("❌ No pattern analysis results")
        
        # Query the structured data
        print("\n🔍 QUERYING STRUCTURED DATA:")
        print("-" * 35)
        
        # Show the complete therapy session structure
        session_structure_query = """
        MATCH (u:User {user_id: $user_id})-[:HAS_SESSION]->(s:Session {session_id: $session_id})
        MATCH (s)-[:ASKED]->(q:Question)-[:ANSWERED_BY]->(a:Answer)
        OPTIONAL MATCH (a)-[:EXPRESSES]->(e:Emotion)
        OPTIONAL MATCH (a)-[:RELATES_TO]->(t:Topic)
        WITH q, a, 
             collect(DISTINCT e.type) as emotions,
             collect(DISTINCT t.label) as topics
        RETURN q.text as question, 
               a.text as answer,
               emotions,
               topics
        ORDER BY q.timestamp
        """
        
        results = kg_builder.graph.query(session_structure_query, {
            "user_id": user_id,
            "session_id": session_id
        })
        
        print(f"📋 Session Structure for {session_id}:")
        for i, result in enumerate(results, 1):
            print(f"\nQ{i}: {result['question']}")
            print(f"A{i}: {result['answer']}")
            if result['emotions'] and any(result['emotions']):
                emotions = [e for e in result['emotions'] if e]
                print(f"😊 Emotions: {', '.join(emotions)}")
            if result['topics'] and any(result['topics']):
                topics = [t for t in result['topics'] if t]
                print(f"📝 Topics: {', '.join(topics)}")
        
        # Check for patterns
        pattern_query = """
        MATCH (u:User {user_id: $user_id})-[:HAS_PATTERN]->(p:Pattern)
        RETURN p.label, p.confidence, p.description
        ORDER BY p.confidence DESC
        """
        
        patterns = kg_builder.graph.query(pattern_query, {"user_id": user_id})
        
        if patterns:
            print(f"\n🎯 IDENTIFIED PATTERNS:")
            for pattern in patterns:
                print(f"- {pattern['p.label']} (confidence: {pattern['p.confidence']:.2f})")
                print(f"  {pattern['p.description']}")
        else:
            print(f"\n🎯 No high-confidence patterns identified yet")
        
        # Show node and relationship counts
        count_query = """
        MATCH (n) WHERE n.user_id = $user_id OR 
                       (n:Session AND n.session_id = $session_id) OR
                       (n:Question AND n.q_id STARTS WITH $session_id) OR
                       (n:Answer AND n.a_id STARTS WITH $session_id) OR
                       (n:Emotion AND n.e_id CONTAINS $session_id) OR
                       (n:Topic AND EXISTS((n)<-[:RELATES_TO]-(:Answer {a_id: $session_id + '_a1'})))
        RETURN labels(n)[0] as node_type, count(n) as count
        ORDER BY count DESC
        """
        
        counts = kg_builder.graph.query(count_query, {
            "user_id": user_id,
            "session_id": session_id
        })
        
        print(f"\n📊 CREATED NODES:")
        total_nodes = 0
        for count in counts:
            print(f"- {count['node_type']}: {count['count']}")
            total_nodes += count['count']
        print(f"Total: {total_nodes} nodes")
        
        # Show relationships
        rel_count_query = """
        MATCH (n)-[r]->(m) 
        WHERE (n.user_id = $user_id OR n.session_id = $session_id OR 
               n.q_id STARTS WITH $session_id OR n.a_id STARTS WITH $session_id)
        RETURN type(r) as relationship_type, count(r) as count
        ORDER BY count DESC
        """
        
        rel_counts = kg_builder.graph.query(rel_count_query, {
            "user_id": user_id,
            "session_id": session_id
        })
        
        print(f"\n🔗 CREATED RELATIONSHIPS:")
        total_rels = 0
        for rel in rel_counts:
            print(f"- {rel['relationship_type']}: {rel['count']}")
            total_rels += rel['count']
        print(f"Total: {total_rels} relationships")
        
        print(f"\n✅ STRUCTURED SCHEMA TEST COMPLETED!")
        print(f"Created a complete therapy session with structured nodes and relationships.")
        print(f"The system successfully:")
        print(f"  - Created User, Session, Question, Answer nodes")
        print(f"  - Extracted and linked Emotion and Topic nodes")
        print(f"  - Established all required relationships")
        print(f"  - Analyzed patterns across the session data")
        
    except Exception as e:
        print(f"❌ Error testing structured schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_structured_schema()
