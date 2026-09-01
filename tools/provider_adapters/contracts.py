"""Narrow contracts for provider-specific evidence normalization.

The contract here reflects only behavior already proven by the current MVP work:
provider evidence can be normalized into a deterministic Foundry observation. It is
not a general provider/plugin API and intentionally says nothing about acquisition,
runtime loading, policy, qualification, deployment, or plugin discovery.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

NORMALIZE_OBSERVATION = "normalize_observation"


@runtime_checkable
class ProviderEvidenceAdapter(Protocol):
    """Adapter for normalizing captured provider evidence.

    Implementations remain provider-specific; consumers receive only normalized
    Foundry observation dictionaries rather than provider SDK objects.
    """

    provider_id: str
    capabilities: frozenset[str]

    def normalize_observation(
        self,
        fixture: dict[str, Any],
        provenance: dict[str, Any],
        *,
        fixture_ref: str,
        provenance_ref: str,
    ) -> dict[str, Any]:
        """Normalize captured evidence without live provider access."""
        ...
