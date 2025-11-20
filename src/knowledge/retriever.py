"""Hybrid knowledge retrieval system combining structured data with semantic search."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from openai import OpenAI


class KnowledgeRetriever:
    """Hybrid retriever for Soomgo knowledge base.

    Combines:
    1. Structured lookup (exact info like pricing, policies)
    2. Semantic search (FAQ questions using OpenAI embeddings)
    """

    def __init__(
        self,
        data_dir: str = "data/knowledge",
        embedding_model: str = "text-embedding-3-small",
    ):
        """Initialize retriever.

        Args:
            data_dir: Directory containing knowledge files
            embedding_model: OpenAI embedding model to use
        """
        self.data_dir = Path(data_dir)
        self.embedding_model = embedding_model

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = OpenAI(api_key=api_key)

        # Load structured data
        self.services = self._load_json("structured/services.json")
        self.policies = self._load_json("structured/policies.json")

        # Load semantic FAQ
        faq_data = self._load_json("semantic/faq.json")
        self.faqs = faq_data["faqs"]
        self.faq_questions = [faq["question"] for faq in self.faqs]

        # Pre-compute FAQ embeddings
        print(f"Computing embeddings for {len(self.faqs)} FAQs using OpenAI...")
        self.faq_embeddings = self._compute_embeddings(self.faq_questions)
        print("✓ Knowledge base loaded!")

    def _load_json(self, relative_path: str) -> Dict:
        """Load JSON file from data directory."""
        path = self.data_dir / relative_path
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _compute_embeddings(self, texts: List[str]) -> np.ndarray:
        """Compute embeddings for a list of texts using OpenAI API.

        Args:
            texts: List of texts to embed

        Returns:
            NumPy array of embeddings (shape: [len(texts), embedding_dim])
        """
        response = self.client.embeddings.create(
            input=texts,
            model=self.embedding_model
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings)

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            NumPy array of embedding
        """
        response = self.client.embeddings.create(
            input=[text],
            model=self.embedding_model
        )
        return np.array(response.data[0].embedding)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """Retrieve relevant knowledge for a query.

        Args:
            query: User's question or message
            top_k: Number of similar FAQs to retrieve
            threshold: Minimum similarity score (0-1)

        Returns:
            Dictionary with retrieved knowledge:
            {
                "structured": {...},  # Exact lookups
                "faqs": [...]         # Similar FAQs
            }
        """
        result = {
            "structured": {},
            "faqs": []
        }

        # 1. Structured lookup (keyword matching)
        structured = self._structured_lookup(query)
        if structured:
            result["structured"] = structured

        # 2. Semantic FAQ search
        similar_faqs = self._semantic_search(query, top_k, threshold)
        if similar_faqs:
            result["faqs"] = similar_faqs

        return result

    def _structured_lookup(self, query: str) -> Dict[str, Any]:
        """Look up structured information based on keywords."""
        query_lower = query.lower()
        result = {}

        # Service lookup
        for service_name, service_data in self.services.items():
            keywords = service_data.get("keywords", [])
            if any(kw in query_lower for kw in keywords):
                result[service_name] = service_data

        # Policy lookup
        for policy_name, policy_data in self.policies.items():
            keywords = policy_data.get("keywords", [])
            if any(kw in query_lower for kw in keywords):
                result[policy_name] = policy_data

        return result

    def _semantic_search(
        self,
        query: str,
        top_k: int,
        threshold: float
    ) -> List[Dict]:
        """Search for similar FAQs using semantic similarity with OpenAI embeddings."""
        # Get query embedding
        query_embedding = self._get_embedding(query)

        # Compute cosine similarity
        similarities = np.dot(self.faq_embeddings, query_embedding) / (
            np.linalg.norm(self.faq_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        # Get top-k results above threshold
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                faq = self.faqs[idx].copy()
                faq["similarity_score"] = score
                results.append(faq)

        return results

    def format_knowledge(self, retrieved: Dict[str, Any]) -> str:
        """Format retrieved knowledge into a readable string for prompting.

        Args:
            retrieved: Output from retrieve()

        Returns:
            Formatted knowledge string
        """
        parts = []

        # Format structured data
        if retrieved.get("structured"):
            parts.append("## 📋 정확한 정보")
            for key, data in retrieved["structured"].items():
                parts.append(f"\n### {data.get('name', key)}")
                parts.append(self._format_structured_item(data))

        # Format FAQs
        if retrieved.get("faqs"):
            parts.append("\n## 💡 관련 FAQ")
            for i, faq in enumerate(retrieved["faqs"], 1):
                parts.append(f"\n**Q{i}:** {faq['question']}")
                parts.append(f"**A{i}:** {faq['answer']}")

        return "\n".join(parts) if parts else ""

    def _format_structured_item(self, data: Dict) -> str:
        """Format a single structured data item."""
        lines = []

        # Handle services with types (e.g., 자기소개서)
        if "types" in data:
            for type_name, type_data in data["types"].items():
                lines.append(f"\n**{type_name}:**")
                lines.append(self._format_pricing_turnaround(type_data))
        else:
            # Single service (e.g., 이력서)
            lines.append(self._format_pricing_turnaround(data))

        # Description
        if "description" in data:
            lines.append(f"- 설명: {data['description']}")

        # Note
        if "note" in data:
            lines.append(f"- 참고: {data['note']}")

        # Revision
        if "revision" in data:
            lines.append(f"- 수정: {data['revision']}")

        # Policy-specific fields
        if "rules" in data:
            lines.append("- 규칙:")
            for rule in data["rules"]:
                lines.append(f"  - {rule['condition']}: {rule['refund']} ({rule['description']})")

        if "options" in data:
            lines.append("- 옵션:")
            for option in data["options"]:
                lines.append(f"  - {option['duration']}: {option['display']}")

        if "methods" in data:
            lines.append("- 결제 방법:")
            for method in data["methods"]:
                lines.append(f"  - {method['type']}")

        return "\n".join(lines)

    def _format_pricing_turnaround(self, data: Dict) -> str:
        """Format pricing and turnaround for a service."""
        lines = []

        # Pricing
        if "pricing" in data:
            pricing = data["pricing"]
            if "rate" in pricing:
                lines.append(f"- 가격: {pricing['rate']:,}원/{pricing['unit']}")
                if "calculation" in pricing:
                    lines.append(f"  - 계산: {pricing['calculation']}")
                if "examples" in pricing:
                    for ex in pricing["examples"]:
                        lines.append(f"  - 예시: {ex.get('length', ex.get('slides', ex.get('sets', ex.get('session', ''))))} = {ex['price']}")
            elif "amount" in pricing:
                lines.append(f"- 가격: {pricing['amount']:,}원")
                if "basis" in pricing:
                    lines.append(f"  - 기준: {pricing['basis']}")
            elif "tiers" in pricing:
                lines.append("- 가격:")
                for tier in pricing["tiers"]:
                    lines.append(f"  - {tier['session']}: {tier['display']}")

        # Turnaround
        if "turnaround" in data:
            lines.append(f"- 작업기간: {data['turnaround']}")

        return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    retriever = KnowledgeRetriever()

    test_queries = [
        "자기소개서 가격이 얼마예요?",
        "비용이 부담돼요",
        "급하게 할 수 있나요?",
        "환불 가능한가요?"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print('='*80)

        retrieved = retriever.retrieve(query)
        formatted = retriever.format_knowledge(retrieved)

        print(formatted)
        print()
