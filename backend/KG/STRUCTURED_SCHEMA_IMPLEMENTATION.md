# Structured Therapy Knowledge Graph Implementation

## Overview

I've successfully implemented your requested structured Knowledge Graph schema for the therapy system. The implementation creates specific node types and relationships that follow the exact specifications you provided.

## 🏗️ **Implemented Schema**

### **Node Types**

| Node Type | Properties | When Created | Purpose |
|-----------|------------|--------------|---------|
| **User** | `user_id`, `created_at` | Once per user | Represents therapy client |
| **Session** | `session_id`, `timestamp`, `status`, `original_concern` | Start of therapy session | Contains therapy session data |
| **Question** | `q_id`, `text`, `timestamp` | Each LLM1 question | Stores counselor questions |
| **Answer** | `a_id`, `text`, `timestamp` | Each user answer | Stores user responses |
| **Emotion** | `e_id`, `type`, `intensity` | Extracted from answers | Emotional states (anxiety, sadness, etc.) |
| **Topic** | `t_id`, `label` | Extracted from answers | Discussion themes (work stress, family, etc.) |
| **Pattern** | `p_id`, `label`, `confidence`, `description` | LLM2 analysis (85%+ confidence) | Psychological patterns |

### **Relationships**

| Relationship | Meaning | Purpose |
|--------------|---------|---------|
| `(:User)-[:HAS_SESSION]->(:Session)` | User has therapy sessions | Links user to their sessions |
| `(:Session)-[:ASKED]->(:Question)` | Session contains questions | Session flow tracking |
| `(:Question)-[:ANSWERED_BY]->(:Answer)` | Questions get answered | Q&A pair linking |
| `(:Answer)-[:EXPRESSES]->(:Emotion)` | Answers express emotions | Emotional analysis |
| `(:Answer)-[:RELATES_TO]->(:Topic)` | Answers relate to topics | Thematic analysis |
| `(:Topic)-[:PART_OF_PATTERN]->(:Pattern)` | Topics form patterns | Pattern recognition |
| `(:User)-[:HAS_PATTERN]->(:Pattern)` | Users have patterns | User-level insights |

## 🔄 **Real-Time Flow Implementation**

### **1. Q&A Turn Processing**
```python
# When LLM1 asks a question and user answers:
kg_builder.store_therapy_qa_pair(
    session_id="session_123",
    qa_number=1,
    question="How are you feeling today?",
    answer="I'm feeling anxious about work deadlines",
    original_concern="Work stress",
    user_id="user_001"
)
```

**What happens internally:**
1. Creates/updates `User` node
2. Creates/updates `Session` node with `HAS_SESSION` relationship
3. Creates `Question` node with `ASKED` relationship
4. Creates `Answer` node with `ANSWERED_BY` relationship
5. Extracts emotions → Creates `Emotion` nodes with `EXPRESSES` relationships
6. Extracts topics → Creates `Topic` nodes with `RELATES_TO` relationships

### **2. Enrichment Stage**
The system automatically:
- **Emotion Extraction**: Uses LLM to identify emotions like "anxiety", "sadness" with intensity scores
- **Topic Extraction**: Identifies themes like "work stress", "family issues", "sleep problems"
- **Relationship Creation**: Links all extracted data through proper relationships

### **3. Pattern Analysis by LLM2**
```python
# LLM2 analyzes across all sessions:
kg_context = kg_builder.analyze_therapy_patterns(session_id, qa_pairs, user_id)
```

**What happens:**
1. Queries entire user history using structured relationships
2. Analyzes cross-session patterns using LLM
3. Creates `Pattern` nodes when confidence ≥ 85%
4. Links patterns to users and topics

## 📁 **Modified Files**

### **1. `KG/kg_builder.py`** - Core Implementation
- **`store_therapy_qa_pair()`**: Creates structured nodes and relationships
- **`analyze_therapy_patterns()`**: Queries structured data for pattern analysis
- **`_extract_emotions_from_text()`**: LLM-based emotion extraction
- **`_extract_topics_from_text()`**: LLM-based topic extraction
- **`_analyze_patterns_with_llm()`**: Pattern identification using LLM
- **`_create_pattern_nodes()`**: Creates Pattern nodes with high confidence

### **2. `main.py`** - Updated Integration
- Modified calls to use new `user_id` parameter
- Maintains backward compatibility with existing system

### **3. New Utility Files**
- **`KG/visualize_structured_kg.py`**: Visualization and inspection tools
- **`test_structured_kg.py`**: Complete testing script
- **`KG/SCHEMA_DOCUMENTATION.md`**: Detailed schema documentation

## 🚀 **Usage Examples**

### **Running the System**
```bash
cd backend
python main.py
# System now creates structured nodes automatically
```

### **Testing the Schema**
```bash
python test_structured_kg.py
# Creates sample therapy data and shows structure
```

### **Visualizing the Graph**
```bash
cd KG
python visualize_structured_kg.py
# Shows node counts, relationships, and sample data
```

## 🔍 **Sample Queries**

### **Get Complete Session Structure**
```cypher
MATCH (u:User)-[:HAS_SESSION]->(s:Session)-[:ASKED]->(q:Question)-[:ANSWERED_BY]->(a:Answer)
OPTIONAL MATCH (a)-[:EXPRESSES]->(e:Emotion)
OPTIONAL MATCH (a)-[:RELATES_TO]->(t:Topic)
RETURN u.user_id, s.original_concern, q.text, a.text, 
       collect(e.type) as emotions, collect(t.label) as topics
```

### **Find User Patterns**
```cypher
MATCH (u:User {user_id: "user_001"})-[:HAS_PATTERN]->(p:Pattern)
RETURN p.label, p.confidence, p.description
ORDER BY p.confidence DESC
```

### **Analyze Emotional Trends**
```cypher
MATCH (u:User)-[:HAS_SESSION]->(s:Session)-[:ASKED]->()-[:ANSWERED_BY]->(a:Answer)-[:EXPRESSES]->(e:Emotion)
RETURN e.type, avg(e.intensity) as avg_intensity, count(e) as frequency
ORDER BY frequency DESC
```

## ✅ **Key Benefits**

1. **Structured Data**: Clear separation of concerns with specific node types
2. **Rich Relationships**: Meaningful connections between all data points
3. **Automatic Enrichment**: LLM-powered emotion and topic extraction
4. **Pattern Recognition**: Cross-session analysis with confidence scoring
5. **Scalable Design**: Efficient queries across multiple users and sessions
6. **Real-time Processing**: Immediate storage and analysis of Q&A pairs

## 🔧 **Technical Features**

- **LLM Integration**: Uses Groq/Gemini for intelligent extraction
- **Fallback Mechanisms**: Keyword-based extraction when LLM fails
- **Confidence Thresholds**: Only creates patterns with 85%+ confidence
- **Timestamp Tracking**: Full audit trail of all interactions
- **Schema Validation**: Proper Neo4j schema with constraints
- **Error Handling**: Robust error handling and logging

The implementation is now ready for production use and provides the exact structured schema you requested for comprehensive therapy session analysis! 🎯
