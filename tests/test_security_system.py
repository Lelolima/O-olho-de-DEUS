#!/usr/bin/env python3
"""
Testes unitários para O-olho-de-DEUS
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from security_system import ConfigManager, SecureDataHandler, AISecuritySystem


class TestConfigManager(unittest.TestCase):
    """Testes para ConfigManager"""

    def test_default_config(self):
        """Config padrão deve ter valores esperados"""
        config_manager = ConfigManager('config_inexistente.json')
        config = config_manager.config

        self.assertEqual(config['security_level'], 'medium')
        self.assertEqual(config['log_level'], 'INFO')
        self.assertEqual(config['confidence_threshold'], 0.7)
        self.assertEqual(config['incident_retention_days'], 30)
        self.assertIsInstance(config['video_sources'], list)

    def test_load_existing_config(self):
        """Carregar config existente"""
        # Criar config temporário
        test_config = {
            "security_level": "high",
            "log_level": "DEBUG",
            "video_sources": ["0", "1"]
        }
        config_path = Path('test_config_temp.json')
        with open(config_path, 'w') as f:
            json.dump(test_config, f)

        config_manager = ConfigManager(str(config_path))
        self.assertEqual(config_manager.config['security_level'], 'high')
        self.assertEqual(len(config_manager.config['video_sources']), 2)

        # Cleanup
        config_path.unlink()


class TestSecureDataHandler(unittest.TestCase):
    """Testes para SecureDataHandler"""

    def test_hash_is_consistent(self):
        """Hash deve ser consistente para mesma entrada"""
        data = "test_face_data"
        hash1 = SecureDataHandler.hash_sensitive_data(data)
        hash2 = SecureDataHandler.hash_sensitive_data(data)
        self.assertEqual(hash1, hash2)

    def test_hash_is_different_for_different_data(self):
        """Hashes diferentes para dados diferentes"""
        hash1 = SecureDataHandler.hash_sensitive_data("data1")
        hash2 = SecureDataHandler.hash_sensitive_data("data2")
        self.assertNotEqual(hash1, hash2)

    def test_hash_uses_salt(self):
        """Salt deve tornar hash diferente do hash simples"""
        import hashlib
        data = "sensitive_data"
        hashed = SecureDataHandler.hash_sensitive_data(data)
        simple_hash = hashlib.sha256(data.encode()).hexdigest()
        self.assertNotEqual(hashed, simple_hash)

    def test_anonymize_face_data(self):
        """Anonimização deve retornar estrutura esperada"""
        face_data = {"x": 100, "y": 200, "w": 50, "h": 50}
        anonymized = SecureDataHandler.anonymize_face_data(face_data)

        self.assertIn('face_hash', anonymized)
        self.assertIn('timestamp', anonymized)
        self.assertIsInstance(anonymized['face_hash'], str)
        self.assertEqual(len(anonymized['face_hash']), 64)  # SHA256 hex


class TestAISecuritySystem(unittest.TestCase):
    """Testes para AISecuritySystem"""

    def setUp(self):
        """Setup para cada teste"""
        self.config_manager = ConfigManager('config_test.json')
        with patch('cv2.CascadeClassifier'):
            self.system = AISecuritySystem(self.config_manager)

    def test_validate_video_source_webcam(self):
        """Validar webcam (número)"""
        self.assertTrue(self.system._validate_video_source("0"))
        self.assertTrue(self.system._validate_video_source("1"))

    def test_validate_video_source_local_file(self):
        """Validar arquivo local"""
        # Criar arquivo temporário
        test_file = Path('test_video_temp.mp4')
        test_file.touch()
        self.assertTrue(self.system._validate_video_source(str(test_file)))
        test_file.unlink()

    def test_validate_video_source_localhost(self):
        """Validar localhost"""
        self.assertTrue(self.system._validate_video_source("http://localhost/stream"))
        self.assertTrue(self.system._validate_video_source("http://127.0.0.1:8080/stream"))

    def test_detect_faces_empty_if_no_model(self):
        """Detecção deve retornar lista vazia se sem modelo"""
        import numpy as np
        self.system.face_detection_model = None
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        faces = self.system._detect_faces(frame)
        self.assertEqual(faces, [])

    def test_is_suspicious_behavior_many_faces(self):
        """Comportamento suspeito com muitas pessoas"""
        import numpy as np
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        faces = [(i, i, 50, 50) for i in range(15)]  # 15 rostos
        self.assertTrue(self.system._is_suspicious_behavior(frame, faces))

    def test_is_suspicious_behavior_few_faces(self):
        """Sem comportamento suspeito com poucos rostos"""
        import numpy as np
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        faces = [(10, 10, 50, 50)]  # 1 rosto
        self.assertFalse(self.system._is_suspicious_behavior(frame, faces))


class TestIntegration(unittest.TestCase):
    """Testes de integração"""

    def test_config_and_system_compatibility(self):
        """Config e sistema devem ser compatíveis"""
        config_manager = ConfigManager('config_integration.json')
        with patch('cv2.CascadeClassifier'):
            system = AISecuritySystem(config_manager)

        # Verificar que directories foram criadas
        self.assertTrue(Path('incidents').exists())
        self.assertTrue(Path('logs').exists())
        self.assertTrue((Path('incidents') / 'images').exists())
        self.assertTrue((Path('logs') / 'security_system.log').exists())


if __name__ == '__main__':
    print("=" * 60)
    print("Executando testes do O-olho-de-DEUS")
    print("=" * 60)

    unittest.main(verbosity=2)