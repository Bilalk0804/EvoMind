#!/usr/bin/env python3
"""
Test script to verify all imports are working correctly.
"""
import sys
import traceback

def test_imports():
    """Test all critical imports."""
    print("🧪 Testing imports...")
    
    try:
        print("1. Testing vector database imports...")
        from vector_db.vector_manager import get_vector_db_manager
        print("   ✅ Vector database imports successful")
    except Exception as e:
        print(f"   ❌ Vector database imports failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("2. Testing graph node imports...")
        from graph.nodes.classify_message import classify_message
        from graph.nodes.problem_extractor import extract_root_problem
        from graph.nodes.proximity_checker import check_proximity
        from graph.nodes.response_generator import generate_response_with_insights
        from graph.nodes.qa_collector import collect_qa_pairs
        print("   ✅ Graph node imports successful")
    except Exception as e:
        print(f"   ❌ Graph node imports failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("3. Testing agent imports...")
        from graph.agent import build_graph
        print("   ✅ Agent imports successful")
    except Exception as e:
        print(f"   ❌ Agent imports failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("4. Testing KG imports...")
        from KG.kg_builder import RobustKnowledgeGraphBuilder
        from KG.kg_query import RobustKnowledgeGraphQuery
        print("   ✅ KG imports successful")
    except Exception as e:
        print(f"   ❌ KG imports failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("5. Testing main imports...")
        from main import main
        print("   ✅ Main imports successful")
    except Exception as e:
        print(f"   ❌ Main imports failed: {e}")
        traceback.print_exc()
        return False
    
    print("\n🎉 All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    if not success:
        sys.exit(1)
    print("\n✅ System is ready to run!")
