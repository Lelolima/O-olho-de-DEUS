"""Gera vídeos sintéticos de amostra para os exemplos e testes.

São cenas desenhadas (fundo texturizado + ruído de sensor + silhuetas em movimento),
não gravações reais. Servem para exercitar o pipeline de ponta a ponta de forma
reproduzível e sem baixar nada.

Uso:
    python -m src.tools.sample_videos --scene intrusao --out intrusao.avi
    python -m src.tools.sample_videos --scene contagem --out contagem.avi
    python -m src.tools.sample_videos --scene abandono --out abandono.avi
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT, FPS = 320, 240, 10
PERSON_W, PERSON_H = 22, 60


def _background(seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(70, 110, size=(HEIGHT // 8, WIDTH // 8, 3), dtype=np.uint8)
    bg = cv2.resize(base, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST)
    cv2.rectangle(bg, (0, HEIGHT - 40), (WIDTH, HEIGHT), (60, 60, 60), -1)  # piso
    return cv2.GaussianBlur(bg, (3, 3), 0)


def _person(frame: np.ndarray, cx: int, feet_y: int, color: tuple[int, int, int]) -> None:
    x0, y0 = cx - PERSON_W // 2, feet_y - PERSON_H
    cv2.rectangle(frame, (x0, y0 + 14), (x0 + PERSON_W, feet_y), color, -1)  # corpo
    cv2.circle(frame, (cx, y0 + 7), 8, (180, 200, 220), -1)  # cabeça


def _noise(frame: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    noisy = frame.astype(np.int16) + rng.normal(0, 2.0, frame.shape).astype(np.int16)
    return np.clip(noisy, 0, 255).astype(np.uint8)


def scene_intrusion(frames: int = 60) -> list[np.ndarray]:
    """Pessoa entra pela direita e caminha até a metade esquerda (zona restrita)."""
    bg, rng, out = _background(), np.random.default_rng(1), []
    for i in range(frames):
        f = bg.copy()
        if i >= 20:
            cx = WIDTH - 10 - (i - 20) * 7
            _person(f, max(cx, 40), HEIGHT - 45, (40, 40, 160))
        out.append(_noise(f, rng))
    return out


def scene_counting(frames: int = 150) -> list[np.ndarray]:
    """Três pessoas cruzam a linha central da esquerda para a direita e uma volta."""
    walkers = [  # (frame inicial, direção, cor)
        (10, +1, (160, 60, 60)),
        (45, +1, (60, 160, 60)),
        (80, +1, (60, 60, 160)),
        (115, -1, (160, 160, 60)),
    ]
    bg, rng, out = _background(), np.random.default_rng(2), []
    speed = 12
    for i in range(frames):
        f = bg.copy()
        for start, direction, color in walkers:
            t = i - start
            if 0 <= t <= (WIDTH + 40) // speed:
                cx = -20 + t * speed if direction > 0 else WIDTH + 20 - t * speed
                _person(f, cx, HEIGHT - 45, color)
        out.append(_noise(f, rng))
    return out


def scene_abandoned(frames: int = 160) -> list[np.ndarray]:
    """Pessoa entra com uma mala, deixa-a no chão e sai; a mala fica."""
    bg, rng, out = _background(), np.random.default_rng(3), []
    drop_frame, box = 40, (150, HEIGHT - 62, 26, 20)
    for i in range(frames):
        f = bg.copy()
        if i >= drop_frame:
            x, y, w, h = box
            cv2.rectangle(f, (x, y), (x + w, y + h), (30, 120, 200), -1)  # mala deixada
        if 15 <= i < drop_frame:  # chega carregando
            cx = 20 + (i - 15) * 6
            _person(f, cx, HEIGHT - 45, (90, 40, 40))
        elif drop_frame <= i < drop_frame + 30:  # vai embora para a esquerda
            cx = 170 - (i - drop_frame) * 8
            _person(f, cx, HEIGHT - 45, (90, 40, 40))
        out.append(_noise(f, rng))
    return out


SCENES: dict[str, Callable[[], list[np.ndarray]]] = {
    "intrusao": scene_intrusion,
    "contagem": scene_counting,
    "abandono": scene_abandoned,
}


def write_video(frames: list[np.ndarray], path: str | Path, fps: int = FPS) -> Path:
    """Grava em MJPG/AVI (disponível em qualquer build do OpenCV)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter.fourcc(*"MJPG"), fps, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise OSError(f"Não foi possível gravar {out}")
    for frame in frames:
        writer.write(frame)
    writer.release()
    return out


def make_scene(scene: str, path: str | Path) -> Path:
    if scene not in SCENES:
        raise ValueError(f"Cena desconhecida: {scene} (opções: {', '.join(SCENES)})")
    return write_video(SCENES[scene](), path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera vídeo sintético de amostra")
    parser.add_argument("--scene", choices=sorted(SCENES), required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    path = make_scene(args.scene, args.out)
    print(f"Vídeo gerado: {path} ({WIDTH}x{HEIGHT}, {FPS} fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
