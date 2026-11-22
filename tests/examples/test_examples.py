"""Executa cada exemplo de examples/ (cenas sintéticas) e confere a saída esperada."""

import importlib.util
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def load(name: str):
    path = EXAMPLES / name / "run.py"
    spec = importlib.util.spec_from_file_location(f"exemplo_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("USE_SQLITE", "true")


def test_01_intrusao_alerta_somente_fora_do_horario(tmp_path, capsys):
    ex = load("01_intrusao_fora_do_horario")
    noite = ex.main(["--saida", str(tmp_path / "noite"), "--inicio", "2026-11-22T22:30:00"])
    assert noite["events_by_type"] == {"zone_intrusion": 1}
    assert noite["alertas"][0]["details"]["zone"] == "patio_fundos"
    assert list((tmp_path / "noite" / "snapshots").glob("*_zone_intrusion.jpg"))
    assert list((tmp_path / "noite" / "forense" / "archives").glob("*.json"))  # batch Merkle gravado

    dia = ex.main(["--saida", str(tmp_path / "dia"), "--inicio", "2026-11-22T10:00:00", "--sem-snapshots"])
    assert dia["zona_ativa_no_horario"] is False
    assert dia["events"] == 0


def test_02_contagem_entradas_saidas_e_lotacao(tmp_path):
    ex = load("02_contagem_de_pessoas")
    r = ex.main(["--saida", str(tmp_path), "--sem-snapshots"])
    assert (r["entradas"], r["saidas"], r["ocupacao_final"]) == (3, 1, 2)
    assert r["events_by_type"] == {"line_crossing": 4, "occupancy_exceeded": 1}


def test_02_contagem_com_detector_hog_executa(tmp_path):
    """HOG real do OpenCV; a cena sintética não tem pessoas reais, então não conta ninguém."""
    ex = load("02_contagem_de_pessoas")
    r = ex.main(["--saida", str(tmp_path), "--sem-snapshots", "--detector", "hog"])
    assert r["detector"] == "hog" and r["frames_processed"] == 150


def test_03_objeto_abandonado(tmp_path):
    ex = load("03_objeto_abandonado")
    r = ex.main(["--saida", str(tmp_path)])
    assert r["events_by_type"] == {"abandoned_object": 1}
    x, y, w, h = r["alertas"][0]["details"]["box"]
    # mala desenhada em (150, 178, 26, 20)
    assert abs(x - 150) <= 3 and abs(y - 178) <= 3 and abs(w - 26) <= 4 and abs(h - 20) <= 4


def test_04_fluxo_hitl_completo(tmp_path):
    ex = load("04_fluxo_hitl_completo")
    r = ex.main(["--saida", str(tmp_path)])
    assert r["status_inicial_alerta"] == "pending"
    assert r["decisao_operador"] == "escalate"
    assert r["operador_registrado"] == "operador.demo"
    assert r["status_final_alerta"] == "escalated"
    assert r["evidencia_integra"] is True
    assert r["cadeia_merkle_valida"] is True
