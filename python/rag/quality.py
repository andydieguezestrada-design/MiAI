from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RAGRelevanceReport:
    """Decision returned by the RAG relevance gate."""
    accepted: bool
    score: float
    threshold: float
    reason: str


class RAGRelevanceGate:
    """Reject weak retrieval results before they contaminate model context.

    The gate is deliberately small and provider-agnostic.  It works with the
    existing lexical score and with the optional hybrid semantic score added
    in V0.11.  Exact matches are always allowed when their score is positive.
    """

    def __init__(self, threshold: float | None = None):
        if threshold is None:
            threshold = float(os.getenv("MIAI_RAG_MIN_SCORE", "0.08"))
        self.threshold = max(0.0, float(threshold))

    def assess(self, score: float, *, exact_match: bool = False) -> RAGRelevanceReport:
        score = float(score)
        if exact_match and score > 0:
            return RAGRelevanceReport(True, score, self.threshold, "exact_match")
        accepted = score >= self.threshold and score > 0
        reason = "above_threshold" if accepted else "below_threshold"
        return RAGRelevanceReport(accepted, score, self.threshold, reason)
