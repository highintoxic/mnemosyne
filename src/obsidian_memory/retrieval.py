from __future__ import annotations
from pathlib import Path
from typing import Protocol
import math
import re

from .config import VaultConfig
from .notes import read_note


class SemanticProvider(Protocol):
    def search(self, query: str, documents: list[dict[str, object]], limit: int) -> list[dict[str, object]]: ...


class Retriever:
    def __init__(self, vault: Path, provider: SemanticProvider | None = None):
        self.config = VaultConfig.load(Path(vault))
        self.vault = self.config.vault
        self.provider = provider

    def search(self, query: str, filters: dict[str, object] | None = None, limit: int = 10) -> list[dict[str, object]]:
        filters = filters or {}
        terms = [term.lower() for term in re.findall(r"[\w-]+", query) if len(term) > 1]
        candidates: list[dict[str, object]] = []
        managed_roots = [self.vault / "memories", self.vault / "entities", self.vault / "sessions"]
        for root in managed_roots:
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                try:
                    metadata, body = read_note(path)
                except (OSError, ValueError):
                    continue
                if metadata.get("status") in {"archived", "rejected"}:
                    continue
                if filters.get("type") and metadata.get("type") != filters["type"]:
                    continue
                haystack = (path.stem + " " + str(metadata.get("title", "")) + " " + body).lower()
                matches = sum(term in haystack for term in terms)
                if terms and not matches:
                    continue
                try:
                    confidence = float(metadata.get("confidence", 0.5))
                    importance = float(metadata.get("importance", 0.5))
                except (TypeError, ValueError):
                    confidence, importance = 0.5, 0.5
                score = matches * 10 + importance * 2 + confidence
                candidates.append({"id": path.stem, "note_id": metadata.get("id", path.stem), "title": metadata.get("title", path.stem),
                                   "type": metadata.get("type", "unknown"), "excerpt": body[:500],
                                   "confidence": confidence, "score": score,
                                   "source_path": str(path.relative_to(self.vault))})
        candidates.sort(key=lambda item: float(item["score"]), reverse=True)
        if self.provider is not None:
            candidates = self._blend_provider_scores(query, candidates)
        selected = candidates[:limit]
        if selected:
            known = {item["id"] for item in selected}
            relation_terms = {str(item["id"]) for item in selected}
            for relation_path in (self.vault / "relations").glob("*.md"):
                try:
                    metadata, _ = read_note(relation_path)
                except (OSError, ValueError):
                    continue
                source, target = metadata.get("source"), metadata.get("target")
                if source in relation_terms or target in relation_terms:
                    related_id = target if source in relation_terms else source
                    if related_id in known:
                        continue
                    related = self._result_for_id(str(related_id))
                    if related:
                        related["score"] = max(0.1, float(related["score"]) * 0.5)
                        selected.append(related)
                        known.add(related_id)
        return selected[:limit]

    def _blend_provider_scores(self, query: str, candidates: list[dict[str, object]]) -> list[dict[str, object]]:
        try:
            documents = [{"id": str(item["id"]), "text": f"{item.get('title', '')} {item.get('excerpt', '')}"} for item in candidates]
            scores = {str(result["id"]): float(result["score"]) for result in self.provider.search(query, documents, limit=len(documents))}
        except Exception:
            return candidates
        for item in candidates:
            item["score"] = float(item["score"]) + 5.0 * scores.get(str(item["id"]), 0.0)
        candidates.sort(key=lambda item: float(item["score"]), reverse=True)
        return candidates

    def _result_for_id(self, identifier: str) -> dict[str, object] | None:
        for root in (self.vault / "memories", self.vault / "entities", self.vault / "sessions"):
            for path in root.rglob("*.md") if root.exists() else ():
                try:
                    metadata, body = read_note(path)
                except (OSError, ValueError):
                    continue
                if metadata.get("id") == identifier or path.stem == identifier:
                    return {"id": path.stem, "note_id": metadata.get("id", path.stem), "title": metadata.get("title", path.stem),
                            "type": metadata.get("type", "unknown"), "excerpt": body[:500],
                            "confidence": float(metadata.get("confidence", 0.5)), "score": 1.0,
                            "source_path": str(path.relative_to(self.vault))}
        return None
