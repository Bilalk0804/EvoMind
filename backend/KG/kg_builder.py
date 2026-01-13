#!/usr/bin/env python3
"""
Script for building a robust knowledge graph from documents.
Reads credentials from a .env file.
Dynamically infers graph schema from document content.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any
from datetime import datetime

# LangChain imports
from langchain_groq import ChatGroq
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_neo4j import Neo4jGraph
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
import re
import hashlib
import json
import time
# Load environment variables
class RobustKnowledgeGraphBuilder:
    """
    Builds a knowledge graph from a collection of documents with dynamic schema.
    """
    def __init__(self, groq_api_key: str, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        self.logger = self._setup_logging()
        self.logger.info("Initializing Robust Knowledge Graph Builder...")
        
        try:
            self.llm = ChatGroq(
                groq_api_key=groq_api_key,
                model_name="qwen/qwen3-32b",
                temperature=0.1,
                max_tokens=4096
            )
            # Try multiple connection approaches for Neo4j
            connection_successful = False
            
            # Try different connection configurations
            connection_configs = [
                {"url": neo4j_uri, "username": neo4j_username, "password": neo4j_password, "database": "neo4j"},
                {"url": neo4j_uri, "username": neo4j_username, "password": neo4j_password},
                {"url": neo4j_uri.replace("neo4j+s://", "bolt+s://"), "username": neo4j_username, "password": neo4j_password},
                {"url": neo4j_uri.replace("neo4j+s://", "neo4j://"), "username": neo4j_username, "password": neo4j_password}
            ]
            
            for i, config in enumerate(connection_configs):
                try:
                    self.logger.info(f"Trying Neo4j connection attempt {i+1}/4...")
                    self.graph = Neo4jGraph(**config)
                    # Test connection
                    test_result = self.graph.query("RETURN 1 as test")
                    self.logger.info(f"✅ Connected to Neo4j successfully with config {i+1}")
                    connection_successful = True
                    break
                except Exception as e:
                    self.logger.warning(f"Connection attempt {i+1} failed: {e}")
                    continue
            
            if not connection_successful:
                self.logger.error("❌ All Neo4j connection attempts failed")
                self.logger.error("🚫 THERAPY SYSTEM REQUIRES REAL NEO4J - NO MOCK FALLBACK")
                raise Exception(f"Failed to connect to Neo4j after all attempts")
            
            # Enhanced LLM Graph Transformer with detailed extraction
            self.llm_transformer = LLMGraphTransformer(
                llm=self.llm, 
                strict_mode=False,
                node_properties=["description", "type", "importance", "context"],
                relationship_properties=["description", "strength", "context"]
            )
            self.logger.info("Enhanced LLM Graph Transformer initialized.")
            
            # Adaptive text splitter based on document type
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,  # Smaller chunks for better entity extraction
                chunk_overlap=150,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ";", ":", " ", ""]
            )
            self.logger.info("Knowledge Graph Builder initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize builder: {e}")
            raise

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _analyze_document_content(self, content: str) -> str:
        """Analyze document content dynamically using LLM to determine optimal extraction strategy."""
        try:
            # Use LLM to analyze the document and suggest extraction approach
            analysis_prompt = f"""
            Analyze this document content and determine the best extraction strategy. 
            
            Content sample (first 500 chars):
            {content[:500]}...
            
            Based on the content, suggest ONE word that best describes the extraction approach needed:
            - academic (for research papers, studies, academic content)
            - business (for corporate documents, reports, procedures)
            - narrative (for stories, novels, creative writing)
            - legal (for laws, contracts, legal documents)
            - technical (for manuals, specifications, technical docs)
            - historical (for historical accounts, biographies)
            - news (for news articles, journalism)
            - reference (for encyclopedias, reference materials)
            - general (for mixed or unclear content)
            
            Respond with just ONE word:
            """
            
            message = HumanMessage(content=analysis_prompt)
            response = self.llm.invoke([message])
            doc_type = response.content.strip().lower()
            
            # Validate response
            valid_types = ['academic', 'business', 'narrative', 'legal', 'technical', 'historical', 'news', 'reference', 'general']
            if doc_type in valid_types:
                return doc_type
            else:
                return 'general'
                
        except Exception as e:
            self.logger.warning(f"Failed to analyze document type: {e}")
            return 'general'
    
    def _enhance_document_content(self, documents: List[Document]) -> List[Document]:
        """Enhance documents with metadata and preprocessing."""
        enhanced_docs = []
        
        for doc in documents:
            # Analyze document type dynamically
            doc_type = self._analyze_document_content(doc.page_content)
            
            # Add metadata
            doc.metadata['document_type'] = doc_type
            doc.metadata['content_length'] = len(doc.page_content)
            
            # Apply generic content enhancement (no specific preprocessing)
            doc.page_content = self._enhance_content_for_extraction(doc.page_content)
            
            enhanced_docs.append(doc)
        
        return enhanced_docs
    
    def _enhance_content_for_extraction(self, content: str) -> str:
        """Apply generic content enhancement for better entity extraction."""
        # Generic enhancements that work for any document type
        # Preserve proper nouns and important phrases
        content = re.sub(r'(\d{1,4}\s*(BC|AD|BCE|CE|years?|century|centuries))', r'[DATE] \1', content)
        content = re.sub(r'(\d{4})', r'[YEAR] \1', content)
        content = re.sub(r'(founded|established|built|created|invented|discovered)', r'[ACTION] \1', content)
        content = re.sub(r'(Section|Article|Chapter|Part)\s+(\d+)', r'[SECTION] \1 \2', content)
        return content
    
    def _create_enhanced_graph_documents(self, chunked_docs: List[Document]) -> List:
        """Create graph documents with enhanced prompting for better extraction."""
        enhanced_graph_docs = []
        
        for i, chunk in enumerate(chunked_docs):
            doc_type = chunk.metadata.get('document_type', 'general')
            
            # Create enhanced prompt based on document type
            enhanced_prompt = self._create_extraction_prompt(chunk.page_content, doc_type)
            
            # Create a new document with enhanced content
            enhanced_chunk = Document(
                page_content=enhanced_prompt,
                metadata=chunk.metadata
            )
            
            try:
                # Convert to graph format
                graph_docs = self.llm_transformer.convert_to_graph_documents([enhanced_chunk])
                enhanced_graph_docs.extend(graph_docs)
                
                if (i + 1) % 10 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(chunked_docs)} chunks")
                    
            except Exception as e:
                self.logger.warning(f"Failed to process chunk {i}: {e}")
                continue
        
        return enhanced_graph_docs
    
    def _create_extraction_prompt(self, content: str, doc_type: str) -> str:
        """Create dynamic extraction prompts based on LLM-determined document type."""
        return f"""
