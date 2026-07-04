"""
Conditional Unblurer - Re-exports from masker.py para compatibilidade.

Este arquivo mantém compatibilidade com imports que esperam
conditional_unblur.py como módulo separado.
"""

from src.privacy.masker import ConditionalUnblurer, create_blurred_preview

__all__ = ["ConditionalUnblurer", "create_blurred_preview"]