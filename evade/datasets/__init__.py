"""
EVADE Dataset Package
Provides dataset schemas, GitHub benchmark loaders, programmatic generators,
deduplication, 8-point automated validation, and condition context generation.
"""

from .schema import EVADEItem, ContextCondition, SourceMeta, ContaminationMeta, ValidationMeta

__all__ = [
    "EVADEItem",
    "ContextCondition",
    "SourceMeta",
    "ContaminationMeta",
    "ValidationMeta",
]