Document Analysis Type: {doc_type.upper()}

Content:
{content}

Universal Extraction Instructions:
- Extract ALL entities: people, organizations, concepts, locations, events, objects, dates, numbers
- Identify ALL meaningful relationships between entities
- Capture temporal sequences, hierarchical structures, and causal relationships
- Preserve context, importance, and detailed information
- Include descriptive properties for entities and relationships
- Note any dates, quantities, measurements, or specific details
- Capture both explicit and implicit relationships
- Maintain the semantic richness of the original content

Focus on creating a comprehensive knowledge representation that preserves the document's information structure and enables detailed querying.
"""
    
    def process_documents_and_build_graph(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Enhanced document processing with adaptive strategies for different content types.
        """
        results = {
            'processed_files': [], 'failed_files': [], 'total_nodes': 0, 
            'total_relationships': 0, 'processing_time': None, 'document_types': {}
        }
        start_time = datetime.now()
        all_documents = []
        
        # Load documents
        for file_path in file_paths:
            try:
                extension = Path(file_path).suffix.lower()
                if extension == '.pdf':
                    loader = PyPDFLoader(file_path)
                elif extension in ['.txt', '.md']:
                    loader = TextLoader(file_path, encoding='utf-8')
                elif extension == '.docx':
                    loader = UnstructuredWordDocumentLoader(file_path)
                else:
                    raise ValueError("Unsupported file format.")
                
                documents = loader.load()
                all_documents.extend(documents)
                results['processed_files'].append(file_path)
                self.logger.info(f"Loaded {file_path} - {len(documents)} pages")
                
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                results['failed_files'].append({'file': file_path, 'error': str(e)})

        if not all_documents:
            self.logger.warning("No documents were successfully loaded.")
            return results

        # Enhance documents with metadata and preprocessing
        self.logger.info("Enhancing documents with metadata and preprocessing...")
        enhanced_docs = self._enhance_document_content(all_documents)
        
        # Track document types
        for doc in enhanced_docs:
            doc_type = doc.metadata.get('document_type', 'general')
            results['document_types'][doc_type] = results['document_types'].get(doc_type, 0) + 1
        
        # Split into chunks
        chunked_docs = self.text_splitter.split_documents(enhanced_docs)
        self.logger.info(f"Split documents into {len(chunked_docs)} chunks.")
        
        # Create enhanced graph documents
        self.logger.info("Converting documents to graph format with enhanced extraction...")
        graph_documents = self._create_enhanced_graph_documents(chunked_docs)
        
        # Add to Neo4j in batches
        self.logger.info(f"Adding {len(graph_documents)} graph documents to Neo4j...")
        batch_size = 10
        for i in range(0, len(graph_documents), batch_size):
            batch = graph_documents[i:i + batch_size]
            try:
                self.graph.add_graph_documents(batch)
                self.logger.info(f"Added batch {i//batch_size + 1}/{(len(graph_documents) + batch_size - 1)//batch_size}")
            except Exception as e:
                self.logger.error(f"Failed to add batch {i//batch_size + 1}: {e}")
        
        # Calculate statistics
        for doc in graph_documents:
            results['total_nodes'] += len(doc.nodes)
            results['total_relationships'] += len(doc.relationships)

        self.graph.refresh_schema()
        results['processing_time'] = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Graph construction complete:")
        self.logger.info(f"  - Nodes: {results['total_nodes']}")
        self.logger.info(f"  - Relationships: {results['total_relationships']}")
        self.logger.info(f"  - Document types: {results['document_types']}")
        self.logger.info(f"  - Processing time: {results['processing_time']:.2f} seconds")
        
        return results
    
    def store_therapy_qa_pair(self, session_id: str, qa_number: int, question: str, answer: str, original_concern: str, user_id: str = "default_user"):
        """OPTIMIZED: Store Q&A pair with minimal graph operations using single transaction"""
        try:
            timestamp = datetime.now().isoformat()
            question_id = f"{session_id}_q{qa_number}"
            answer_id = f"{session_id}_a{qa_number}"
            
            # SINGLE OPTIMIZED QUERY: Create all nodes and relationships in one transaction
            optimized_query = """
            // 1. Ensure User and Session exist (MERGE = create if not exists)
            MERGE (u:User {user_id: $user_id})
            ON CREATE SET u.created_at = $timestamp
            
            MERGE (s:Session {session_id: $session_id})
            ON CREATE SET s.timestamp = $timestamp, s.status = 'active', s.original_concern = $original_concern
            
            MERGE (u)-[:HAS_SESSION]->(s)
            
            // 2. Create Question and Answer nodes (only if they don't exist)
            MERGE (q:Question {q_id: $question_id})
            ON CREATE SET q.text = $question, q.timestamp = $timestamp
            
            MERGE (a:Answer {a_id: $answer_id})
            ON CREATE SET a.text = $answer, a.timestamp = $timestamp
            
            // 3. Create relationships
            MERGE (s)-[:ASKED]->(q)
            MERGE (q)-[:ANSWERED_BY]->(a)
            
            RETURN u, s, q, a
            """
            
            # Execute single optimized query
            result = self.graph.query(optimized_query, {
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": timestamp,
                "question_id": question_id,
                "answer_id": answer_id,
                "question": question,
                "answer": answer,
                "original_concern": original_concern
            })
            
            # OPTIMIZED: Extract and create Emotion + Topic nodes in batch operations
            emotions = self._extract_emotions_from_text(answer)
            topics = self._extract_topics_from_text(answer)
            
            # Batch create emotions and topics in single query if any exist
            if emotions or topics:
                self._create_emotions_and_topics_batch(answer_id, emotions, topics)
            else:
                self.logger.warning(f"No emotions/topics extracted from: {answer[:50]}...")
            
            # Refresh schema
            self.graph.refresh_schema()
            
            # Q&A pair stored successfully
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error storing structured Q&A in KG: {e}")
            return False
    
    def analyze_therapy_patterns(self, session_id: str, current_qa_pairs: list, user_id: str = "default_user"):
        """Analyze therapy patterns using structured Knowledge Graph schema and create Pattern nodes"""
        try:
            # Query all user's therapy data using structured schema
            pattern_query = """
            MATCH (u:User {user_id: $user_id})-[:HAS_SESSION]->(s:Session)
            MATCH (s)-[:ASKED]->(q:Question)-[:ANSWERED_BY]->(a:Answer)
            OPTIONAL MATCH (a)-[:EXPRESSES]->(e:Emotion)
            OPTIONAL MATCH (a)-[:RELATES_TO]->(t:Topic)
            WITH s, q, a, 
                 collect(DISTINCT e.type) as emotions,
                 collect(DISTINCT e.intensity) as emotion_intensities,
                 collect(DISTINCT t.label) as topics
            RETURN s.session_id as session_id, 
                   s.original_concern as original_concern,
                   s.timestamp as session_timestamp,
                   q.text as question, 
                   q.timestamp as question_timestamp,
                   a.text as answer,
                   emotions,
                   emotion_intensities,
                   topics
            ORDER BY s.timestamp, q.timestamp
            """
            
            results = self.graph.query(pattern_query, {"user_id": user_id})
            
            if not results:
                return ""
            
            # Build comprehensive analysis context
            kg_context = "STRUCTURED THERAPY PATTERN ANALYSIS:\n\n"
            
            # Group by session
            sessions = {}
            all_emotions = set()
            all_topics = set()
            
            for result in results:
                sid = result['session_id']
                if sid not in sessions:
                    sessions[sid] = {
                        'original_concern': result['original_concern'],
                        'timestamp': result['session_timestamp'],
                        'qa_pairs': []
                    }
                
                sessions[sid]['qa_pairs'].append({
                    'question': result['question'],
                    'answer': result['answer'],
                    'emotions': [e for e in result['emotions'] if e],
                    'emotion_intensities': [i for i in result['emotion_intensities'] if i],
                    'topics': [t for t in result['topics'] if t]
                })
                
                # Collect all emotions and topics for pattern analysis
                all_emotions.update([e for e in result['emotions'] if e])
                all_topics.update([t for t in result['topics'] if t])
            
            # Add session analysis
            for sid, session_data in sessions.items():
                kg_context += f"SESSION {sid} ({session_data['timestamp']}):\n"
                kg_context += f"Original Concern: {session_data['original_concern']}\n\n"
                
                for i, qa in enumerate(session_data['qa_pairs'], 1):
                    kg_context += f"Q{i}: {qa['question']}\n"
                    kg_context += f"A{i}: {qa['answer']}\n"
                    if qa['emotions']:
                        kg_context += f"Emotions: {', '.join(qa['emotions'])}\n"
                    if qa['topics']:
                        kg_context += f"Topics: {', '.join(qa['topics'])}\n"
                    kg_context += "\n"
                
                kg_context += "---\n\n"
            
            # Add pattern summary
            kg_context += f"CROSS-SESSION PATTERNS:\n"
            kg_context += f"Recurring Emotions: {', '.join(all_emotions)}\n"
            kg_context += f"Recurring Topics: {', '.join(all_topics)}\n\n"
            
            # Use LLM to identify patterns and create Pattern nodes if confidence is high
            pattern_analysis = self._analyze_patterns_with_llm(kg_context, user_id)
            
            if pattern_analysis and pattern_analysis.get('confidence', 0) >= 0.85:
                self._create_pattern_nodes(user_id, pattern_analysis, all_topics)
            
            return kg_context
            
        except Exception as e:
            self.logger.error(f"❌ Error analyzing therapy patterns: {e}")
            return ""
    
    def _create_emotions_and_topics_batch(self, answer_id: str, emotions: list, topics: list):
        """OPTIMIZED: Create all emotions and topics for an answer in a single batch query"""
        try:
            if not emotions and not topics:
                return
            
            # Build dynamic query parts
            emotion_creates = []
            topic_creates = []
            emotion_merges = []
            topic_merges = []
            
            params = {"answer_id": answer_id}
            
            # Prepare emotion creation statements
            for i, emotion in enumerate(emotions):
                emotion_id = f"{answer_id}_emotion_{emotion['type']}"
                emotion_var = f"e{i}"
                
                emotion_creates.append(f"MERGE ({emotion_var}:Emotion {{e_id: $emotion_id_{i}, type: $emotion_type_{i}, intensity: $emotion_intensity_{i}}})")
                emotion_merges.append(f"MERGE (a)-[:EXPRESSES]->({emotion_var})")
                
                params[f"emotion_id_{i}"] = emotion_id
                params[f"emotion_type_{i}"] = emotion['type']
                params[f"emotion_intensity_{i}"] = emotion['intensity']
            
            # Prepare topic creation statements
            for i, topic in enumerate(topics):
                topic_id = f"topic_{topic['label'].lower().replace(' ', '_')}"
                topic_var = f"t{i}"
                
                topic_creates.append(f"MERGE ({topic_var}:Topic {{t_id: $topic_id_{i}, label: $topic_label_{i}}})")
                topic_merges.append(f"MERGE (a)-[:RELATES_TO]->({topic_var})")
                
                params[f"topic_id_{i}"] = topic_id
                params[f"topic_label_{i}"] = topic['label']
            
            # Build complete batch query
            batch_query = f"""
            MATCH (a:Answer {{a_id: $answer_id}})
            {chr(10).join(emotion_creates)}
            {chr(10).join(topic_creates)}
            {chr(10).join(emotion_merges)}
            {chr(10).join(topic_merges)}
            RETURN a
            """
            
            # Execute batch query
            self.graph.query(batch_query, params)
            
            # Quietly created emotions and topics
            
        except Exception as e:
            self.logger.error(f"❌ Error in batch emotion/topic creation: {e}")
            # Fallback to individual creation if batch fails
            self._create_emotions_and_topics_individual(answer_id, emotions, topics)
    
    def _create_emotions_and_topics_individual(self, answer_id: str, emotions: list, topics: list):
        """Fallback: Create emotions and topics individually if batch fails"""
        try:
            # Create emotions individually
            for emotion in emotions:
                emotion_id = f"{answer_id}_emotion_{emotion['type']}"
                emotion_query = """
                MERGE (a:Answer {a_id: $answer_id})
                MERGE (e:Emotion {e_id: $emotion_id, type: $emotion_type, intensity: $intensity})
                MERGE (a)-[:EXPRESSES]->(e)
                """
                self.graph.query(emotion_query, {
                    "answer_id": answer_id,
                    "emotion_id": emotion_id,
                    "emotion_type": emotion['type'],
                    "intensity": emotion['intensity']
                })
            
            # Create topics individually
            for topic in topics:
                topic_id = f"topic_{topic['label'].lower().replace(' ', '_')}"
                topic_query = """
                MERGE (a:Answer {a_id: $answer_id})
                MERGE (t:Topic {t_id: $topic_id, label: $topic_label})
                MERGE (a)-[:RELATES_TO]->(t)
                """
                self.graph.query(topic_query, {
                    "answer_id": answer_id,
                    "topic_id": topic_id,
                    "topic_label": topic['label']
                })
            
            # Fallback creation completed
            
        except Exception as e:
            self.logger.error(f"❌ Error in individual emotion/topic creation: {e}")
    
    def _extract_emotions_from_text(self, text: str) -> list:
        """Extract emotions from text using LLM with robust fallback"""
        try:
            # First try keyword-based extraction (more reliable)
            emotion_keywords = {
                'anxiety': ['anxious', 'worried', 'nervous', 'stressed', 'overwhelmed', 'panic'],
                'sadness': ['sad', 'depressed', 'down', 'upset', 'crying', 'tears'],
                'anger': ['angry', 'mad', 'frustrated', 'irritated', 'furious', 'annoyed'],
                'fear': ['scared', 'afraid', 'fearful', 'terrified', 'frightened'],
                'confusion': ['confused', 'lost', 'unclear', 'puzzled', 'unsure'],
                'stress': ['stressed', 'pressure', 'burden', 'overwhelmed'],
                'tiredness': ['tired', 'exhausted', 'drained', 'fatigued'],
                'hope': ['hope', 'optimistic', 'positive', 'better'],
                'guilt': ['guilty', 'shame', 'regret', 'fault']
            }
            
            detected_emotions = []
            text_lower = text.lower()
            
            for emotion, keywords in emotion_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    # Calculate intensity based on keyword strength
                    intensity = 0.8 if any(strong in text_lower for strong in ['very', 'extremely', 'really']) else 0.6
                    detected_emotions.append({"type": emotion, "intensity": intensity})
            
            # If no emotions detected, try LLM extraction
            if not detected_emotions:
                emotion_prompt = f"""
                Analyze this text and extract emotions. Return ONLY a JSON list:
                [
                    {{"type": "anxiety", "intensity": 0.8}},
                    {{"type": "sadness", "intensity": 0.6}}
                ]
                
                Text: "{text}"
                
                Common emotions: anxiety, sadness, anger, fear, stress, confusion, tiredness, hope, guilt
                """
                
                response = self.llm.invoke([HumanMessage(content=emotion_prompt)])
                
                try:
                    import json
                    emotions = json.loads(response.content.strip())
                    if isinstance(emotions, list) and emotions:
                        detected_emotions = emotions
                except json.JSONDecodeError:
                    pass
            
            # Ensure at least one emotion if text suggests emotional content
            if not detected_emotions and len(text) > 10:
                detected_emotions = [{"type": "neutral", "intensity": 0.5}]
            
            return detected_emotions
                
        except Exception as e:
            self.logger.error(f"Error extracting emotions: {e}")
            return [{"type": "neutral", "intensity": 0.5}]  # Default emotion
    
    def _extract_topics_from_text(self, text: str) -> list:
        """Extract topics/themes from text using keyword matching with LLM fallback"""
        try:
            # First try keyword-based extraction (more reliable)
            topic_keywords = {
                'work stress': ['work', 'job', 'career', 'boss', 'colleague', 'office', 'deadline', 'project'],
                'family issues': ['family', 'parents', 'siblings', 'mother', 'father', 'mom', 'dad'],
                'relationships': ['relationship', 'partner', 'boyfriend', 'girlfriend', 'friend', 'dating'],
                'health concerns': ['health', 'sick', 'tired', 'pain', 'medical', 'doctor', 'illness'],
                'sleep problems': ['sleep', 'insomnia', 'tired', 'exhausted', 'rest', 'awake', 'sleepless'],
                'academic pressure': ['school', 'study', 'exam', 'grade', 'university', 'college', 'student'],
                'financial stress': ['money', 'financial', 'debt', 'bills', 'expensive', 'afford'],
                'social anxiety': ['social', 'people', 'crowd', 'public', 'embarrassed', 'awkward'],
                'self-esteem': ['confidence', 'self-worth', 'insecure', 'doubt', 'inadequate'],
                'mental health': ['depression', 'anxiety', 'therapy', 'counseling', 'mental', 'emotional']
            }
            
            detected_topics = []
            text_lower = text.lower()
            
            for topic, keywords in topic_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    detected_topics.append({"label": topic})
            
            # If no topics detected, try LLM extraction
            if not detected_topics:
                topic_prompt = f"""
                Extract main topics from this text. Return ONLY a JSON list:
                [
                    {{"label": "work stress"}},
                    {{"label": "sleep problems"}}
                ]
                
                Text: "{text}"
                
                Common topics: work stress, family issues, relationships, health concerns, sleep problems, academic pressure, financial stress, social anxiety, self-esteem, mental health
                """
                
                response = self.llm.invoke([HumanMessage(content=topic_prompt)])
                
                try:
                    import json
                    topics = json.loads(response.content.strip())
                    if isinstance(topics, list) and topics:
                        detected_topics = topics
                except json.JSONDecodeError:
                    pass
            
            # Ensure at least one topic if text is substantial
            if not detected_topics and len(text) > 20:
                detected_topics = [{"label": "general concerns"}]
            
            return detected_topics
                
        except Exception as e:
            self.logger.error(f"Error extracting topics: {e}")
            return [{"label": "general concerns"}]  # Default topic
    
    def _analyze_patterns_with_llm(self, kg_context: str, user_id: str) -> dict:
        """Use LLM to analyze patterns and determine if a Pattern node should be created"""
        try:
            pattern_prompt = f"""
            Analyze the following therapy session data and identify psychological patterns:
            
            {kg_context}
            
            Based on this data, determine if there's a clear psychological pattern that should be recorded.
            
            Return a JSON response in this format:
            {{
                "pattern_found": true/false,
                "pattern_label": "specific pattern name",
                "confidence": 0.0-1.0,
                "description": "detailed description of the pattern",
                "supporting_evidence": ["evidence1", "evidence2"]
            }}
            
            Only return pattern_found=true if confidence >= 0.85 and you can identify a clear, recurring psychological pattern.
            
            Examples of patterns:
            - "Academic perfectionism with anxiety"
            - "Family conflict avoidance pattern"
            - "Work-related stress and sleep disruption cycle"
            - "Social anxiety with isolation behaviors"
            """
            
            response = self.llm.invoke([HumanMessage(content=pattern_prompt)])
            
            try:
                pattern_analysis = json.loads(response.content.strip())
                return pattern_analysis
            except json.JSONDecodeError:
                return {"pattern_found": False, "confidence": 0.0}
                
        except Exception as e:
            self.logger.error(f"Error analyzing patterns with LLM: {e}")
            return {"pattern_found": False, "confidence": 0.0}
    
    def _create_pattern_nodes(self, user_id: str, pattern_analysis: dict, related_topics: set):
        """Create Pattern nodes and relationships when high confidence patterns are found"""
        try:
            if not pattern_analysis.get('pattern_found', False):
                return
            
            pattern_id = f"pattern_{pattern_analysis['pattern_label'].lower().replace(' ', '_')}"
            timestamp = datetime.now().isoformat()
            
            # Create Pattern node
            pattern_query = """
            MERGE (u:User {user_id: $user_id})
            MERGE (p:Pattern {
                p_id: $pattern_id, 
                label: $pattern_label, 
                confidence: $confidence,
                description: $description,
                created_at: $timestamp
            })
            MERGE (u)-[:HAS_PATTERN]->(p)
            RETURN p
            """
            
            self.graph.query(pattern_query, {
                "user_id": user_id,
                "pattern_id": pattern_id,
                "pattern_label": pattern_analysis['pattern_label'],
                "confidence": pattern_analysis['confidence'],
                "description": pattern_analysis.get('description', ''),
                "timestamp": timestamp
            })
            
            # Link related topics to the pattern
            for topic_label in related_topics:
                if topic_label:  # Skip empty topics
                    topic_id = f"topic_{topic_label.lower().replace(' ', '_')}"
                    topic_pattern_query = """
                    MATCH (t:Topic {t_id: $topic_id})
                    MATCH (p:Pattern {p_id: $pattern_id})
                    MERGE (t)-[:PART_OF_PATTERN]->(p)
                    """
                    
                    self.graph.query(topic_pattern_query, {
                        "topic_id": topic_id,
                        "pattern_id": pattern_id
                    })
            
            self.logger.info(f"✅ Pattern node created: {pattern_analysis['pattern_label']} (confidence: {pattern_analysis['confidence']:.2f})")
            
        except Exception as e:
            self.logger.error(f"❌ Error creating pattern nodes: {e}")

