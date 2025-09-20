#!/usr/bin/env python3
"""
Visualization script for the structured therapy Knowledge Graph schema.
Shows the node types and relationships as defined in the new schema.
"""

from kg_builder import RobustKnowledgeGraphBuilder, get_credentials_from_env
import json
from datetime import datetime

def visualize_kg_schema():
    """Generate a comprehensive view of the structured Knowledge Graph"""
    try:
        # Get credentials and initialize KG builder
        groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
        kg_builder = RobustKnowledgeGraphBuilder(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)
        
        print("🧠 STRUCTURED THERAPY KNOWLEDGE GRAPH VISUALIZATION")
        print("=" * 60)
        
        # Query to get all node types and their counts
        node_counts_query = """
        MATCH (n)
        RETURN labels(n)[0] as node_type, count(n) as count
        ORDER BY count DESC
        """
        
        node_results = kg_builder.graph.query(node_counts_query)
        
        print("\n📊 NODE TYPES AND COUNTS:")
        print("-" * 30)
        for result in node_results:
            print(f"{result['node_type']}: {result['count']} nodes")
        
        # Query to get all relationship types and their counts
        relationship_counts_query = """
        MATCH ()-[r]->()
        RETURN type(r) as relationship_type, count(r) as count
        ORDER BY count DESC
        """
        
        rel_results = kg_builder.graph.query(relationship_counts_query)
        
        print("\n🔗 RELATIONSHIP TYPES AND COUNTS:")
        print("-" * 35)
        for result in rel_results:
            print(f"{result['relationship_type']}: {result['count']} relationships")
        
        # Show sample data for each node type
        print("\n🔍 SAMPLE DATA BY NODE TYPE:")
        print("-" * 35)
        
        # Users
        user_query = "MATCH (u:User) RETURN u LIMIT 3"
        users = kg_builder.graph.query(user_query)
        if users:
            print("\n👤 USERS:")
            for user in users:
                print(f"  - {user['u']}")
        
        # Sessions
        session_query = """
        MATCH (s:Session) 
        RETURN s.session_id, s.original_concern, s.timestamp 
        ORDER BY s.timestamp DESC 
        LIMIT 3
        """
        sessions = kg_builder.graph.query(session_query)
        if sessions:
            print("\n💬 RECENT SESSIONS:")
            for session in sessions:
                print(f"  - {session['s.session_id']}: {session['s.original_concern'][:50]}...")
        
        # Questions and Answers
        qa_query = """
        MATCH (q:Question)-[:ANSWERED_BY]->(a:Answer)
        RETURN q.text as question, a.text as answer
        ORDER BY q.timestamp DESC
        LIMIT 3
        """
        qa_pairs = kg_builder.graph.query(qa_query)
        if qa_pairs:
            print("\n❓ RECENT Q&A PAIRS:")
            for qa in qa_pairs:
                print(f"  Q: {qa['question'][:60]}...")
                print(f"  A: {qa['answer'][:60]}...")
                print()
        
        # Emotions
        emotion_query = """
        MATCH (e:Emotion)
        RETURN e.type, avg(e.intensity) as avg_intensity, count(e) as frequency
        ORDER BY frequency DESC
        LIMIT 5
        """
        emotions = kg_builder.graph.query(emotion_query)
        if emotions:
            print("\n😊 TOP EMOTIONS:")
            for emotion in emotions:
                print(f"  - {emotion['e.type']}: {emotion['frequency']} times (avg intensity: {emotion['avg_intensity']:.2f})")
        
        # Topics
        topic_query = """
        MATCH (t:Topic)
        RETURN t.label, count(t) as frequency
        ORDER BY frequency DESC
        LIMIT 5
        """
        topics = kg_builder.graph.query(topic_query)
        if topics:
            print("\n📝 TOP TOPICS:")
            for topic in topics:
                print(f"  - {topic['t.label']}: {topic['frequency']} mentions")
        
        # Patterns
        pattern_query = """
        MATCH (p:Pattern)
        RETURN p.label, p.confidence, p.description
        ORDER BY p.confidence DESC
        LIMIT 3
        """
        patterns = kg_builder.graph.query(pattern_query)
        if patterns:
            print("\n🎯 IDENTIFIED PATTERNS:")
            for pattern in patterns:
                print(f"  - {pattern['p.label']} (confidence: {pattern['p.confidence']:.2f})")
                print(f"    {pattern['p.description'][:80]}...")
                print()
        
        # Show relationship paths
        print("\n🛤️  SAMPLE RELATIONSHIP PATHS:")
        print("-" * 35)
        
        path_query = """
        MATCH path = (u:User)-[:HAS_SESSION]->(s:Session)-[:ASKED]->(q:Question)-[:ANSWERED_BY]->(a:Answer)-[:EXPRESSES]->(e:Emotion)
        RETURN u.user_id, s.session_id, q.text, a.text, e.type
        LIMIT 2
        """
        paths = kg_builder.graph.query(path_query)
        for path in paths:
            print(f"User({path['u.user_id']}) → Session({path['s.session_id']}) → Question → Answer → Emotion({path['e.type']})")
            print(f"  Q: {path['q.text'][:50]}...")
            print(f"  A: {path['a.text'][:50]}...")
            print()
        
        print("\n✅ Knowledge Graph visualization complete!")
        
    except Exception as e:
        print(f"❌ Error visualizing Knowledge Graph: {e}")

