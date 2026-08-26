"""Optional semantic providers. Pure stdlib; no network access required."""
from __future__ import annotations

from collections import Counter
from math import log, sqrt
import re


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[\w-]+", text.lower()) if len(token) > 1]


class TfidfProvider:
    """Rank documents against a query using TF-IDF cosine similarity."""

    def search(self, query: str, documents: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
        doc_tokens = [_tokens(str(document.get("text", ""))) for document in documents]
        total_docs = max(1, len(documents))
        document_frequency: Counter[str] = Counter()
        for tokens in doc_tokens:
            document_frequency.update(set(tokens))
        query_counts = Counter(_tokens(query))
        if not query_counts:
            return [{"id": str(document["id"]), "score": 0.0} for document in documents[:limit]]

        results = []
        for document, tokens in zip(documents, doc_tokens):
            term_counts = Counter(tokens)
            score = 0.0
            norm = sqrt(sum((count * (log(1 + count))) ** 2 for count in term_counts.values()))
            for term, query_count in query_counts.items():
                if term not in term_counts:
                    continue
                idf = log(total_docs / (1 + document_frequency[term])) + 1.0
                weight = (1 + log(term_counts[term])) * idf
                score += weight * query_count
            results.append({"id": str(document["id"]), "score": score / norm if norm else 0.0})
        results.sort(key=lambda item: float(item["score"]), reverse=True)
        return results[:limit]
