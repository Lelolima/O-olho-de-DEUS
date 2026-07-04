"""Testes para Forensic Logging - Merkle Tree e Timestamp."""

import unittest
import hashlib
import json
from datetime import datetime
from src.forensic.merkle_tree import MerkleTree, MerkleProof
from src.forensic.timestamp import TimestampAuthority
from src.forensic.logger import ForensicLogger


class TestMerkleTree(unittest.TestCase):
    """Testes para árvore Merkle."""

    def test_single_leaf(self):
        """Testa árvore com única folha."""
        leaves = [{"id": "evt1", "hash": "abc123"}]
        tree = MerkleTree(leaves)

        self.assertEqual(tree.leaf_count, 1)
        self.assertIsNotNone(tree.root)

    def test_multiple_leaves(self):
        """Testa árvore com múltiplas folhas."""
        leaves = [
            {"id": "evt1", "hash": "abc"},
            {"id": "evt2", "hash": "def"},
            {"id": "evt3", "hash": "ghi"},
            {"id": "evt4", "hash": "jkl"}
        ]
        tree = MerkleTree(leaves)

        self.assertEqual(tree.leaf_count, 4)

    def test_proof_verification(self):
        """Testa geração e verificação de prova Merkle."""
        leaves = [
            {"id": f"evt{i}", "hash": f"hash{i}"}
            for i in range(8)
        ]
        tree = MerkleTree(leaves)

        # Gera prova para primeira folha
        proof = tree.get_proof(0)

        # Verifica prova
        self.assertTrue(tree.verify_proof(proof))

        # Verifica prova para outras folhas
        for i in range(len(leaves)):
            proof = tree.get_proof(i)
            self.assertTrue(tree.verify_proof(proof))

    def test_invalid_proof_tampered(self):
        """Testa que prova adulterada é detectada."""
        leaves = [{"id": "evt1", "hash": "abc"}, {"id": "evt2", "hash": "def"}]
        tree = MerkleTree(leaves)

        proof = tree.get_proof(0)

        # Adultera proof
        proof.leaf_hash = "tampered"

        self.assertFalse(tree.verify_proof(proof))

    def test_consistent_root_hash(self):
        """Testa que mesmas folhas produzem mesma root."""
        leaves = [{"id": f"evt{i}", "hash": f"hash{i}"} for i in range(4)]

        tree1 = MerkleTree(leaves)
        tree2 = MerkleTree(leaves)

        self.assertEqual(tree1.root_hash, tree2.root_hash)


class TestForensicLogger(unittest.TestCase):
    """Testes para Forensic Logger."""

    def setUp(self):
        """Configura teste."""
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.logger = ForensicLogger(
            log_dir=self.temp_dir,
            tsa_enabled=False,  # Desabilita TSA para testes
            batch_size=3  # Batch pequeno para testes
        )

    def test_log_evidence(self):
        """Testa log de evidência individual."""
        evidence = {
            "id": "evt_test_001",
            "timestamp": "2026-07-03T14:00:00Z",
            "camera_id": "CAM-001",
            "alarm_score": 0.95
        }

        result = self.logger.log_evidence(evidence)

        self.assertIn("metadata_hash", result)
        self.assertEqual(result["id"], "evt_test_001")

    def test_batch_flush(self):
        """Testa flush de batch após atingir threshold."""
        for i in range(3):
            self.logger.log_evidence({
                "id": f"evt_test_{i:03d}",
                "timestamp": "2026-07-03T14:00:00Z",
                "camera_id": "CAM-001",
                "alarm_score": 0.90
            })

        # Batch deve ter sido flushado automaticamente
        self.assertEqual(self.logger.total_batches_flushed, 1)

    def test_evidence_chain_verification(self):
        """Testa verificação de cadeia de custódia."""
        # Log de evidências
        evidence = {
            "id": "evt_verify_test",
            "timestamp": "2026-07-03T14:00:00Z",
            "camera_id": "CAM-001",
            "alarm_score": 0.95
        }
        self.logger.log_evidence(evidence)
        batch = self.logger.flush_batch()

        # Verifica cadeia
        result = self.logger.verify_evidence_chain(
            "evt_verify_test",
            batch
        )

        self.assertTrue(result["evidence_found"])


class TestTimestampAuthority(unittest.TestCase):
    """Testes para Timestamp Authority."""

    def test_hash_validation(self):
        """Testa validação de hash."""
        tsa = TimestampAuthority()

        # Hash inválido (curto demais)
        response = tsa.request_timestamp("abc123")
        self.assertEqual(response.status, "rejected")

        # Hash válido (64 caracteres hex)
        valid_hash = "a" * 64
        # Nota: TSA real pode falhar em testes sem rede
        # response = tsa.request_timestamp(valid_hash)
        # self.assertIn(response.status, ["granted", "rejected"])


if __name__ == "__main__":
    unittest.main()