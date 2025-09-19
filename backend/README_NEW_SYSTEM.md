# Enhanced Conversation System

## Overview

This system implements a sophisticated conversation flow that combines vector database storage, knowledge graph analysis, and intelligent decision-making to provide contextually appropriate responses.

## Architecture Flow

```
User Prompt → Vector DB Query → LLM1 (Question Generator) → User Responses → 
Q&A Storage → LLM2 (Problem Extractor) → Proximity Check → Response Generation
```

### Detailed Flow

1. **User enters a prompt**
2. **System queries Vector Database** for similar Q&A pairs
3. **LLM1 analyzes the prompt** and generates clarifying questions
4. **Questions are shown to the user**, who provides responses
5. **Q&A pairs are stored** in both Knowledge Graph and Vector Database
6. **LLM2 processes the Knowledge Graph** to extract the root problem
7. **Decision 1**: If root problem is not discovered → ask for more info → loop back
8. **If root problem is discovered** → check proximity between original question and problem
9. **Decision 2**: 
   - If proximity is **low** → generate simple response → send to user only → end (no storage)
   - If proximity is **high** → generate comprehensive response → send to user → store in Vector DB → update Knowledge Graph → end (full storage)

## Components

### Core Components

#### 1. Vector Database Manager (`vector_db/vector_manager.py`)
- **Purpose**: Manages Q&A pair storage and retrieval using ChromaDB
- **Features**:
  - Store Q&A pairs with metadata
  - Similarity search for related conversations
  - Persistent storage with embeddings
  - Collection statistics and management

#### 2. LLM1 - Question Generator (`graph/nodes/classify_message.py`)
- **Purpose**: Analyzes user prompts and generates clarifying questions
- **Features**:
  - Queries vector database for similar conversations
  - Generates 2-3 specific clarifying questions
  - Determines if more information is needed
  - Uses structured output for consistent results

#### 3. Q&A Collector (`graph/nodes/qa_collector.py`)
- **Purpose**: Collects and processes user responses to clarifying questions
- **Features**:
  - Parses user responses into structured Q&A pairs
  - Handles multiple response formats
  - Creates metadata for each Q&A pair

#### 4. Knowledge Graph Integration (`graph/nodes/kg_ingest.py`)
- **Purpose**: Stores Q&A pairs in both Knowledge Graph and Vector Database
- **Features**:
  - Dual storage (Neo4j + ChromaDB)
  - Background processing for performance
  - Enhanced document processing
  - Schema refresh and maintenance

#### 5. LLM2 - Problem Extractor (`graph/nodes/problem_extractor.py`)
- **Purpose**: Analyzes Knowledge Graph data to identify root problems
- **Features**:
  - Queries Knowledge Graph for relevant information
  - Uses LLM to analyze patterns and extract root problems
  - Provides confidence scoring
  - Generates supporting evidence

#### 6. Proximity Checker (`graph/nodes/proximity_checker.py`)
- **Purpose**: Determines relationship between original question and discovered problem
- **Features**:
  - Semantic similarity analysis
  - Proximity scoring (0.0-1.0)
  - Decision logic for storage vs. simple response
  - Detailed reasoning for decisions

#### 7. Response Generator (`graph/nodes/response_generator.py`)
- **Purpose**: Generates appropriate responses based on analysis
- **Features**:
  - Comprehensive responses with insights (high proximity)
  - Simple direct responses (low proximity)
  - Follow-up question generation
  - Streaming response output

#### 8. Main Agent Flow (`graph/agent.py`)
- **Purpose**: Orchestrates the entire conversation flow
- **Features**:
  - State management across all components
  - Conditional routing based on analysis results
  - Loop handling for iterative clarification
  - Decision point management

## State Management

The system maintains a comprehensive state object that tracks:

