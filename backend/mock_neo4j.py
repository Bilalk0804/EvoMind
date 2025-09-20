#!/usr/bin/env python3
"""
Simple Mock Neo4j for fallback when real Neo4j is unavailable.
"""
import logging

class MockNeo4jGraph:
    """Mock Neo4j Graph for testing."""
    
    def __init__(self, url=None, username=None, password=None, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔧 Using Mock Neo4j (real Neo4j unavailable)")
        self._schema = "Mock Schema: No real graph structure available"
    
    @property
    def schema(self):
        return self._schema
    
    def query(self, query, params=None):
        """Mock query that returns empty results."""
        self.logger.info(f"Mock query executed: {query[:50]}...")
        return [{"answer": "Mock Neo4j response", "confidence": 0.1, "sources": []}]
    
    def add_graph_documents(self, documents, **kwargs):
        """Mock document addition."""
        self.logger.info(f"Mock: Would add {len(documents)} documents")
        return True
    
    def refresh_schema(self):
        """Mock schema refresh."""
        self.logger.info("Mock: Schema refresh completed")
        return True

def create_mock_graph(uri, username, password):
    """Create a mock graph instance."""
    return MockNeo4jGraph(url=uri, username=username, password=password)
