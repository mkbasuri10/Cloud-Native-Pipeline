from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class DocumentResult:
    doc_id: str
    title: str
    score: float
    snippet: str


class DocumentStore:
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self._documents: list[tuple[str, str]] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._load_documents()

    def _load_documents(self) -> None:
        docs = []
        for path in sorted(self.docs_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            docs.append((path.stem, text))
        self._documents = docs
        if docs:
            self._vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = self._vectorizer.fit_transform([text for _, text in docs])

    def search(self, query: str, top_k: int = 3) -> list[DocumentResult]:
        if not self._documents or not self._vectorizer or self._matrix is None:
            return []
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        results: list[DocumentResult] = []
        for idx, score in ranked[:top_k]:
            doc_id, text = self._documents[idx]
            snippet = _snippet(text, query)
            results.append(DocumentResult(doc_id=doc_id, title=doc_id.replace("_", " ").title(), score=float(score), snippet=snippet))
        return results


def _snippet(text: str, query: str, window: int = 160) -> str:
    lowered = text.lower()
    q = query.lower()
    pos = lowered.find(q)
    if pos == -1:
        return text[:window].strip()
    start = max(pos - window // 4, 0)
    end = min(start + window, len(text))
    return text[start:end].strip()
