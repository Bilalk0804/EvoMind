"""
Cleaned & refactored Knowledge Graph Builder

Goals of refactor:
- Remove excessive defensive try/except blocks
- Remove over-engineered connection retries and silent fallbacks
- Separate concerns: loading, preprocessing, extraction, persistence
- Make KG schema + therapy schema explicit and predictable
- Keep LLM usage intentional (no LLM calls inside tight loops unless necessary)
- Make this safe to call from an API server

This version is simpler, faster, and far easier to reason about.
"""

from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("kg_builder")

# -----------------------------------------------------------------------------
# Knowledge Graph Builder
# -----------------------------------------------------------------------------
class RobustKnowledgeGraphBuilder:
    """Builds and maintains a Neo4j-based Knowledge Graph for documents and therapy sessions."""

    # ----------------------------
    # Initialization
    # ----------------------------
    def __init__(self, groq_api_key: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        if not all([groq_api_key, neo4j_uri, neo4j_user, neo4j_password]):
            raise RuntimeError("Missing required KG credentials")

        self.llm = ChatGroq(
            api_key=groq_api_key,
            model="qwen/qwen3-32b",
            temperature=0.1,
            max_tokens=4096,
        )

        self.graph = Neo4jGraph(
            url=neo4j_uri,
            username=neo4j_user,
            password=neo4j_password,
        )

        # Test connection explicitly
        self.graph.query("RETURN 1")
        logger.info("Connected to Neo4j")

        self.transformer = LLMGraphTransformer(
            llm=self.llm,
            strict_mode=False,
            node_properties=["description", "type", "importance", "context"],
            relationship_properties=["description", "strength", "context"],
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
        )

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------
    def load_documents(self, files: List[str]) -> List[Document]:
        docs: List[Document] = []

        for path in files:
            suffix = Path(path).suffix.lower()
            if suffix == ".pdf":
                loader = PyPDFLoader(path)
            elif suffix in {".txt", ".md"}:
                loader = TextLoader(path, encoding="utf-8")
            elif suffix == ".docx":
                loader = UnstructuredWordDocumentLoader(path)
            else:
                logger.warning("Unsupported file skipped: %s", path)
                continue

            loaded = loader.load()
            docs.extend(loaded)
            logger.info("Loaded %s (%d pages)", path, len(loaded))

        return docs

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------
    def enhance_documents(self, docs: List[Document]) -> List[Document]:
        for doc in docs:
            doc.metadata["length"] = len(doc.page_content)
            doc.page_content = self._normalize_text(doc.page_content)
        return docs

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r"(\d{4})", r"[YEAR] \\1", text)
        text = re.sub(r"(founded|created|established|invented)", r"[ACTION] \\1", text, flags=re.I)
        return text

    # ------------------------------------------------------------------
    # Graph extraction
    # ------------------------------------------------------------------
    def documents_to_graph(self, docs: List[Document]) -> List[Any]:
        chunks = self.splitter.split_documents(docs)
        logger.info("Split into %d chunks", len(chunks))

        graph_docs = []
        for i, chunk in enumerate(chunks, 1):
            prompt = self._extraction_prompt(chunk.page_content)
            enriched = Document(page_content=prompt, metadata=chunk.metadata)
            graph_docs.extend(self.transformer.convert_to_graph_documents([enriched]))

            if i % 10 == 0:
                logger.info("Processed %d chunks", i)

        return graph_docs

    def _extraction_prompt(self, content: str) -> str:
        return f"""
Extract a comprehensive knowledge graph from the following text.

Rules:
- Extract entities (people, orgs, concepts, events, places, dates)
- Extract relationships (causal, temporal, hierarchical)
- Preserve meaning and context
- Prefer explicit facts over speculation

TEXT:
{content}
"""

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def persist_graph(self, graph_docs: List[Any], batch_size: int = 10) -> Dict[str, int]:
        nodes = relationships = 0

        for i in range(0, len(graph_docs), batch_size):
            batch = graph_docs[i : i + batch_size]
            self.graph.add_graph_documents(batch)
            logger.info("Persisted batch %d", (i // batch_size) + 1)

            for doc in batch:
                nodes += len(doc.nodes)
                relationships += len(doc.relationships)

        self.graph.refresh_schema()
        return {"nodes": nodes, "relationships": relationships}

    # ------------------------------------------------------------------
    # Public pipeline
    # ------------------------------------------------------------------
    def process_documents(self, files: List[str]) -> Dict[str, Any]:
        start = datetime.utcnow()

        docs = self.load_documents(files)
        if not docs:
            return {"nodes": 0, "relationships": 0, "time": 0}

        docs = self.enhance_documents(docs)
        graph_docs = self.documents_to_graph(docs)
        stats = self.persist_graph(graph_docs)

        stats["time"] = (datetime.utcnow() - start).total_seconds()
        return stats

    # ------------------------------------------------------------------
    # Therapy schema (used by chat system)
    # ------------------------------------------------------------------
    def store_therapy_qa_pair(
        self,
        session_id: str,
        qa_number: int,
        question: str,
        answer: str,
        original_concern: str,
        user_id: str = "default_user",
    ) -> None:
        ts = datetime.utcnow().isoformat()

        query = """
MERGE (u:User {user_id: $user_id})
MERGE (s:Session {session_id: $session_id})
  ON CREATE SET s.created_at = $ts, s.original_concern = $original
MERGE (u)-[:HAS_SESSION]->(s)

MERGE (q:Question {id: $qid})
  ON CREATE SET q.text = $question, q.created_at = $ts
MERGE (a:Answer {id: $aid})
  ON CREATE SET a.text = $answer, a.created_at = $ts

MERGE (s)-[:ASKED]->(q)
MERGE (q)-[:ANSWERED_BY]->(a)
"""

        self.graph.query(
            query,
            {
                "user_id": user_id,
                "session_id": session_id,
                "qid": f"{session_id}_q{qa_number}",
                "aid": f"{session_id}_a{qa_number}",
                "question": question,
                "answer": answer,
                "original": original_concern,
                "ts": ts,
            },
        )

    def analyze_therapy_patterns(self, session_id: str, qa_pairs: List[Dict[str, str]], user_id: str) -> str:
        query = """
MATCH (u:User {user_id: $user_id})-[:HAS_SESSION]->(s:Session {session_id: $sid})
MATCH (s)-[:ASKED]->(q)-[:ANSWERED_BY]->(a)
RETURN q.text AS question, a.text AS answer
ORDER BY q.created_at
"""

        rows = self.graph.query(query, {"sid": session_id, "user_id": user_id})
        if not rows:
            return ""

        context = "THERAPY SESSION CONTEXT:\n"
        for i, r in enumerate(rows, 1):
            context += f"Q{i}: {r['question']}\nA{i}: {r['answer']}\n\n"
        return context


# -----------------------------------------------------------------------------
# Standalone execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    load_dotenv()

    required = ["GROQ_API_KEY", "NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

    builder = RobustKnowledgeGraphBuilder(
        os.getenv("GROQ_API_KEY"),
        os.getenv("NEO4J_URI"),
        os.getenv("NEO4J_USERNAME"),
        os.getenv("NEO4J_PASSWORD"),
    )

    docs_dir = Path("documents")
    files = [str(p) for p in docs_dir.rglob("*") if p.suffix.lower() in {".pdf", ".txt", ".md", ".docx"}]

    if not files:
        logger.info("No documents found")
    else:
        stats = builder.process_documents(files)
        logger.info("Graph built: %s", stats)
