"""
Edge Masker - Re-export do DynamicMasker para o módulo edge.

Este arquivo provê compatibilidade de imports, redirecionando
para a implementação principal em src/privacy/masker.py.
"""

from src.privacy.masker import BoundingBox, DynamicMasker

__all__ = ["BoundingBox", "DynamicMasker"]
