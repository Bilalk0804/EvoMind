#!/usr/bin/env python3
"""
Debug script to check what's currently in the Knowledge Graph
and clear old data if needed.
"""

from KG.kg_builder import RobustKnowledgeGraphBuilder, get_credentials_from_env

def debug_kg_state():
    """Check current state of Knowledge Graph"""
    try:
        print("🔍 DEBUGGING KNOWLEDGE GRAPH STATE")
        print("=" * 50)
        
        # Initialize KG builder
        groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
        kg_builder = RobustKnowledgeGraphBuilder(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)
        
        # Check all nodes in the database
        all_nodes_query = """
        MATCH (n)
        RETURN labels(n)[0] as node_type, count(n) as count
        ORDER BY count DESC
        """
        
        node_results = kg_builder.graph.query(all_nodes_query)
        
        print("📊 ALL NODES IN DATABASE:")
        print("-" * 30)
        total_nodes = 0
        for result in node_results:
            print(f"{result['node_type']}: {result['count']} nodes")
            total_nodes += result['count']
        print(f"TOTAL: {total_nodes} nodes")
        
        if total_nodes == 0:
            print("✅ Database is empty - no old data")
            return
        
        # Check all relationships
        all_rels_query = """
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(r) as count
        ORDER BY count DESC
        """
        
        rel_results = kg_builder.graph.query(all_rels_query)
        
        print("\n🔗 ALL RELATIONSHIPS IN DATABASE:")
        print("-" * 35)
        total_rels = 0
        for result in rel_results:
            print(f"{result['rel_type']}: {result['count']} relationships")
            total_rels += result['count']
        print(f"TOTAL: {total_rels} relationships")
        
        # Show recent sessions
        recent_sessions_query = """
        MATCH (s:Session)
        RETURN s.session_id, s.original_concern, s.timestamp
        ORDER BY s.timestamp DESC
        LIMIT 5
        """
        
        sessions = kg_builder.graph.query(recent_sessions_query)
        
        if sessions:
            print("\n💬 RECENT SESSIONS:")
            print("-" * 20)
            for session in sessions:
                print(f"- {session['s.session_id']}: {session['s.original_concern']}")
                print(f"  Time: {session['s.timestamp']}")
        
        # Show recent Q&A pairs
        recent_qa_query = """
        MATCH (q:Question)-[:ANSWERED_BY]->(a:Answer)
        RETURN q.text as question, a.text as answer, q.timestamp
        ORDER BY q.timestamp DESC
        LIMIT 5
        """
        
        qa_pairs = kg_builder.graph.query(recent_qa_query)
        
        if qa_pairs:
            print("\n❓ RECENT Q&A PAIRS:")
            print("-" * 20)
            for qa in qa_pairs:
                print(f"Q: {qa['question'][:60]}...")
                print(f"A: {qa['answer'][:60]}...")
                print(f"Time: {qa['q.timestamp']}")
                print()
        
        # Test what analyze_therapy_patterns returns
        print("\n🧠 TESTING PATTERN ANALYSIS:")
        print("-" * 30)
        
        # Test with default user
        kg_context = kg_builder.analyze_therapy_patterns("current_session", [], "default_user")
        
        if kg_context:
            print("PATTERN ANALYSIS RESULT:")
            print(kg_context[:500] + "..." if len(kg_context) > 500 else kg_context)
        else:
            print("No pattern analysis context returned")
        
        # Ask user if they want to clear the database
        print(f"\n🧹 DATABASE CLEANUP OPTIONS:")
        print("1. Clear ALL data (fresh start)")
        print("2. Keep data (for analysis)")
        print("3. Exit without changes")
        
        choice = input("Enter choice (1/2/3): ").strip()
        
        if choice == "1":
            print("Clearing all data...")
            clear_query = "MATCH (n) DETACH DELETE n"
            kg_builder.graph.query(clear_query)
            print("✅ Database cleared successfully")
        elif choice == "2":
            print("✅ Keeping existing data")
        else:
            print("✅ No changes made")
        
    except Exception as e:
        print(f"❌ Error debugging KG state: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_kg_state()
