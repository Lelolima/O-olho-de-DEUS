"""Testes para Fairness Metrics."""

import unittest
import numpy as np
from src.fairness.metrics import FairnessMetrics, BiasDetector


class TestFairnessMetrics(unittest.TestCase):
    """Testes para métricas de fairness."""

    def setUp(self):
        """Configura teste."""
        self.metrics = FairnessMetrics()

    def test_demographic_parity_equal(self):
        """Testa paridade demográfica com grupos iguais."""
        # Ambos grupos têm 50% de positivos
        y_pred = np.array([1, 0, 1, 0, 1, 0, 1, 0])
        sensitive = np.array(["A", "A", "A", "A", "B", "B", "B", "B"])

        result = self.metrics.demographic_parity(y_pred, sensitive)

        self.assertEqual(result.max_disparity, 0.0)
        self.assertTrue(result.passed)

    def test_demographic_parity_unequal(self):
        """Testa paridade demográfica com disparidade."""
        # Grupo A: 100% positivos, Grupo B: 0% positivos
        y_pred = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        sensitive = np.array(["A", "A", "A", "A", "B", "B", "B", "B"])

        result = self.metrics.demographic_parity(y_pred, sensitive)

        self.assertEqual(result.max_disparity, 1.0)
        self.assertFalse(result.passed)

    def test_equal_opportunity(self):
        """Testa equal opportunity."""
        # Ambos grupos detectam 100% dos positivos reais
        y_true = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        y_pred = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        sensitive = np.array(["A", "A", "A", "A", "B", "B", "B", "B"])

        result = self.metrics.equal_opportunity(y_true, y_pred, sensitive)

        self.assertEqual(result.max_disparity, 0.0)
        self.assertTrue(result.passed)

    def test_false_positive_rate_balance(self):
        """Testa false positive rate balance."""
        # Grupo A tem mais falsos positivos que B
        y_true = np.array([0, 0, 0, 0, 0, 0, 0, 0])
        y_pred = np.array([1, 1, 0, 0, 0, 0, 0, 0])  # A: 50% FPR, B: 0% FPR
        sensitive = np.array(["A", "A", "A", "A", "B", "B", "B", "B"])

        result = self.metrics.false_positive_rate_balance(y_true, y_pred, sensitive)

        self.assertEqual(result.max_disparity, 0.5)
        self.assertFalse(result.passed)

    def test_generate_fairness_report(self):
        """Testa relatório completo de fairness."""
        y_pred = np.array([1, 0, 1, 0, 1, 0, 1, 0])
        y_true = np.array([1, 0, 1, 0, 1, 0, 1, 0])
        sensitive = np.array(["A", "A", "A", "A", "B", "B", "B", "B"])

        report = self.metrics.generate_fairness_report(y_pred, y_true, sensitive)

        self.assertIn("overall_passed", report)
        self.assertIn("metrics", report)
        self.assertIn("recommendations", report)
        self.assertEqual(report["sample_size"], 8)


class TestBiasDetector(unittest.TestCase):
    """Testes para detector de viés."""

    def setUp(self):
        """Configura teste."""
        self.detector = BiasDetector(window_size=50, check_interval=10)

    def test_record_decision(self):
        """Testa registro de decisões."""
        self.detector.record(
            prediction=1,
            ground_truth=1,
            sensitive_attr="A"
        )

        self.assertEqual(len(self.detector._predictions), 1)

    def test_check_bias_insufficient_samples(self):
        """Testa verificação com amostras insuficientes."""
        # Registra poucas amostras
        for _ in range(5):
            self.detector.record(1, 1, "A")

        result = self.detector.check_bias()

        # Retorna None se amostras insuficientes
        # ou resultado com warning
        self.assertIsNone(result) or self.assertIn("samples_analyzed", result)


if __name__ == "__main__":
    unittest.main()