"""
Bias Detector - Detector contínuo de viés em produção.

Re-export de BiasDetector do metrics.py para compatibilidade.
"""

from src.fairness.metrics import BiasDetector

__all__ = ["BiasDetector"]