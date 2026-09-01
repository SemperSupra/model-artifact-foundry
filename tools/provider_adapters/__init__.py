"""In-tree provider adapters for proven Foundry boundaries.

This package is intentionally explicit and in-tree. It is not a plugin manager and
performs no entry-point discovery. Extraction to separately distributed wheels is
deferred until multiple real implementations validate a stable boundary.
"""

from .contracts import NORMALIZE_OBSERVATION, ProviderEvidenceAdapter
from .huggingface import HUGGINGFACE_ADAPTER, HuggingFaceEvidenceAdapter

__all__ = [
    "HUGGINGFACE_ADAPTER",
    "NORMALIZE_OBSERVATION",
    "HuggingFaceEvidenceAdapter",
    "ProviderEvidenceAdapter",
]
