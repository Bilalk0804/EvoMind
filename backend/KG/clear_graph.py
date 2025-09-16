#!/usr/bin/env python3
"""
Utility script to completely clear the Neo4j knowledge graph.
This will remove all nodes, relationships, and reset the database.
"""
import os
import sys
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

# Load environment variables
load_dotenv()

def clear_knowledge_graph():
    """Clear all data from the Neo4j knowledge graph."""
    try:
        # Get credentials from environment
        neo4j_uri = os.getenv('NEO4J_URI')
        neo4j_username = os.getenv('NEO4J_USERNAME', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        if not all([neo4j_uri, neo4j_password]):
            print("❌ Missing Neo4j credentials in .env file")
            print("Required: NEO4J_URI, NEO4J_PASSWORD")
            return False
        
        print("🔗 Connecting to Neo4j database...")
        
        # Connect to Neo4j
        graph = Neo4jGraph(
            url=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password
        )
        
        print("✅ Connected to Neo4j successfully")
        
        # Get current stats before clearing
        print("\n📊 Current database statistics:")
        try:
            node_count = graph.query("MATCH (n) RETURN count(n) as count")[0]['count']
            rel_count = graph.query("MATCH ()-[r]->() RETURN count(r) as count")[0]['count']
            print(f"   Nodes: {node_count}")
            print(f"   Relationships: {rel_count}")
        except Exception as e:
            print(f"   Could not get statistics: {e}")
        
        # Confirm deletion
        if node_count > 0 or rel_count > 0:
            confirm = input(f"\n⚠️  This will permanently delete ALL data from the knowledge graph.\n   Continue? (yes/no): ").strip().lower()
            
            if confirm != 'yes':
                print("❌ Operation cancelled")
                return False
        
        print("\n🗑️  Clearing knowledge graph...")
        
        # Delete all nodes and relationships
        # This query deletes all nodes and their relationships
        graph.query("MATCH (n) DETACH DELETE n")
        
        # Clear any remaining constraints and indexes (optional)
        try:
            # Drop all constraints
            constraints = graph.query("SHOW CONSTRAINTS")
            for constraint in constraints:
                constraint_name = constraint.get('name', '')
                if constraint_name:
                    graph.query(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
            
            # Drop all indexes  
            indexes = graph.query("SHOW INDEXES")
            for index in indexes:
                index_name = index.get('name', '')
                if index_name and index.get('type') != 'LOOKUP':  # Don't drop lookup indexes
                    graph.query(f"DROP INDEX {index_name} IF EXISTS")
                    
        except Exception as e:
            print(f"⚠️  Note: Could not clear all constraints/indexes: {e}")
        
        # Refresh schema
        graph.refresh_schema()
        
        # Verify deletion
        final_node_count = graph.query("MATCH (n) RETURN count(n) as count")[0]['count']
        final_rel_count = graph.query("MATCH ()-[r]->() RETURN count(r) as count")[0]['count']
        
        print("✅ Knowledge graph cleared successfully!")
        print(f"📊 Final statistics:")
        print(f"   Nodes: {final_node_count}")
        print(f"   Relationships: {final_rel_count}")
        
        if final_node_count == 0 and final_rel_count == 0:
            print("🎉 Database is now completely empty")
            return True
        else:
            print("⚠️  Warning: Some data may still remain")
            return False
            
    except Exception as e:
        print(f"❌ Error clearing knowledge graph: {str(e)}")
        return False

def main():
    """Main function."""
    print("🗑️  Neo4j Knowledge Graph Cleaner")
    print("=" * 50)
    
    success = clear_knowledge_graph()
    
    if success:
        print("\n✅ Operation completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Operation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
