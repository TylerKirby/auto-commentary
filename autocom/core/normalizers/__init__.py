"""
Normalizers for converting raw dictionary data to NormalizedLexicalEntry.

Each normalizer transforms source-specific data structures into the canonical
NormalizedLexicalEntry model, handling headword reconstruction, POS mapping,
and sense cleaning.
"""

from autocom.core.normalizers.whitakers import WhitakersNormalizer

__all__ = ["WhitakersNormalizer"]
