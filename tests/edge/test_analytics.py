"""Testes unitários dos analisadores de vídeo (frames sintéticos em memória)."""

import json
from datetime import datetime, timedelta

import numpy as np
import pytest

import main as cli
from src.edge.analytics import (
    AbandonedObjectDetector,
    HogPersonDetector,
    PeopleCounter,
    Schedule,
    ZoneIntrusionDetector,
    build_analyzers,
)
from src.edge.pipeline import VideoPipeline
from src.tools.sample_videos import make_scene, scene_abandoned, scene_counting, scene_intrusion

T0 = datetime(2026, 11, 22, 22, 0)


class TestSchedule:
    def test_window_crossing_midnight(self):
        s = Schedule.from_config([("19:00", "07:00")])
        assert s.is_active(datetime(2026, 1, 1, 23, 0))
        assert s.is_active(datetime(2026, 1, 1, 6, 59))
        assert not s.is_active(datetime(2026, 1, 1, 7, 0))
        assert not s.is_active(datetime(2026, 1, 1, 12, 0))

    def test_same_day_window_and_empty(self):
        s = Schedule.from_config([("08:00", "18:00")])
        assert s.is_active(datetime(2026, 1, 1, 8, 0)) and not s.is_active(datetime(2026, 1, 1, 18, 0))
        assert Schedule().is_active(datetime(2026, 1, 1, 3, 0))


def run(analyzer, frames, start=T0):
    return VideoPipeline("T", analyzers=[analyzer]).run_frames(frames, fps=10, start_time=start)


class TestZoneIntrusion:
    ZONE = ((0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0))

    def test_alert_inside_zone_with_cooldown(self):
        det = ZoneIntrusionDetector(self.ZONE, cooldown_seconds=999)
        summary = run(det, scene_intrusion())
        assert summary.events_by_type == {"zone_intrusion": 1}

    def test_motion_outside_zone_is_ignored(self):
        right_half = [(0.95, 0.0), (1.0, 0.0), (1.0, 0.05), (0.95, 0.05)]  # canto sem movimento
        assert run(ZoneIntrusionDetector(right_half), scene_intrusion()).events == []

    def test_cooldown_allows_repeated_alerts_after_interval(self):
        det = ZoneIntrusionDetector(self.ZONE, cooldown_seconds=0.5)
        assert len(run(det, scene_intrusion()).events) > 1

    def test_invalid_zone(self):
        with pytest.raises(ValueError):
            ZoneIntrusionDetector([(0, 0), (1, 1)])


class TestPeopleCounter:
    def test_counts_and_occupancy(self):
        pc = PeopleCounter(((0.5, 0.0), (0.5, 1.0)), max_occupancy=2)
        summary = run(pc, scene_counting())
        assert (pc.entries, pc.exits, pc.occupancy) == (3, 1, 2)
        assert summary.events_by_type["occupancy_exceeded"] == 1

    def test_reversed_line_swaps_direction(self):
        pc = PeopleCounter(((0.5, 1.0), (0.5, 0.0)))
        run(pc, scene_counting())
        assert (pc.entries, pc.exits) == (1, 3)

    def test_unknown_detector(self):
        with pytest.raises(ValueError):
            PeopleCounter(((0, 0), (1, 1)), detector="yolo")


class TestAbandonedObject:
    def test_detects_left_object_once(self):
        summary = run(AbandonedObjectDetector(min_static_seconds=5), scene_abandoned())
        assert summary.events_by_type == {"abandoned_object": 1}

    def test_threshold_longer_than_video_gives_no_alert(self):
        assert run(AbandonedObjectDetector(min_static_seconds=60), scene_abandoned()).events == []


def test_hog_detector_runs_and_validates():
    det = HogPersonDetector(resize=1.0)
    assert det.detect(np.zeros((240, 320, 3), dtype=np.uint8)) == []
    with pytest.raises(ValueError):
        HogPersonDetector(resize=0)


def test_build_analyzers_from_config():
    analyzers = build_analyzers(
        {
            "zone_intrusion": {"zone": [[0, 0], [0.5, 0], [0.5, 1]], "active_hours": [["19:00", "07:00"]]},
            "people_counter": {"line": [[0.5, 0], [0.5, 1]], "max_occupancy": 3},
            "abandoned_object": {"min_static_seconds": 10},
        }
    )
    assert [a.name for a in analyzers] == ["zone_intrusion", "people_counter", "abandoned_object"]
    assert build_analyzers(None) == [] and build_analyzers({}) == []


def test_edge_cli_with_analytics_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    video = make_scene("intrusao", tmp_path / "cena.avi")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
                "edge": {"backend": "haar", "face_detection": False},
                "forensic": {"log_dir": str(tmp_path / "f"), "tsa_enabled": False},
                "analytics": {"zone_intrusion": {"zone": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]]}},
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["--mode", "edge", "-c", str(cfg), "-s", str(video)]) == 0
    out = capsys.readouterr().out
    summary = json.loads(out[out.index("{") :])
    assert summary["CLI"]["events_by_type"] == {"zone_intrusion": 1}


def test_event_timestamps_follow_video_fps():
    pc = PeopleCounter(((0.5, 0.0), (0.5, 1.0)))
    summary = run(pc, scene_counting(), start=datetime(2026, 1, 1, 9, 0))
    first = summary.events[0]
    assert first.timestamp == datetime(2026, 1, 1, 9, 0) + timedelta(seconds=first.frame_index / 10)
