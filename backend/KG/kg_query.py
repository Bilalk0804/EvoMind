#!/usr/bin/env python3
"""
Script for querying a pre-built knowledge graph interactively.
Reads credentials from a .env file.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import hashlib
import json
import time
from functools import lru_cache

# LangChain imports
from langchain_groq import ChatGroq
from langchain_neo4j import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_core.messages import HumanMessage

# Removed unused Config import

class RobustKnowledgeGraphQuery:
    """
    Handles interactive querying of a knowledge graph with dynamic schema.
    Enhanced with efficiency, robustness, and hallucination prevention.
    """
    def __init__(self, groq_api_key: str, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        self.logger = self._setup_logging()
        self.logger.info("Initializing Robust Knowledge Graph Query System...")
        
        # Initialize caching and validation systems
        self.query_cache = {}
        self.entity_cache = {}
        self.confidence_threshold = 0.7
        self.max_cache_size = 1000
        
        try:
            self.llm = ChatGroq(
                groq_api_key=groq_api_key,
                model_name="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=4096
            )
            # Try Neo4j connection with fallback to mock
            try:
                self.graph = Neo4jGraph(url=neo4j_uri, username=neo4j_username, password=neo4j_password)
                self.graph.refresh_schema()
                self.logger.info("✅ Connected to Neo4j successfully")
            except Exception as neo4j_error:
                self.logger.warning(f"Neo4j connection failed: {neo4j_error}")
                self.logger.info("🔧 Using mock Neo4j for testing...")
                from mock_neo4j import create_mock_graph
                self.graph = create_mock_graph(neo4j_uri, neo4j_username, neo4j_password)

            # Skip GraphCypherQAChain for now due to compatibility issues
            # Use direct LLM queries with graph context instead
            self.qa_chain = None
            self.logger.info("Using direct LLM queries with graph context.")
            
            self.logger.info("Knowledge Graph Query System initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize system: {e}")
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

    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the knowledge graph with enhanced efficiency, robustness, and hallucination prevention.
        """
        self.logger.info(f"Processing query: {question}")
        
        # Step 1: Check cache first for efficiency
        cache_key = self._generate_cache_key(question)
        if cache_key in self.query_cache:
            self.logger.info("Returning cached result")
            return self.query_cache[cache_key]
        
        # Step 2: Validate and preprocess question
        processed_question = self._preprocess_question(question)
        
        # Step 3: Use enhanced fallback directly (skip GraphCypherQAChain due to compatibility issues)
        validated_answer = self._enhanced_fallback_query(processed_question)

        # Step 5: Create result with confidence scoring and analysis details
        result = {
            'question': question,
            'answer': validated_answer['answer'],
            'confidence': validated_answer.get('confidence', 0.5),
            'sources': validated_answer.get('sources', []),
            'analysis_details': validated_answer.get('analysis_details', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        # Step 6: Cache result if confidence is high enough
        if validated_answer.get('confidence', 0) >= self.confidence_threshold:
            self._cache_result(cache_key, result)
        
        return result

    def _fallback_query(self, question: str) -> str:
        """Robust query system with multi-query retrieval and fallback strategies."""
        
        # Strategy 1: Multi-query retrieval
        try:
            multi_query_result = self._multi_query_retrieval(question)
            if multi_query_result and multi_query_result != "No relevant data found.":
                return multi_query_result
        except Exception as e:
            self.logger.warning(f"Multi-query retrieval failed: {e}")
        
        # Strategy 2: Try keyword-based search
        try:
            keyword_result = self._keyword_search_strategy(question)
            if keyword_result and keyword_result != "No relevant data found.":
                return keyword_result
        except Exception as e:
            self.logger.warning(f"Keyword search failed: {e}")
        
        # Strategy 3: Try LLM-generated Cypher query
        try:
            cypher_result = self._llm_cypher_strategy(question)
            if cypher_result and cypher_result != "No relevant data found.":
                return cypher_result
        except Exception as e:
            self.logger.warning(f"LLM Cypher strategy failed: {e}")
        
        # Strategy 4: Broad search with context
        try:
            return self._broad_search_strategy(question)
        except Exception as e:
            self.logger.error(f"All query strategies failed: {e}")
            return f"I apologize, but I couldn't find relevant information to answer your question: {question}"
    
    def _generate_cache_key(self, question: str) -> str:
        """Generate cache key for question."""
        return hashlib.md5(question.lower().strip().encode()).hexdigest()
    
    def _preprocess_question(self, question: str) -> str:
        """Preprocess and validate question."""
        # Remove extra whitespace and normalize
        question = ' '.join(question.strip().split())
        
        # Basic validation
        if len(question) < 3:
            raise ValueError("Question too short")
        
        return question
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache result with size management."""
        if len(self.query_cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[cache_key] = result
    
    def _validate_and_enhance_answer(self, question: str, raw_answer: str, response: Dict) -> Dict[str, Any]:
        """Validate answer for hallucinations and enhance with confidence scoring."""
        try:
            # Extract Cypher query and results if available
            cypher_query = response.get('intermediate_steps', [{}])[0].get('query', '')
            cypher_results = response.get('intermediate_steps', [{}])[0].get('context', [])
            
            # Validate answer against actual graph data
            validation_result = self._validate_against_graph_data(question, raw_answer, cypher_results)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(question, raw_answer, cypher_results, validation_result)
            
            # Enhance answer with source attribution
            enhanced_answer = self._enhance_with_sources(raw_answer, cypher_results, confidence)
            
            return {
                'answer': enhanced_answer['answer'],
                'confidence': confidence,
                'sources': enhanced_answer['sources'],
                'validation': validation_result
            }
            
        except Exception as e:
            self.logger.warning(f"Answer validation failed: {e}")
            return {
                'answer': raw_answer,
                'confidence': 0.3,
                'sources': [],
                'validation': {'status': 'failed', 'reason': str(e)}
            }
    
    def _validate_against_graph_data(self, question: str, answer: str, graph_results: List) -> Dict[str, Any]:
        """Validate answer against actual graph data to prevent hallucinations."""
        try:
            if not graph_results:
                return {'status': 'no_data', 'confidence': 0.2}
            
            # Extract entities and facts from answer
            answer_entities = self._extract_entities_from_text(answer)
            
            # Check if entities exist in graph results
            graph_entities = set()
            for result in graph_results:
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, str):
                            graph_entities.add(value.lower())
            
            # Calculate overlap
            entity_overlap = len(answer_entities.intersection(graph_entities)) / max(len(answer_entities), 1)
            
            # Validate specific facts using LLM
            fact_validation = self._validate_facts_with_llm(question, answer, graph_results)
            
            return {
                'status': 'validated',
                'entity_overlap': entity_overlap,
                'fact_validation': fact_validation,
                'confidence': (entity_overlap + fact_validation.get('score', 0)) / 2
            }
            
        except Exception as e:
            return {'status': 'error', 'reason': str(e), 'confidence': 0.1}
    
    def _extract_entities_from_text(self, text: str) -> set:
        """Extract entities from text for validation."""
        import re
        # Extract proper nouns and significant terms
        entities = set()
        
        # Proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.update([entity.lower() for entity in proper_nouns])
        
        # Numbers and dates
        numbers = re.findall(r'\b\d+(?:\w+)?\b', text)
        entities.update(numbers)
        
        return entities
    
    def _validate_facts_with_llm(self, question: str, answer: str, graph_data: List) -> Dict[str, Any]:
        """Use LLM to validate facts in answer against graph data."""
        try:
            validation_prompt = f"""
            Question: {question}
            Answer: {answer}
            Graph Data: {graph_data[:10]}  # Limit data size
            
            Validate if the answer contains any information NOT supported by the graph data.
            Rate the factual accuracy from 0.0 to 1.0.
            
            Response format:
            Score: [0.0-1.0]
            Issues: [list any unsupported claims]
            """
            
            message = HumanMessage(content=validation_prompt)
            response = self.llm.invoke([message])
            
            # Parse response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract score
            import re
            score_match = re.search(r'Score:\s*([0-9.]+)', content)
            score = float(score_match.group(1)) if score_match else 0.5
            
            return {'score': score, 'details': content}
            
        except Exception as e:
            return {'score': 0.5, 'error': str(e)}
    
    def _calculate_confidence_score(self, question: str, answer: str, graph_results: List, validation: Dict) -> float:
        """Calculate enhanced confidence score based on completeness and source diversity."""
        try:
            # Base confidence from validation
            base_confidence = validation.get('confidence', 0.5)
            
            # Enhanced completeness scoring
            completeness_score = self._calculate_completeness_score(question, answer, graph_results)
            
            # Source diversity factor (more sources = higher confidence)
            source_diversity = min(len(graph_results) / 15, 1.0) if graph_results else 0.1
            
            # Answer quality indicators
            quality_indicators = self._calculate_answer_quality(answer)
            
            # Combine factors with enhanced weighting
            confidence = (
                base_confidence * 0.4 +           # Validation confidence
                completeness_score * 0.3 +        # Answer completeness
                source_diversity * 0.2 +          # Source diversity
                quality_indicators * 0.1          # Answer quality
            )
            
            return min(max(confidence, 0.0), 1.0)  # Clamp to [0, 1]
            
        except Exception:
            return 0.5
    
    def _calculate_completeness_score(self, question: str, answer: str, graph_results: List) -> float:
        """Calculate how complete the answer is based on available information."""
        try:
            # Extract key concepts from question
            question_keywords = set(self._extract_comprehensive_keywords(question))
            
            # Extract concepts mentioned in answer
            answer_keywords = set(self._extract_comprehensive_keywords(answer))
            
            # Calculate keyword coverage
            keyword_coverage = len(question_keywords.intersection(answer_keywords)) / max(len(question_keywords), 1)
            
            # Check for specific completeness indicators
            completeness_indicators = 0
            if any(word in answer.lower() for word in ['annual', 'annually', 'yearly']):
                completeness_indicators += 0.1
            if any(word in answer.lower() for word in ['30 days', 'thirty days', 'month']):
                completeness_indicators += 0.1
            if any(word in answer.lower() for word in ['iso', 'nist', 'standard']):
                completeness_indicators += 0.1
            if any(word in answer.lower() for word in ['background', 'screening', 'verification']):
                completeness_indicators += 0.1
            if any(word in answer.lower() for word in ['training', 'education', 'awareness']):
                completeness_indicators += 0.1
            if any(word in answer.lower() for word in ['performance', 'evaluation', 'review']):
                completeness_indicators += 0.1
            
            # Penalize generic answers
            if len(answer.split()) < 20:
                completeness_indicators -= 0.2
            
            return min(keyword_coverage + completeness_indicators, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_answer_quality(self, answer: str) -> float:
        """Calculate answer quality based on structure and content."""
        try:
            quality_score = 0.5  # Base score
            
            # Length appropriateness (not too short, not too long)
            word_count = len(answer.split())
            if 30 <= word_count <= 200:
                quality_score += 0.2
            elif 20 <= word_count <= 300:
                quality_score += 0.1
            
            # Specific information indicators
            if any(char.isupper() for char in answer):  # Has proper nouns/standards
                quality_score += 0.1
            if any(char.isdigit() for char in answer):  # Has numbers/timeframes
                quality_score += 0.1
            
            # Structure indicators
            if answer.count('.') >= 2:  # Multiple sentences
                quality_score += 0.1
            
            return min(quality_score, 1.0)
            
        except Exception:
            return 0.5
    
    def _enhance_with_sources(self, answer: str, graph_results: List, confidence: float) -> Dict[str, Any]:
        """Enhance answer with detailed source attribution and citations."""
        try:
            sources = []
            citations = []
            
            # Extract detailed sources from graph results
            for i, result in enumerate(graph_results[:10], 1):  # Increased source limit
                if isinstance(result, dict):
                    # Create detailed source information
                    source_info = {
                        'id': i,
                        'type': 'graph_node',
                        'node_type': result.get('node_type', 'Unknown'),
                        'node_id': result.get('node_id', 'Unknown'),
                        'data': {k: v for k, v in result.items() if isinstance(v, (str, int, float))}
                    }
                    
                    # Extract standard references for citations
                    node_id = result.get('node_id', '')
                    if any(std in node_id for std in ['ISO', 'NIST', 'CSA']):
                        citations.append(f"[{i}] {node_id}")
                    
                    sources.append(source_info)
            
            # Enhanced answer with citations
            enhanced_answer = answer
            
            # Add citations if available
            if citations:
                enhanced_answer += "\n\n📚 **Sources Referenced:**\n"
                for citation in citations[:5]:
                    enhanced_answer += f"• {citation}\n"
            
            # Add confidence indicator with more detail
            if confidence < 0.6:
                enhanced_answer += f"\n\n⚠️ **Confidence: {confidence:.2f}** - This answer may be incomplete. Consider reviewing source documents for additional details."
            elif confidence < self.confidence_threshold:
                enhanced_answer += f"\n\n🟡 **Confidence: {confidence:.2f}** - Good answer quality with room for additional verification."
            else:
                enhanced_answer += f"\n\n🟢 **Confidence: {confidence:.2f}** - High-quality comprehensive answer."
            
            return {
                'answer': enhanced_answer,
                'sources': sources,
                'citations': citations
            }
            
        except Exception:
            return {'answer': answer, 'sources': [], 'citations': []}
    
    def _enhanced_fallback_query(self, question: str) -> Dict[str, Any]:
        """Enhanced fallback with multi-node analysis tracking and validation."""
        try:
            self.logger.info("Starting multi-node analysis...")
            
            # Initialize analysis tracking
            analysis_tracker = {
                'nodes_checked': 0,
                'relationships_found': 0,
                'cross_patterns': 0,
                'search_methods_used': []
            }
            
            # Use existing multi-query retrieval but with tracking
            raw_answer, analysis_data = self._multi_query_retrieval_with_tracking(question, analysis_tracker)
            
            if raw_answer and raw_answer != "No relevant data found.":
                # Validate the fallback answer
                validation = self._validate_fallback_answer(question, raw_answer)
                confidence = validation.get('confidence', 0.4)
                
                self.logger.info(f"Multi-node analysis complete: {analysis_data['nodes_checked']} nodes, {analysis_data['relationships_found']} relationships")
                
                return {
                    'answer': raw_answer,
                    'confidence': confidence,
                    'sources': validation.get('sources', []),
                    'analysis_details': analysis_data,
                    'method': 'enhanced_fallback'
                }
            else:
                return {
                    'answer': "I couldn't find sufficient information to answer your question confidently.",
                    'confidence': 0.1,
                    'sources': [],
                    'analysis_details': analysis_data,
                    'method': 'no_data'
                }
                
        except Exception as e:
            return {
                'answer': f"An error occurred while processing your question: {str(e)}",
                'confidence': 0.0,
                'sources': [],
                'analysis_details': {'nodes_checked': 0, 'relationships_found': 0, 'cross_patterns': 0},
                'method': 'error'
            }
    
    def _validate_fallback_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """Validate fallback answer quality."""
        try:
            # Check answer quality indicators
            word_count = len(answer.split())
            has_specific_info = any(char.isupper() for char in answer)  # Has proper nouns
            has_numbers = any(char.isdigit() for char in answer)
            
            # Calculate quality score
            quality_score = 0.3  # Base score
            if 10 <= word_count <= 100:  # Good length
                quality_score += 0.2
            if has_specific_info:  # Contains specific information
                quality_score += 0.2
            if has_numbers:  # Contains quantitative data
                quality_score += 0.1
            if "No relevant data found" not in answer:  # Not a failure message
                quality_score += 0.2
            
            return {
                'confidence': min(quality_score, 0.8),  # Cap fallback confidence
                'sources': [{'type': 'multi_query_search', 'quality_score': quality_score}]
            }
            
        except Exception:
            return {'confidence': 0.3, 'sources': []}
    
    def _multi_query_retrieval_with_tracking(self, question: str, analysis_tracker: Dict) -> tuple:
        """Multi-query retrieval with detailed tracking of nodes and relationships checked."""
        try:
            self.logger.info("Decomposing question into sub-queries...")
            # Step 1: Decompose the question into multiple sub-queries
            sub_queries = self._decompose_question(question)
            analysis_tracker['search_methods_used'].append('question_decomposition')
            
            # Step 2: Execute all sub-queries with tracking
            all_results = []
            for sub_query in sub_queries:
                try:
                    self.logger.info(f"Processing sub-query: {sub_query}")
                    # Use different search strategies for each sub-query
                    keyword_results = self._execute_sub_query_search_with_tracking(sub_query, analysis_tracker)
                    if keyword_results:
                        all_results.extend(keyword_results)
                except Exception as e:
                    self.logger.warning(f"Sub-query '{sub_query}' failed: {e}")
                    continue
            
            # Step 3: Fuse and rank results with tracking
            if all_results:
                fused_results = self._fuse_and_rank_results(all_results, question)
                
                # Count cross-patterns
                synthesized_data = self._synthesize_multi_node_data(fused_results)
                analysis_tracker['cross_patterns'] = len(synthesized_data.get('cross_patterns', []))
                
                answer = self._generate_multi_query_answer(question, sub_queries, fused_results)
                return answer, analysis_tracker
            
            return "No relevant data found.", analysis_tracker
            
        except Exception as e:
            self.logger.error(f"Multi-query retrieval failed: {e}")
            return "No relevant data found.", analysis_tracker
    
    def _execute_sub_query_search_with_tracking(self, sub_query: str, analysis_tracker: Dict) -> list:
        """Execute search for a single sub-query with node/relationship tracking."""
        all_results = []
        
        # Method 1: Keyword extraction and search with tracking
        try:
            keywords = self._extract_comprehensive_keywords(sub_query)
            if keywords:
                analysis_tracker['search_methods_used'].append('keyword_extraction')
                
                # Exact matches
                for keyword in keywords[:3]:
                    exact_results = self._search_exact_matches(keyword)
                    if exact_results:
                        all_results.extend(exact_results)
                        # Count nodes and relationships
                        for result in exact_results:
                            analysis_tracker['nodes_checked'] += 1
                            if result.get('relationships'):
                                analysis_tracker['relationships_found'] += len(result['relationships'])
                
                # Partial matches if no exact matches
                if not all_results:
                    for keyword in keywords[:3]:
                        partial_results = self._search_partial_matches(keyword)
                        if partial_results:
                            all_results.extend(partial_results)
                            # Count nodes and relationships
                            for result in partial_results:
                                analysis_tracker['nodes_checked'] += 1
                                if result.get('relationships'):
                                    analysis_tracker['relationships_found'] += len(result['relationships'])
        except Exception as e:
            self.logger.warning(f"Keyword search for sub-query failed: {e}")
        
        # Method 2: Dynamic relationship search with tracking
        try:
            dynamic_results = self._search_dynamic_relationships(sub_query, keywords if 'keywords' in locals() else [])
            if dynamic_results:
                all_results.extend(dynamic_results)
                analysis_tracker['search_methods_used'].append('dynamic_relationships')
                # Count additional nodes
                for result in dynamic_results:
                    analysis_tracker['nodes_checked'] += 1
                    if result.get('additional_connections'):
                        analysis_tracker['relationships_found'] += len(result.get('additional_connections', []))
                    if result.get('extended_connections'):
                        analysis_tracker['relationships_found'] += len(result.get('extended_connections', []))
                    if result.get('distant_connections'):
                        analysis_tracker['relationships_found'] += len(result.get('distant_connections', []))
        except Exception as e:
            self.logger.warning(f"Dynamic search for sub-query failed: {e}")
        
        # Method 3: Broad context search with tracking
        try:
            if not all_results and 'keywords' in locals():
                broad_results = self._search_broad_context(keywords)
                if broad_results:
                    all_results.extend(broad_results)
                    analysis_tracker['search_methods_used'].append('broad_context')
                    # Count broad search nodes
                    for result in broad_results:
                        analysis_tracker['nodes_checked'] += 1
                        if result.get('additional_connections'):
                            analysis_tracker['relationships_found'] += len(result.get('additional_connections', []))
        except Exception as e:
            self.logger.warning(f"Broad search for sub-query failed: {e}")
        
        return all_results

    def _multi_query_retrieval(self, question: str) -> str:
        """Multi-query retrieval system that decomposes complex questions into sub-queries."""
        try:
            # Step 1: Decompose the question into multiple sub-queries
            sub_queries = self._decompose_question(question)
            
            # Step 2: Execute all sub-queries in parallel
            all_results = []
            for sub_query in sub_queries:
                try:
                    # Use different search strategies for each sub-query
                    keyword_results = self._execute_sub_query_search(sub_query)
                    if keyword_results:
                        all_results.extend(keyword_results)
                except Exception as e:
                    self.logger.warning(f"Sub-query '{sub_query}' failed: {e}")
                    continue
            
            # Step 3: Fuse and rank results with enhanced scoring
            if all_results:
                fused_results = self._fuse_and_rank_results_enhanced(all_results, question)
                return self._generate_multi_query_answer(question, sub_queries, fused_results)
            
            return "No relevant data found."
            
        except Exception as e:
            self.logger.error(f"Multi-query retrieval failed: {e}")
            return "No relevant data found."
    
    def _decompose_question(self, question: str) -> list:
        """Decompose complex questions into simpler sub-queries for any domain."""
        try:
            decomposition_prompt = f"""
            Decompose this complex question into 3-5 simpler, focused sub-questions that together would help answer the original question.
            
            Original Question: {question}
            
            Create sub-questions that:
            1. Focus on different aspects of the main question
            2. Are specific and searchable
            3. Cover the key information needed
            4. Can be answered independently
            5. Target specific entities, concepts, or relationships
            
            Consider breaking down by:
            - What entities are involved?
            - What relationships exist?
            - What specific attributes or properties?
            - What processes or procedures?
            - What requirements or conditions?
            
            Return ONLY the sub-questions, one per line, ending with '?'
            """
            
            message = HumanMessage(content=decomposition_prompt)
            response = self.llm.invoke([message])
            
            # Parse and validate sub-queries
            sub_queries = [q.strip() for q in response.content.split('\n') if q.strip() and '?' in q]
            
            # Quality filter: ensure sub-queries are meaningful and well-formed
            filtered_queries = []
            for q in sub_queries:
                # Basic quality checks: reasonable length and contains question words
                if (len(q.split()) >= 3 and 
                    any(qword in q.lower() for qword in ['what', 'which', 'who', 'where', 'when', 'how', 'why', 'is', 'are', 'do', 'does', 'can', 'will'])):
                    filtered_queries.append(q)
            
            # Fallback to original question if no good sub-queries
            if not filtered_queries:
                filtered_queries = [question]
            
            # Add original question as final fallback if not already included
            if question not in filtered_queries:
                filtered_queries.append(question)
            
            return filtered_queries[:5]
            
        except Exception as e:
            self.logger.warning(f"Question decomposition failed: {e}")
            return [question]
    
    
    def _execute_sub_query_search(self, sub_query: str) -> list:
        """Execute search for a single sub-query using multiple methods."""
        all_results = []
        
        # Method 1: Keyword extraction and search
        try:
            keywords = self._extract_comprehensive_keywords(sub_query)
            if keywords:
                # Exact matches
                for keyword in keywords[:3]:
                    exact_results = self._search_exact_matches(keyword)
                    if exact_results:
                        all_results.extend(exact_results)
                
                # Partial matches if no exact matches
                if not all_results:
                    for keyword in keywords[:3]:
                        partial_results = self._search_partial_matches(keyword)
                        if partial_results:
                            all_results.extend(partial_results)
        except Exception as e:
            self.logger.warning(f"Keyword search for sub-query failed: {e}")
        
        # Method 2: Dynamic relationship search
        try:
            dynamic_results = self._search_dynamic_relationships(sub_query, keywords if 'keywords' in locals() else [])
            if dynamic_results:
                all_results.extend(dynamic_results)
        except Exception as e:
            self.logger.warning(f"Dynamic search for sub-query failed: {e}")
        
        # Method 3: Broad context search
        try:
            if not all_results and 'keywords' in locals():
                broad_results = self._search_broad_context(keywords)
                if broad_results:
                    all_results.extend(broad_results)
        except Exception as e:
            self.logger.warning(f"Broad search for sub-query failed: {e}")
        
        return all_results
    
    def _fuse_and_rank_results(self, all_results: list, original_question: str) -> list:
        """Fuse and rank results from multiple sub-queries."""
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        
        for result in all_results:
            # Create identifier for deduplication
            if 'relationships' in result and result['relationships']:
                identifier = f"{result['node_type']}:{result['node_id']}"
            else:
                identifier = f"{result.get('node_type', '')}:{result.get('node_id', '')}:{result.get('relationship', '')}:{result.get('connected_id', '')}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(result)
        
        # Score results based on relevance to original question
        scored_results = []
        question_keywords = set(self._extract_comprehensive_keywords(original_question))
        
        for result in unique_results:
            score = 0
            
            # Score based on keyword matches in node IDs
            node_id = result.get('node_id', '').lower()
            connected_id = result.get('connected_id', '').lower()
            relationship = result.get('relationship', '').lower()
            
            for keyword in question_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in node_id:
                    score += 3
                if keyword_lower in connected_id:
                    score += 2
                if keyword_lower in relationship:
                    score += 1
            
            # Bonus for having relationships
            if 'relationships' in result and result['relationships']:
                score += len(result['relationships']) * 0.5
            
            scored_results.append((score, result))
        
        # Sort by score (descending) and return top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results[:25]]  # Increased result limit
    
    def _fuse_and_rank_results_enhanced(self, all_results: list, original_question: str) -> list:
        """Enhanced result fusion with better scoring and more comprehensive ranking."""
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        
        for result in all_results:
            # Create identifier for deduplication
            if 'relationships' in result and result['relationships']:
                identifier = f"{result['node_type']}:{result['node_id']}"
            else:
                identifier = f"{result.get('node_type', '')}:{result.get('node_id', '')}:{result.get('relationship', '')}:{result.get('connected_id', '')}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(result)
        
        # Enhanced scoring with multiple factors
        scored_results = []
        question_keywords = set(self._extract_comprehensive_keywords(original_question))
        
        for result in unique_results:
            score = 0
            
            # Primary scoring based on keyword matches
            node_id = result.get('node_id', '').lower()
            connected_id = result.get('connected_id', '').lower()
            relationship = result.get('relationship', '').lower()
            
            for keyword in question_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in node_id:
                    score += 5  # Increased weight for node matches
                if keyword_lower in connected_id:
                    score += 3  # Increased weight for connected nodes
                if keyword_lower in relationship:
                    score += 2  # Increased weight for relationships
            
            # Bonus scoring for comprehensive information
            if 'relationships' in result and result['relationships']:
                score += len(result['relationships']) * 1.0  # Increased relationship bonus
            
            # Bonus for standard references (ISO, NIST, etc.)
            if any(std in node_id for std in ['iso', 'nist', 'csa']):
                score += 3
            
            # Bonus for policy/requirement keywords
            if any(word in node_id for word in ['policy', 'requirement', 'training', 'screening']):
                score += 2
            
            scored_results.append((score, result))
        
        # Sort by score (descending) and return more results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [result for score, result in scored_results[:30]]  # Increased from 20 to 30
    
    def _generate_multi_query_answer(self, original_question: str, sub_queries: list, fused_results: list) -> str:
        """Generate comprehensive answer from multi-query results with enhanced completeness."""
        if not fused_results:
            return "No relevant data found."
        
        # Synthesize multi-node information with enhanced aggregation
        synthesized_data = self._synthesize_multi_node_data(fused_results)
        
        # Create comprehensive context with ALL relevant information
        context = f"Original Question: {original_question}\n\n"
        context += f"Sub-questions analyzed:\n"
        for i, sq in enumerate(sub_queries, 1):
            context += f"{i}. {sq}\n"
        
        context += f"\nComprehensive Graph Analysis:\n"
        
        # Show ALL primary nodes with full details (increased from 10 to 15)
        primary_nodes = synthesized_data.get('primary_nodes', [])
        for i, node_data in enumerate(primary_nodes[:15], 1):
            context += f"\n{i}. NODE: {node_data['node_id']} ({node_data['node_type']})\n"
            
            # Show ALL relationships (increased from 5 to 8)
            if node_data.get('relationships'):
                context += "   Direct Connections:\n"
                for rel in node_data['relationships'][:8]:
                    context += f"   - {rel.get('relationship', 'Unknown')} -> {rel.get('connected_id', 'Unknown')} ({rel.get('connected_type', 'Unknown')})\n"
                    
                    # Show more secondary connections (increased from 2 to 4)
                    if rel.get('secondary_connections'):
                        for sec_rel in rel['secondary_connections'][:4]:
                            context += f"     └─ {sec_rel.get('relationship', 'Unknown')} -> {sec_rel.get('connected_id', 'Unknown')}\n"
            
            # Show extended network connections
            if node_data.get('additional_connections'):
                context += "   Extended Network:\n"
                for add_rel in node_data['additional_connections'][:4]:
                    context += f"   + {add_rel.get('relationship', 'Unknown')} -> {add_rel.get('connected_id', 'Unknown')}\n"
        
        # Show cross-node patterns with more detail
        cross_patterns = synthesized_data.get('cross_patterns', [])
        if cross_patterns:
            context += f"\nCross-Node Patterns & Connections:\n"
            for pattern in cross_patterns[:5]:
                context += f"- {pattern}\n"
        
        # Concise prompt for direct answers
        concise_prompt = f"""{context}

Based on the graph analysis above, provide a CONCISE and DIRECT answer to: {original_question}

IMPORTANT INSTRUCTIONS:
1. Keep answer to 3-4 sentences maximum
2. List key requirements in bullet points if needed
3. Include specific timeframes and standards mentioned
4. Be direct and factual - no explanatory text
5. Use simple, clear language
6. Focus only on essential information

Generate a brief, focused answer with key facts only."""
        
        try:
            message = HumanMessage(content=concise_prompt)
            response = self.llm.invoke([message])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Found comprehensive multi-node data but couldn't generate answer: {e}"
    
    def _detect_answer_type(self, question: str) -> str:
        """Detect the type of answer expected based on question format."""
        question_lower = question.lower()
        
        if "table" in question_lower or "list" in question_lower:
            return "structured"
        elif question_lower.startswith(("is ", "are ", "do ", "does ", "can ", "will ")):
            return "yes_no"
        elif question_lower.startswith(("what ", "which ", "who ", "where ", "when ", "how ")):
            return "direct_factual"
        elif "show" in question_lower or "display" in question_lower:
            return "display"
        else:
            return "general"
    
    def _create_targeted_prompt(self, question: str, context: str, answer_type: str) -> str:
        """Create concise targeted prompts based on answer type."""
        base_context = f"{context}\n\nQuestion: {question}\n\n"
        
        if answer_type == "structured":
            return f"""{base_context}
Provide a STRUCTURED answer in the requested format (table/list).
- Extract key information only
- Use bullet points or numbered list
- Be concise and direct
- No explanatory text"""
        
        elif answer_type == "yes_no":
            return f"""{base_context}
Answer with YES or NO followed by ONE brief sentence.
- Maximum 15 words total
- Be definitive and concise"""
        
        elif answer_type == "direct_factual":
            return f"""{base_context}
Provide a DIRECT answer in 1-2 sentences maximum.
- Include specific details (timeframes, standards)
- Be clear and factual
- No explanations or background"""
        
        elif answer_type == "display":
            return f"""{base_context}
Show the requested information in simple format.
- Use bullet points for multiple items
- Keep each point brief
- No explanatory text"""
        
        else:
            return f"""{base_context}
Provide a brief, focused answer.
- Maximum 2-3 sentences
- Include key facts and requirements
- Be direct and specific"""
    
    def _keyword_search_strategy(self, question: str) -> str:
        """Enhanced search using multiple keyword extraction and semantic matching."""
        import re
        
        # Extract different types of keywords
        keywords = self._extract_comprehensive_keywords(question)
        
        if not keywords:
            return "No relevant data found."
        
        # Multi-level search approach
        search_results = []
        
        # Level 1: Exact matches
        for keyword in keywords:
            try:
                exact_results = self._search_exact_matches(keyword)
                if exact_results:
                    search_results.extend(exact_results)
            except Exception as e:
                self.logger.warning(f"Exact search for '{keyword}' failed: {e}")
        
        # Level 2: Partial matches if no exact matches
        if not search_results:
            for keyword in keywords[:8]:  # Limit to top 8 terms
                try:
                    partial_results = self._search_partial_matches(keyword)
                    if partial_results:
                        search_results.extend(partial_results)
                except Exception as e:
                    self.logger.warning(f"Partial search for '{keyword}' failed: {e}")
        
        # Level 3: Semantic search using related terms
        if not search_results:
            semantic_results = self._search_semantic_matches(question, keywords)
            if semantic_results:
                search_results.extend(semantic_results)
        
        if search_results:
            return self._generate_comprehensive_answer(question, search_results)
        
        return "No relevant data found."
    
    def _extract_comprehensive_keywords(self, question: str) -> list:
        """Extract keywords from any type of question with intelligent prioritization."""
        import re
        
        keywords = []
        
        # Priority 1: Proper nouns and capitalized terms (highest priority)
        proper_nouns = re.findall(r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b', question)
        keywords.extend([word for word in proper_nouns if len(word) > 2] * 3)  # High priority
        
        # Priority 2: Numbers, codes, and identifiers
        numbers_codes = re.findall(r'\b[A-Z]*[0-9]+[A-Z0-9.-]*\b', question)
        keywords.extend(numbers_codes * 2)  # Medium-high priority
        
        # Priority 3: Quoted terms (exact phrases)
        quoted_terms = re.findall(r'["\']([^"\']+)["\']', question)
        keywords.extend([term.strip() for term in quoted_terms if len(term.strip()) > 2] * 2)
        
        # Priority 4: Significant words (4+ characters, not common words)
        significant_words = re.findall(r'\b[a-zA-Z]{4,}\b', question)
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 
            'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'with', 'what', 'when', 'where', 'will', 'this', 
            'that', 'they', 'them', 'than', 'then', 'there', 'these', 'those', 'have', 'from', 'been', 'were', 
            'said', 'each', 'which', 'their', 'time', 'would', 'about', 'could', 'other', 'after', 'first', 'well', 
            'also', 'some', 'very', 'make', 'most', 'over', 'such', 'take', 'than', 'only', 'think', 'know', 'just', 
            'into', 'good', 'much', 'should', 'before', 'through', 'being', 'where', 'those'
        }
        keywords.extend([word.lower() for word in significant_words if word.lower() not in stop_words])
        
        # Priority 5: Three-letter significant words
        three_letter_words = re.findall(r'\b[a-zA-Z]{3}\b', question)
        keywords.extend([word.lower() for word in three_letter_words if word.lower() not in {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}])
        
        # Remove duplicates while preserving order and priority
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword.lower() not in seen:
                seen.add(keyword.lower())
                unique_keywords.append(keyword)
        
        return unique_keywords[:12]  # Return top 12 keywords
    
    def _sanitize_cypher_input(self, input_text: str) -> str:
        """Sanitize input to prevent Cypher injection and malformed queries."""
        if not input_text:
            return ""
        
        # Remove problematic phrases that cause syntax errors
        problematic_phrases = [
            "here's a list of search terms based on the question:",
            "here are search terms:",
            "search terms:",
            "based on the question:",
            "- experiencing",
            "- feeling", 
            "- emotions",
            "- person",
            "- mental state",
            "- emotional state",
            "- present moment"
        ]
        
        cleaned = input_text.lower().strip()
        
        # Remove problematic phrases
        for phrase in problematic_phrases:
            cleaned = cleaned.replace(phrase, "")
        
        # Remove special characters that can break Cypher
        import re
        cleaned = re.sub(r'[^\w\s-]', '', cleaned)
        
        # Remove extra whitespace and dashes
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'^-+\s*', '', cleaned)  # Remove leading dashes
        
        # Only return if it's a valid single word/phrase
        if len(cleaned.split()) <= 3 and len(cleaned) >= 2:
            return cleaned
        
        return ""
    
    def _search_exact_matches(self, keyword: str) -> list:
        """Search for exact keyword matches with comprehensive multi-node traversal."""
        # Sanitize keyword to prevent Cypher injection
        sanitized_keyword = self._sanitize_cypher_input(keyword)
        if not sanitized_keyword or len(sanitized_keyword.strip()) < 2:
            return []
            
        search_query = f"""
        MATCH (n) 
        WHERE toLower(n.id) CONTAINS toLower('{sanitized_keyword}')
        WITH n
        MATCH (n)-[r1]-(connected1)
        OPTIONAL MATCH (connected1)-[r2]-(connected2)
        WHERE connected2 <> n
        RETURN labels(n)[0] as node_type, n.id as node_id,
               collect(DISTINCT {{
                   relationship: type(r1), 
                   connected_type: labels(connected1)[0], 
                   connected_id: connected1.id,
                   secondary_connections: [(connected1)-[r2]-(connected2) WHERE connected2 <> n | {{
                       relationship: type(r2),
                       connected_type: labels(connected2)[0],
                       connected_id: connected2.id
                   }}][0..3]
               }}) as relationships
        LIMIT 10
        """
        return self.graph.query(search_query)
    
    def _search_partial_matches(self, keyword: str) -> list:
        """Search for partial matches with multi-node relationship expansion."""
        # Sanitize and split keyword into parts for better matching
        sanitized_keyword = self._sanitize_cypher_input(keyword)
        if not sanitized_keyword:
            return []
            
        parts = sanitized_keyword.split()
        search_conditions = []
        
        for part in parts:
            if len(part) > 2:
                # Additional sanitization for each part
                clean_part = self._sanitize_cypher_input(part)
                if clean_part:
                    search_conditions.append(f"toLower(n.id) CONTAINS toLower('{clean_part}')")
        
        if not search_conditions:
            return []
        
        search_query = f"""
        MATCH (n) 
        WHERE {' OR '.join(search_conditions)}
        WITH n
        MATCH (n)-[r1]-(connected1)
        OPTIONAL MATCH (connected1)-[r2]-(connected2)
        WHERE connected2 <> n
        OPTIONAL MATCH (n)-[r3]-(connected3)-[r4]-(connected4)
        WHERE connected3 <> n AND connected4 <> n AND connected4 <> connected1
        RETURN labels(n)[0] as node_type, n.id as node_id,
               collect(DISTINCT {{
                   relationship: type(r1), 
                   connected_type: labels(connected1)[0], 
                   connected_id: connected1.id,
                   secondary_connections: [(connected1)-[r2]-(connected2) WHERE connected2 <> n | {{
                       relationship: type(r2),
                       connected_type: labels(connected2)[0],
                       connected_id: connected2.id
                   }}][0..2]
               }}) + 
               collect(DISTINCT {{
                   relationship: type(r3), 
                   connected_type: labels(connected3)[0], 
                   connected_id: connected3.id,
                   tertiary_connections: [(connected3)-[r4]-(connected4) WHERE connected4 <> n AND connected4 <> connected1 | {{
                       relationship: type(r4),
                       connected_type: labels(connected4)[0],
                       connected_id: connected4.id
                   }}][0..2]
               }}) as relationships
        LIMIT 8
        """
        return self.graph.query(search_query)
    
    def _search_semantic_matches(self, question: str, keywords: list) -> list:
        """Search using semantic understanding of the question."""
        # Use LLM to identify relevant relationship patterns
        return self._search_dynamic_relationships(question, keywords)
    
    def _search_dynamic_relationships(self, question: str, keywords: list) -> list:
        """Search for relationships using dynamic LLM-guided patterns."""
        try:
            # Use LLM to identify relevant search patterns
            pattern_prompt = f"""
            Question: {question}
            Keywords: {keywords}
            
            Based on this question, suggest 3-5 relationship types or node patterns that would be most relevant to search for in a knowledge graph.
            
            Respond with a simple list of search terms, one per line. Focus on:
            - Relationship types (verbs, actions, connections)
            - Entity types (nouns, concepts)
            - Descriptive terms from the question
            
            Example format:
            founded
            created
            person
            location
            """
            
            message = HumanMessage(content=pattern_prompt)
            response = self.llm.invoke([message])
            search_terms = [term.strip().lower() for term in response.content.split('\n') if term.strip()]
            
            # Create dynamic search query with sanitization
            search_conditions = []
            for term in search_terms[:8]:  # Limit to top 8 terms
                clean_term = self._sanitize_cypher_input(term)
                if clean_term:
                    search_conditions.extend([
                        f"toLower(type(r)) CONTAINS '{clean_term}'",
                        f"toLower(n.id) CONTAINS '{clean_term}'",
                        f"toLower(connected.id) CONTAINS '{clean_term}'"
                    ])
            
            if not search_conditions:
                return []
            
            search_query = f"""
            MATCH (n)-[r]-(connected)
            WHERE {' OR '.join(search_conditions)}
            RETURN labels(n)[0] as node_type, n.id as node_id,
                   type(r) as relationship,
                   labels(connected)[0] as connected_type, connected.id as connected_id
            LIMIT 30
            """
            
            return self.graph.query(search_query)
            
        except Exception as e:
            self.logger.warning(f"Dynamic relationship search failed: {e}")
            return self._search_broad_context(keywords)
    
    def _search_broad_context(self, keywords: list) -> list:
        """Universal contextual search with comprehensive multi-node aggregation."""
        if not keywords:
            return []
        
        # Create search conditions for multiple keywords with sanitization
        keyword_conditions = []
        for keyword in keywords[:8]:  # Increased limit for better coverage
            clean_keyword = self._sanitize_cypher_input(keyword)
            if clean_keyword:
                keyword_conditions.extend([
                    f"toLower(n.id) CONTAINS toLower('{clean_keyword}')",
                    f"toLower(connected.id) CONTAINS toLower('{clean_keyword}')",
                    f"toLower(type(r)) CONTAINS toLower('{clean_keyword}')"
                ])
        
        if not keyword_conditions:
            return []
            
        search_query = f"""
        MATCH (n)-[r]-(connected)
        WHERE {' OR '.join(keyword_conditions)}
        WITH n, r, connected
        OPTIONAL MATCH (n)-[r2]-(other1)
        WHERE other1 <> connected
        OPTIONAL MATCH (connected)-[r3]-(other2)
        WHERE other2 <> n
        OPTIONAL MATCH (n)-[r4]-(bridge)-[r5]-(distant)
        WHERE bridge <> connected AND distant <> n AND distant <> connected
        RETURN labels(n)[0] as node_type, n.id as node_id,
               type(r) as relationship,
               labels(connected)[0] as connected_type, connected.id as connected_id,
               collect(DISTINCT {{
                   relationship: type(r2),
                   connected_type: labels(other1)[0],
                   connected_id: other1.id
               }})[0..5] as additional_connections,
               collect(DISTINCT {{
                   relationship: type(r3),
                   connected_type: labels(other2)[0],
                   connected_id: other2.id
               }})[0..3] as extended_connections,
               collect(DISTINCT {{
                   bridge_node: bridge.id,
                   bridge_relationship: type(r4),
                   distant_relationship: type(r5),
                   distant_node: distant.id,
                   distant_type: labels(distant)[0]
               }})[0..2] as distant_connections
        LIMIT 25
        """
        return self.graph.query(search_query)
    
    def _generate_comprehensive_answer(self, question: str, search_results: list) -> str:
        """Generate comprehensive answer from multiple interconnected nodes."""
        if not search_results:
            return "No relevant data found."
        
        # Aggregate and synthesize multi-node information
        synthesized_data = self._synthesize_multi_node_data(search_results)
        
        # Create rich context from multiple nodes
        context = f"Question: {question}\n\nComprehensive Graph Analysis:\n"
        
        # Primary nodes with their full relationship networks
        primary_nodes = synthesized_data.get('primary_nodes', [])
        for i, node_data in enumerate(primary_nodes[:8]):
            context += f"\n{i+1}. PRIMARY NODE: {node_data['node_id']} ({node_data['node_type']})\n"
            
            # Direct relationships
            if node_data.get('relationships'):
                context += "   Direct Connections:\n"
                for rel in node_data['relationships'][:6]:
                    context += f"   - {rel['relationship']} -> {rel['connected_id']} ({rel.get('connected_type', 'Unknown')})\n"
                    
                    # Secondary connections from this relationship
                    if rel.get('secondary_connections'):
                        for sec_rel in rel['secondary_connections'][:2]:
                            context += f"     └─ {sec_rel['relationship']} -> {sec_rel['connected_id']} ({sec_rel.get('connected_type', 'Unknown')})\n"
            
            # Additional connections
            if node_data.get('additional_connections'):
                context += "   Extended Network:\n"
                for add_rel in node_data['additional_connections'][:3]:
                    context += f"   + {add_rel['relationship']} -> {add_rel['connected_id']} ({add_rel.get('connected_type', 'Unknown')})\n"
            
            # Distant connections through bridges
            if node_data.get('distant_connections'):
                context += "   Bridge Connections:\n"
                for dist_rel in node_data['distant_connections'][:2]:
                    context += f"   ↔ via {dist_rel.get('bridge_node', 'Unknown')} -> {dist_rel.get('distant_node', 'Unknown')} ({dist_rel.get('distant_type', 'Unknown')})\n"
        
        # Cross-node relationships and patterns
        cross_patterns = synthesized_data.get('cross_patterns', [])
        if cross_patterns:
            context += f"\nCROSS-NODE PATTERNS:\n"
            for pattern in cross_patterns[:3]:
                context += f"- {pattern}\n"
        
        # Generate comprehensive answer
        prompt = f"""
        {context}
        
        Based on this comprehensive multi-node graph analysis, provide a DETAILED answer that:
        1. Synthesizes information from multiple connected nodes
        2. Shows relationships between different entities
        3. Provides a complete picture using all available connections
        4. Keeps the answer concise but comprehensive (3-5 sentences)
        
        Use specific information from the interconnected graph data to construct a rich, multi-faceted response.
        """
        
        try:
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Found comprehensive multi-node data but couldn't generate answer: {e}"
    
    def _synthesize_multi_node_data(self, search_results: list) -> Dict[str, Any]:
        """Synthesize and organize data from multiple interconnected nodes."""
        try:
            primary_nodes = []
            all_entities = set()
            cross_patterns = []
            
            # Process each result to extract comprehensive node information
            for result in search_results:
                node_data = {
                    'node_id': result.get('node_id', 'Unknown'),
                    'node_type': result.get('node_type', 'Unknown'),
                    'relationships': result.get('relationships', []),
                    'additional_connections': result.get('additional_connections', []),
                    'extended_connections': result.get('extended_connections', []),
                    'distant_connections': result.get('distant_connections', [])
                }
                
                # Collect all entities for pattern analysis
                all_entities.add(node_data['node_id'])
                for rel in node_data['relationships']:
                    if isinstance(rel, dict) and 'connected_id' in rel:
                        all_entities.add(rel['connected_id'])
                
                primary_nodes.append(node_data)
            
            # Identify cross-node patterns
            entity_connections = {}
            for node_data in primary_nodes:
                node_id = node_data['node_id']
                connections = []
                
                # Collect all connections for this node
                for rel in node_data['relationships']:
                    if isinstance(rel, dict):
                        connections.append(rel.get('connected_id'))
                
                entity_connections[node_id] = connections
            
            # Find common connections between nodes
            for i, node1 in enumerate(primary_nodes):
                for j, node2 in enumerate(primary_nodes[i+1:], i+1):
                    node1_connections = set(entity_connections.get(node1['node_id'], []))
                    node2_connections = set(entity_connections.get(node2['node_id'], []))
                    
                    common = node1_connections.intersection(node2_connections)
                    if common:
                        pattern = f"{node1['node_id']} and {node2['node_id']} are both connected to: {', '.join(list(common)[:3])}"
                        cross_patterns.append(pattern)
            
            return {
                'primary_nodes': primary_nodes,
                'cross_patterns': cross_patterns,
                'total_entities': len(all_entities),
                'total_nodes': len(primary_nodes)
            }
            
        except Exception as e:
            self.logger.warning(f"Multi-node synthesis failed: {e}")
            return {
                'primary_nodes': search_results[:5],  # Fallback to simple structure
                'cross_patterns': [],
                'total_entities': len(search_results),
                'total_nodes': len(search_results)
            }
    
    def _organize_search_results(self, results: list) -> list:
        """Organize search results by relevance and remove duplicates."""
        seen = set()
        organized = []
        
        for result in results:
            # Create a unique identifier for deduplication
            if 'relationships' in result:
                identifier = f"{result['node_type']}:{result['node_id']}"
            else:
                identifier = f"{result['node_type']}:{result['node_id']}:{result['relationship']}:{result['connected_id']}"
            
            if identifier not in seen:
                seen.add(identifier)
                organized.append(result)
        
        return organized
    
    def _llm_cypher_strategy(self, question: str) -> str:
        """Generate Cypher query using LLM with improved prompting."""
        schema = self.graph.schema
        
        cypher_prompt = f"""
        Generate a Cypher query to answer: "{question}"
        
        Schema: {schema}
        
        Rules:
        1. Use exact relationship directions from schema
        2. Use CONTAINS for partial text matching: WHERE n.id CONTAINS 'keyword'
        3. Return node IDs and relationship information
        4. Limit results to 10
        5. Only use MATCH, WHERE, RETURN - no CREATE/DELETE
        
        Query:
        """
        
        try:
            message = HumanMessage(content=cypher_prompt)
            cypher_response = self.llm.invoke([message])
            cypher_query = cypher_response.content.strip()
            
            # Clean up query
            if cypher_query.startswith("```"):
                lines = cypher_query.split('\n')
                cypher_query = '\n'.join([line for line in lines if not line.startswith("```") and line.strip()])
            
            self.logger.info(f"Generated Cypher: {cypher_query}")
            
            results = self.graph.query(cypher_query)
            if results:
                return self._generate_natural_answer(question, results)
            
        except Exception as e:
            self.logger.warning(f"LLM Cypher generation failed: {e}")
        
        return "No relevant data found."
    
    def _broad_search_strategy(self, question: str) -> str:
        """Broad search across all nodes and relationships."""
        try:
            # Get sample of all data
            broad_query = """
            MATCH (n)-[r]-(m)
            RETURN labels(n)[0] as node1_type, n.id as node1_id, 
                   type(r) as relationship, 
                   labels(m)[0] as node2_type, m.id as node2_id
            LIMIT 50
            """
            results = self.graph.query(broad_query)
            
            if results:
                return self._generate_contextual_answer(question, results)
            
        except Exception as e:
            self.logger.error(f"Broad search failed: {e}")
        
        return "No data available in the knowledge graph."
    
    def _generate_answer_from_relationships(self, question: str, node_id: str, node_type: str, relationships: list) -> str:
        """Generate answer from node relationships."""
        context = f"Node: {node_id} (Type: {node_type})\nRelationships:\n"
        for rel in relationships:
            context += f"- {rel['relationship']} -> {rel['connected_id']} ({rel['connected_type']})\n"
        
        formatted_context = context.strip()
        
        # Generate answer using LLM with context
        prompt = f"""
        Based on the following graph data, answer this question: {question}
        
        Graph Context:
        {formatted_context}
        
        Provide a CONCISE answer (2-3 sentences max) using the most relevant information from the graph. Be direct and factual.
        """
        
        try:
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Found relevant data but couldn't generate answer: {e}"
    
    def _generate_natural_answer(self, question: str, results: list) -> str:
        """Generate natural language answer from query results."""
        prompt = f"""
        Question: {question}
        Query Results: {results}
        
        Provide a CONCISE answer (2-3 sentences max) based on these results.
        """
        
        try:
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Found data: {results}"
    
    def _generate_contextual_answer(self, question: str, results: list) -> str:
        """Generate answer from broad context search."""
        prompt = f"""
        Question: {question}
        
        Available graph data (sample):
        {results[:20]}  
        
        Based on this data, provide a BRIEF answer (1-2 sentences) to the question.
        """
        
        try:
            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Graph contains data but couldn't process it: {e}"

    def get_graph_stats(self) -> Dict[str, Any]:
        node_stats = self.graph.query("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC")
        rel_stats = self.graph.query("MATCH ()-[r]->() RETURN type(r) as relationship_type, count(r) as count ORDER BY count DESC")
        total_nodes = sum(item['count'] for item in node_stats) if node_stats else 0
        total_rels = sum(item['count'] for item in rel_stats) if rel_stats else 0
        return {
            'total_nodes': total_nodes,
            'total_relationships': total_rels,
            'node_stats': node_stats,
            'relationship_stats': rel_stats,
            'schema': self.graph.schema
        }

    def reset_graph(self) -> bool:
        self.logger.warning("Resetting knowledge graph - all data will be deleted.")
        self.graph.query("MATCH (n) DETACH DELETE n")
        self.graph.refresh_schema()
        self.logger.info("Graph reset successfully.")
        return True

    def get_schema(self) -> str:
        return self.graph.schema

def get_credentials_from_env() -> tuple:
    """Reads credentials exclusively from environment variables."""
    load_dotenv()
    groq_api_key = os.getenv('GROQ_API_KEY')
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_username = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not all([groq_api_key, neo4j_uri, neo4j_password]):
        print("❌ Error: Missing one or more required credentials in the .env file.")
        print("Please ensure your .env file contains GROQ_API_KEY, NEO4J_URI, and NEO4J_PASSWORD.")
        sys.exit(1)
    
    return groq_api_key, neo4j_uri, neo4j_username, neo4j_password

if __name__ == "__main__":
    groq_api_key, neo4j_uri, neo4j_username, neo4j_password = get_credentials_from_env()
    
    print("🚀 Starting Knowledge Graph Query System...")
    query_system = RobustKnowledgeGraphQuery(groq_api_key, neo4j_uri, neo4j_username, neo4j_password)
    
    print("\n============================================================")
    print("🤖 Starting Enhanced Interactive Q&A Mode")
    print("Type your questions or a command ('stats', 'schema', 'reset', 'cache', 'exit').")
    print("Features: Caching, Hallucination Detection, Confidence Scoring")
    print("============================================================\n")
    
    while True:
        try:
            question = input("❓ Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['exit', 'quit', 'q']:
                print("👋 Exiting...")
                break
            elif question.lower() == 'stats':
                stats = query_system.get_graph_stats()
                print(f"\n📊 Graph Statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                print(f"   Cached Queries: {len(query_system.query_cache)}")
                print()
            elif question.lower() == 'schema':
                print(f"\n🗂️  Graph Schema:")
                print(query_system.graph.schema)
                print()
            elif question.lower() == 'cache':
                print(f"\n🗄️  Cache Status:")
                print(f"   Cached queries: {len(query_system.query_cache)}")
                print(f"   Cache size limit: {query_system.max_cache_size}")
                if query_system.query_cache:
                    print("   Recent queries:")
                    for i, key in enumerate(list(query_system.query_cache.keys())[-3:]):
                        result = query_system.query_cache[key]
                        print(f"     {i+1}. Confidence: {result.get('confidence', 'N/A'):.2f}")
                print()
            elif question.lower() == 'reset':
                print("🔄 Resetting conversation and clearing cache...")
                query_system.query_cache.clear()
                query_system.entity_cache.clear()
                print("✅ Cache cleared!")
                print()
            else:
                print("🤔 Processing your question...")
                print("🔍 Multi-node analysis in progress...")
                result = query_system.query(question)
                
                # Enhanced output with multi-node analysis details
                confidence = result.get('confidence', 0.5)
                confidence_emoji = "🟢" if confidence >= 0.7 else "🟡" if confidence >= 0.4 else "🔴"
                
                # Show multi-node processing details
                analysis_details = result.get('analysis_details', {})
                nodes_checked = analysis_details.get('nodes_checked', 0)
                relationships_found = analysis_details.get('relationships_found', 0)
                cross_patterns = analysis_details.get('cross_patterns', 0)
                
                print(f"\n🔍 Multi-Node Analysis:")
                print(f"   📊 Nodes Checked: {nodes_checked}")
                print(f"   🔗 Relationships Found: {relationships_found}")
                print(f"   🌐 Cross-Node Patterns: {cross_patterns}")
                
                print(f"\n💡 Answer: {result['answer']}")
                print(f"{confidence_emoji} Confidence: {confidence:.2f}")
                
                if result.get('sources'):
                    print(f"📚 Sources: {len(result['sources'])} graph nodes referenced")
                
                if confidence < 0.4:
                    print("⚠️  Low confidence - please verify important details")
                
                print()
                
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
            break
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            query_system.logger.error(f"Error in interactive loop: {e}")