def get_credentials_from_env():
    """Reads credentials exclusively from environment variables."""
    load_dotenv()
    groq_api_key = os.getenv('GROQ_API_KEY')
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_username = os.getenv('NEO4J_USERNAME')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not all([groq_api_key, neo4j_uri, neo4j_username, neo4j_password]):
        print("❌ Error: Missing one or more required credentials in the .env file.")
        print("Please ensure your .env file contains GROQ_API_KEY, NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD.")
        sys.exit(1)
        
    return groq_api_key, neo4j_uri, neo4j_username, neo4j_password

if __name__ == "__main__":
    groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
    
    print("🚀 Starting Knowledge Graph Builder...")
    builder = RobustKnowledgeGraphBuilder(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)
    
    documents_dir = Path("documents")
    supported_extensions = {'.pdf', '.docx', '.txt', '.md'}
    files = [str(f) for f in documents_dir.rglob('*') if f.is_file() and f.suffix.lower() in supported_extensions]

    if files:
        results = builder.process_documents_and_build_graph(files)
        print(f"\n✅ Completed processing. Total Nodes: {results['total_nodes']}, Total Relationships: {results['total_relationships']}")
    else:
        print("\n⚠  No documents found in 'documents' folder. Nothing to process.")
        print("Please add PDF, DOCX, TXT, or MD files to the 'documents' folder and run this script again.")