def generate_schema_documentation():
    """Generate documentation for the structured schema"""
    
    schema_doc = """
# STRUCTURED THERAPY KNOWLEDGE GRAPH SCHEMA

## Node Types

### 1. User
- **Properties**: user_id, name, age, demographics, created_at
- **Purpose**: Represents a therapy client
- **When Created**: Once per user

### 2. Session  
- **Properties**: session_id, timestamp, status, original_concern
- **Purpose**: Represents a therapy session
- **When Created**: Start of each therapy session

### 3. Question
- **Properties**: q_id, text, timestamp
- **Purpose**: Stores LLM1 counselor questions
- **When Created**: Each time LLM1 asks a question

### 4. Answer
- **Properties**: a_id, text, timestamp, sentiment_score
- **Purpose**: Stores user responses
- **When Created**: Each time user provides an answer

### 5. Emotion
- **Properties**: e_id, type, intensity (0.0-1.0)
- **Purpose**: Emotional states extracted from answers
- **When Created**: Extracted from each answer using LLM analysis

### 6. Topic
- **Properties**: t_id, label
- **Purpose**: Themes/topics discussed in answers
- **When Created**: Extracted from each answer using LLM analysis

### 7. Pattern
- **Properties**: p_id, label, confidence, description, created_at
- **Purpose**: Psychological patterns identified by LLM2
- **When Created**: When LLM2 identifies patterns with 85%+ confidence

## Relationships

### Core Flow Relationships
- `(:User)-[:HAS_SESSION]->(:Session)` - Links user to their sessions
- `(:Session)-[:ASKED]->(:Question)` - Session contains questions
- `(:Question)-[:ANSWERED_BY]->(:Answer)` - Questions get answered

### Analysis Relationships  
- `(:Answer)-[:EXPRESSES]->(:Emotion)` - Answers express emotions
- `(:Answer)-[:RELATES_TO]->(:Topic)` - Answers relate to topics
- `(:Topic)-[:PART_OF_PATTERN]->(:Pattern)` - Topics connect to patterns
- `(:User)-[:HAS_PATTERN]->(:Pattern)` - Users have identified patterns

## Real-Time Flow

1. **Q&A Turn**: LLM1 asks → Question node created → User answers → Answer node created
2. **Enrichment**: Extract emotions and topics → Create Emotion/Topic nodes → Link to Answer
3. **Pattern Analysis**: LLM2 analyzes across sessions → Create Pattern nodes when confident
4. **Relationship Building**: All nodes connected through meaningful relationships

This schema enables sophisticated psychological analysis across multiple therapy sessions.
    """
    
    with open("d:/Gen-AI-Exc/backend/KG/SCHEMA_DOCUMENTATION.md", "w", encoding="utf-8") as f:
        f.write(schema_doc)
    
    print("📖 Schema documentation generated: KG/SCHEMA_DOCUMENTATION.md")

if __name__ == "__main__":
    print("🚀 Starting Knowledge Graph Schema Visualization...")
    visualize_kg_schema()
    generate_schema_documentation()
