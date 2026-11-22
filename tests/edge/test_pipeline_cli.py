"""Fluxo ponta a ponta do modo edge com vídeo sintético gravado em disco."""

import json
import os
from pathlib import Path

import cv2
import numpy as np
import pytest

import main as cli
from src.edge.sources import VideoSourceError, parse_source, redact_url
from src.edge.streamer import RTSPStreamer


def write_video(path: Path, frames: int = 12, size=(160, 120), fps: int = 10) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
    assert writer.isOpened()
    for i in range(frames):
        frame = np.full((size[1], size[0], 3), 40, dtype=np.uint8)
        cv2.rectangle(frame, (5 + i * 5, 30), (35 + i * 5, 90), (220, 220, 220), -1)
        writer.write(frame)
    writer.release()
    return path


class TestSources:
    def test_webcam_index_becomes_int(self):
        assert parse_source("0") == 0
        assert parse_source(2) == 2

    def test_stream_urls_pass_through(self):
        assert parse_source("rtsp://cam.example.com/s") == "rtsp://cam.example.com/s"

    def test_missing_file_is_clear_error(self, tmp_path):
        with pytest.raises(VideoSourceError, match="não encontrado"):
            parse_source(str(tmp_path / "nao_existe.mp4"))

    def test_unsupported_scheme(self):
        with pytest.raises(VideoSourceError, match="Esquema"):
            parse_source("ftp://host/video")

    def test_file_uri(self, tmp_path):
        video = write_video(tmp_path / "v.avi")
        assert Path(parse_source(video.resolve().as_uri())).resolve() == video.resolve()

    def test_redact_credentials(self):
        assert redact_url("rtsp://user:segredo@10.0.0.2:554/s") == "rtsp://***@10.0.0.2:554/s"
        assert "segredo" not in redact_url("rtsp://user:segredo@cam/s")


class TestStreamer:
    def test_streamer_accepts_video_file_and_finishes(self, tmp_path):
        video = write_video(tmp_path / "v.avi", frames=5)
        streamer = RTSPStreamer(str(video), buffer_size=50, frame_timeout=5.0)
        streamer.start()
        assert streamer.finished.wait(timeout=10)
        read = 0
        while streamer.read_frame(timeout=0) is not None:
            read += 1
        streamer.stop()
        assert read == 5

    def test_streamer_rejects_garbage(self):
        with pytest.raises(ValueError):
            RTSPStreamer("isto-nao-e-uma-fonte")


class TestConfig:
    def test_expand_env_placeholders(self, monkeypatch):
        monkeypatch.setenv("CAM_URL", "rtsp://x/y")
        monkeypatch.delenv("NAO_DEFINIDA", raising=False)
        data = cli.expand_env({"a": "${CAM_URL}", "b": ["${NAO_DEFINIDA:padrao}"], "c": 1})
        assert data == {"a": "rtsp://x/y", "b": ["padrao"], "c": 1}

    def test_yaml_config_example_loads(self):
        cfg = cli.load_config(str(Path(cli.__file__).parent / "config.yaml.example"))
        assert cfg["edge"]["backend"] == "haar"
        assert "${" not in json.dumps(cfg)

    def test_missing_config_uses_defaults(self, tmp_path):
        cfg = cli.load_config(str(tmp_path / "nao_existe.yaml"))
        assert cfg["cameras"] == []


class TestEdgeModeCli:
    def test_no_cameras_returns_2(self, tmp_path):
        assert cli.main(["--mode", "edge", "--config", str(tmp_path / "x.yaml")]) == 2

    def test_edge_mode_processes_video_file(self, tmp_path, capsys):
        video = write_video(tmp_path / "v.avi", frames=12)
        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps({
            "edge": {"backend": "haar"},
            "forensic": {"log_dir": str(tmp_path / "logs"), "tsa_enabled": False, "batch_size": 10},
        }), encoding="utf-8")
        code = cli.main(["--mode", "edge", "--config", str(cfg), "--source", str(video)])
        assert code == 0
        out = capsys.readouterr().out
        summary = json.loads(out[out.index("{"):])
        assert summary["CLI"]["frames_processed"] == 12

    def test_edge_mode_bad_source_fails_cleanly(self, tmp_path):
        cfg = tmp_path / "cfg.json"
        cfg.write_text(json.dumps({"forensic": {"log_dir": str(tmp_path / "l"), "tsa_enabled": False}}))
        assert cli.main(["--mode", "edge", "--config", str(cfg), "--source", str(tmp_path / "nada.mp4")]) == 1


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("USE_SQLITE", os.environ.get("USE_SQLITE", "true"))
