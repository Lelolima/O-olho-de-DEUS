"""
Merkle Tree para cadeia de custódia imutável.

Implementação de árvore Merkle para garantir integridade de evidências.
Cada folha contém o hash de uma evidência, e a raiz prova que todas
as evidências existiram naquele estado específico.

Baseado em: RFC 6962 (Certificate Transparency)
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class MerkleNode:
    """Nó da árvore Merkle."""

    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    data: Optional[dict] = None  # Apenas em folhas (leaf nodes)
    index: Optional[int] = None  # Índice da folha (apenas para leaves)


@dataclass
class MerkleProof:
    """
    Prova de inclusão Merkle.

    Permite verificar que uma evidência específica pertence
    à árvore sem precisar de toda a árvore.
    """

    leaf_hash: str  # Hash da folha sendo provada
    root_hash: str  # Hash da raiz da árvore
    proof_path: List[Tuple[str, str]] = field(default_factory=list)
    # Cada tupla: (hash_do_sibling, posicao) onde posicao é 'left' ou 'right'
    timestamp: datetime = field(default_factory=datetime.now)
    leaf_index: int = 0  # Índice da folha na árvore original

    def to_dict(self) -> dict:
        """Serializa prova para dict JSON-serializable."""
        return {
            "leaf_hash": self.leaf_hash,
            "root_hash": self.root_hash,
            "proof_path": self.proof_path,
            "timestamp": self.timestamp.isoformat(),
            "leaf_index": self.leaf_index
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MerkleProof':
        """Deserializa prova de dict."""
        return cls(
            leaf_hash=data["leaf_hash"],
            root_hash=data["root_hash"],
            proof_path=[tuple(p) for p in data["proof_path"]],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            leaf_index=data.get("leaf_index", 0)
        )


class MerkleTree:
    """
    Árvore Merkle para cadeia de custódia imutável.

    Uso:
        leaves = [{"id": "evt1", "hash": "abc"}, {"id": "evt2", "hash": "def"}]
        tree = MerkleTree(leaves)
        root = tree.root.hash
        proof = tree.get_proof(0)  # Prova para primeira folha
        assert tree.verify_proof(proof)  # True
    """

    # Prefixos para diferenciar folhas de nós internos (previne ataques de segunda pre-imagem)
    LEAF_PREFIX = b'\x00'
    NODE_PREFIX = b'\x01'

    def __init__(self, leaves: List[dict]):
        """
        Constrói árvore Merkle a partir de uma lista de evidências.

        Args:
            leaves: Lista de dicts com dados das evidências.
                   Cada dict deve ter pelo menos um campo identificável.
        """
        if not leaves:
            raise ValueError("MerkleTree requer pelo menos uma folha")

        self.original_leaves = leaves
        self.leaf_hashes: List[str] = []
        self.leaf_nodes: List[MerkleNode] = []
        self.root: Optional[MerkleNode] = None

        # Constrói a árvore
        self._build()

    def _hash_leaf(self, data: dict) -> str:
        """
        Calcula hash SHA-256 de uma folha.

        Usa prefixo 0x00 para distinguir folhas de nós internos.
        """
        # Canonicaliza JSON (sorted keys para consistência)
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        payload = self.LEAF_PREFIX + canonical.encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    def _hash_nodes(self, left_hash: str, right_hash: str) -> str:
        """
        Calcula hash combinando dois nós.

        Usa prefixo 0x01 para distinguir de folhas.
        """
        left_bytes = bytes.fromhex(left_hash)
        right_bytes = bytes.fromhex(right_hash)
        payload = self.NODE_PREFIX + left_bytes + right_bytes
        return hashlib.sha256(payload).hexdigest()

    def _build(self):
        """Constrói a árvore Merkle recursivamente."""
        # Step 1: Cria leaf nodes
        for i, leaf_data in enumerate(self.original_leaves):
            leaf_hash = self._hash_leaf(leaf_data)
            self.leaf_hashes.append(leaf_hash)
            node = MerkleNode(hash=leaf_hash, data=leaf_data, index=i)
            self.leaf_nodes.append(node)

        # Step 2: Constrói árvore bottom-up
        self.root = self._build_level(self.leaf_nodes)

    def _build_level(self, nodes: List[MerkleNode]) -> MerkleNode:
        """
        Constrói um nível da árvore.

        Se número ímpar de nós, duplica o último.
        """
        if len(nodes) == 1:
            return nodes[0]

        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            # Se ímpar, duplica último nó
            right = nodes[i + 1] if i + 1 < len(nodes) else left

            combined_hash = self._hash_nodes(left.hash, right.hash)
            parent = MerkleNode(hash=combined_hash, left=left, right=right)
            next_level.append(parent)

        return self._build_level(next_level)

    def get_proof(self, leaf_index: int) -> MerkleProof:
        """
        Gera prova de inclusão para uma folha específica.

        A prova permite verificar que a folha está na árvore
        sem revelar as outras folhas.

        Args:
            leaf_index: Índice da folha (0-based)

        Returns:
            MerkleProof com caminho de prova
        """
        if leaf_index < 0 or leaf_index >= len(self.leaf_nodes):
            raise ValueError(f"Índice {leaf_index} fora de range [0, {len(self.leaf_nodes)-1}]")

        proof_path = []
        current_index = leaf_index

        # Percorre da folha até a raiz
        nodes = self.leaf_nodes.copy()
        while len(nodes) > 1:
            # Determina sibling
            if current_index % 2 == 0:
                # Nó esquerdo: sibling é à direita
                sibling_index = current_index + 1
                position = 'right'
            else:
                # Nó direito: sibling é à esquerda
                sibling_index = current_index - 1
                position = 'left'

            # Pega sibling (ou duplica se não existir)
            if sibling_index < len(nodes):
                sibling_hash = nodes[sibling_index].hash
            else:
                # Ímpar: último nó não tem sibling
                sibling_hash = nodes[current_index].hash

            proof_path.append((sibling_hash, position))

            # Sobe um nível
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                next_level.append(MerkleNode(
                    hash=self._hash_nodes(left.hash, right.hash),
                    left=left,
                    right=right
                ))

            nodes = next_level
            current_index = current_index // 2

        return MerkleProof(
            leaf_hash=self.leaf_hashes[leaf_index],
            root_hash=self.root.hash if self.root else "",
            proof_path=proof_path,
            timestamp=datetime.now(),
            leaf_index=leaf_index
        )

    def verify_proof(self, proof: MerkleProof) -> bool:
        """
        Verifica se uma prova de inclusão é válida.

        Args:
            proof: Prova Merkle a ser verificada

        Returns:
            True se a prova é válida, False caso contrário
        """
        current_hash = bytes.fromhex(proof.leaf_hash)

        for sibling_hash, position in proof.proof_path:
            sibling = bytes.fromhex(sibling_hash)
            if position == 'left':
                # Sibling está à esquerda
                current_hash = hashlib.sha256(
                    self.NODE_PREFIX + sibling + current_hash
                ).digest()
            else:
                # Sibling está à direita
                current_hash = hashlib.sha256(
                    self.NODE_PREFIX + current_hash + sibling
                ).digest()

        return current_hash.hex() == proof.root_hash

    def get_leaf_data(self, leaf_index: int) -> Optional[dict]:
        """Retorna dados originais de uma folha pelo índice."""
        if 0 <= leaf_index < len(self.original_leaves):
            return self.original_leaves[leaf_index]
        return None

    @property
    def leaf_count(self) -> int:
        """Número de folhas na árvore."""
        return len(self.original_leaves)

    @property
    def root_hash(self) -> str:
        """Hash da raiz da árvore."""
        return self.root.hash if self.root else ""

    def to_dict(self) -> dict:
        """Serializa árvore para dict (apenas metadados, não a árvore completa)."""
        return {
            "root_hash": self.root_hash,
            "leaf_count": self.leaf_count,
            "leaf_hashes": self.leaf_hashes,
            "timestamp": datetime.now().isoformat()
        }