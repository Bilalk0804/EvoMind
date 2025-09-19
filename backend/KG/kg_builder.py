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
                model_name="gemma2-9b-it",
                temperature=0.1,
                max_tokens=4096
            )
            # Try Neo4j connection with fallback to mock
            try:
                self.graph = Neo4jGraph(url=neo4j_uri, username=neo4j_username, password=neo4j_password)
                self.logger.info("✅ Connected to Neo4j successfully")
            except Exception as neo4j_error:
                self.logger.warning(f"Neo4j connection failed: {neo4j_error}")
                self.logger.info("🔧 Using mock Neo4j for testing...")
                from mock_neo4j import create_mock_graph
                self.graph = create_mock_graph(neo4j_uri, neo4j_username, neo4j_password)
            
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