```python
class State(TypedDict):
    messages: List[Message]                    # Conversation history
    original_question: str                     # User's initial question
    clarifying_questions: List[str]            # Generated questions
    needs_more_info: bool                      # Whether more info is needed
    similar_qa_pairs: List[Dict]               # Similar conversations from vector DB
    qa_pairs: List[Dict]                       # Collected Q&A pairs
    qa_collected: bool                         # Whether Q&A collection is complete
    root_problem: str                          # Extracted root problem
    problem_discovered: bool                   # Whether problem was identified
    confidence: float                          # Confidence in problem identification
    supporting_evidence: List[str]             # Evidence supporting the problem
    kg_context: str                            # Knowledge Graph context
    kg_confidence: float                       # KG query confidence
    proximity_score: float                     # Proximity between question and problem
    proximity_level: str                       # High/Medium/Low proximity
    proximity_reasoning: str                   # Explanation of proximity assessment
    should_store_qa: bool                      # Whether to store Q&A pair
    storage_reason: str                        # Reason for storage decision
    final_response: str                        # Generated response
    response_type: str                         # Type of response generated
    kg_ingested: bool                          # Whether KG ingestion is complete
```

## Decision Logic

### Decision 1: Problem Discovery
- **Condition**: `problem_discovered == False OR confidence < 0.7`
- **Action**: Ask for more information → loop back to question generation
- **Purpose**: Ensure we have enough information to identify the root problem

### Decision 2: Storage Decision
- **Condition**: `proximity_score >= 0.7`
- **High Proximity Action**: 
  - Generate comprehensive response with insights
  - Store Q&A pair in Vector Database
  - Update Knowledge Graph
- **Low Proximity Action**:
  - Generate simple direct response
  - No storage (avoid polluting database with irrelevant data)

## Installation & Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file with:
```env
# LLM API Keys
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional fallback

# Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Vector Database (optional customization)
CHROMA_PERSIST_DIRECTORY=./chroma_db

# External Integrations (optional)
NOTION_API_KEY=your_notion_api_key
```

### 3. Run the System
```bash
cd backend
python main.py
```

## Usage Examples

### Example 1: High Proximity Case
```
User: "I'm having trouble with my Python code not running properly"
System: [Asks clarifying questions about specific errors, environment, etc.]
User: [Provides detailed responses]
System: [Extracts root problem: "Python environment configuration issues"]
System: [High proximity detected]
System: [Generates comprehensive response with debugging steps]
System: [Stores Q&A pair for future reference]
```

### Example 2: Low Proximity Case
```
User: "What's the weather like today?"
System: [Asks clarifying questions about location, specific weather info]
User: [Provides responses]
System: [Extracts root problem: "Weather information request"]
System: [Low proximity detected - simple question doesn't need complex analysis]
System: [Generates simple weather response]
System: [No storage - keeps database focused on complex problems]
```

## Benefits

1. **Intelligent Storage**: Only stores relevant, high-value Q&A pairs
2. **Contextual Responses**: Adapts response complexity based on problem relevance
3. **Iterative Refinement**: Can ask follow-up questions to better understand user needs
4. **Knowledge Accumulation**: Builds a growing knowledge base of meaningful conversations
5. **Performance Optimization**: Avoids storing irrelevant data that could degrade search quality

## Technical Features

- **Vector Similarity Search**: Fast retrieval of related conversations
- **Graph-based Analysis**: Rich relationship modeling in Knowledge Graph
- **Confidence Scoring**: Quantified assessment of analysis quality
- **Streaming Responses**: Real-time response generation
- **Background Processing**: Non-blocking data ingestion
- **Error Handling**: Graceful degradation and error recovery
- **Modular Architecture**: Easy to extend and modify individual components

## Future Enhancements

1. **Multi-turn Conversations**: Support for extended dialogue sessions
2. **Domain Specialization**: Custom analyzers for specific domains
3. **User Personalization**: Learning from individual user patterns
4. **Advanced Parsing**: Better extraction of structured information from responses
5. **Performance Metrics**: Detailed analytics on system performance and user satisfaction
