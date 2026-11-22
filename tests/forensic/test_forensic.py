"""Testes para Forensic Logging - Merkle Tree e Timestamp."""

import unittest

from src.forensic.logger import ForensicLogger
from src.forensic.merkle_tree import MerkleTree
from src.forensic.timestamp import TimestampAuthority


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
            {"id": "evt4", "hash": "jkl"},
        ]
        tree = MerkleTree(leaves)

        self.assertEqual(tree.leaf_count, 4)

    def test_proof_verification(self):
        """Testa geração e verificação de prova Merkle."""
        leaves = [{"id": f"evt{i}", "hash": f"hash{i}"} for i in range(8)]
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
            batch_size=3,  # Batch pequeno para testes
        )

    def test_log_evidence(self):
        """Testa log de evidência individual."""
        evidence = {
            "id": "evt_test_001",
            "timestamp": "2026-07-03T14:00:00Z",
            "camera_id": "CAM-001",
            "alarm_score": 0.95,
        }

        result = self.logger.log_evidence(evidence)

        self.assertIn("metadata_hash", result)
        self.assertEqual(result["id"], "evt_test_001")

    def test_batch_flush(self):
        """Testa flush de batch após atingir threshold."""
        for i in range(3):
            self.logger.log_evidence(
                {
                    "id": f"evt_test_{i:03d}",
                    "timestamp": "2026-07-03T14:00:00Z",
                    "camera_id": "CAM-001",
                    "alarm_score": 0.90,
                }
            )

        # Batch deve ter sido flushado automaticamente
        self.assertEqual(self.logger.total_batches_flushed, 1)

    def test_evidence_chain_verification(self):
        """Testa verificação de cadeia de custódia."""
        # Log de evidências
        evidence = {
            "id": "evt_verify_test",
            "timestamp": "2026-07-03T14:00:00Z",
            "camera_id": "CAM-001",
            "alarm_score": 0.95,
        }
        self.logger.log_evidence(evidence)
        batch = self.logger.flush_batch()

        # Verifica cadeia
        result = self.logger.verify_evidence_chain("evt_verify_test", batch)

        self.assertTrue(result["evidence_found"])
        # Antes a verificação lançava ValueError (MerkleTree([])); agora valida de fato
        self.assertTrue(result["valid"])

    def test_evidence_chain_rejects_tampered_root(self):
        """Batch com raiz Merkle adulterada não pode ser considerado válido."""
        self.logger.log_evidence(
            {
                "id": "evt_tamper",
                "timestamp": "2026-07-03T14:00:00Z",
                "camera_id": "CAM-001",
                "alarm_score": 0.95,
            }
        )
        batch = dict(self.logger.flush_batch())
        batch["merkle_root"] = "00" * 32
        result = self.logger.verify_evidence_chain("evt_tamper", batch)
        self.assertFalse(result["valid"])


class TestTimestampAuthority(unittest.TestCase):
    """Testes para Timestamp Authority."""

    def test_hash_validation(self):
        """Testa validação de hash."""
        tsa = TimestampAuthority()

        # Hash inválido (curto demais)
        response = tsa.request_timestamp("abc123")
        self.assertEqual(response.status, "rejected")

        # Hash válido (64 caracteres hex) exige rede; não testado aqui
        # response = tsa.request_timestamp(valid_hash)
        # self.assertIn(response.status, ["granted", "rejected"])


if __name__ == "__main__":
    unittest.main()


class TestTimestampOffline(unittest.TestCase):
    """Partes do RFC 3161 que não exigem rede."""

    def setUp(self):
        from src.forensic.timestamp import TimestampAuthority

        self.tsa = TimestampAuthority(tsa_url="https://tsa.invalid/tsr")

    def test_tsq_is_der_sequence_with_hash(self):
        digest = "ab" * 32
        tsq = self.tsa._create_tsq(digest)
        self.assertEqual(tsq[0], 0x30)
        self.assertIn(bytes.fromhex(digest), tsq)

    def test_non_hex_hash_is_rejected_without_network(self):
        self.assertEqual(self.tsa.request_timestamp("z" * 64).status, "rejected")

    def test_der_length_long_form(self):
        self.assertEqual(self.tsa._der_length(5), b"\x05")
        self.assertEqual(self.tsa._der_length(300), b"\x82\x01\x2c")

    def test_malformed_tsr(self):
        self.assertEqual(self.tsa._parse_tsr(b"\x00\x01").status, "rejected")
        self.assertEqual(self.tsa._extract_pki_status(b"\x31\x00")[0], -1)
        self.assertEqual(self.tsa._extract_pki_status(b"\x30\x03\x02\x01\x00")[0], 0)

    def test_verify_rejects_garbage(self):
        self.assertFalse(self.tsa.verify_timestamp("@@não-base64@@", "a" * 64))
        self.assertFalse(self.tsa.verify_timestamp("AAAA", "a" * 64))
