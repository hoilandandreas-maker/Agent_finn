"""Tester for vision: validering/normalisering med mocket Claude-kall.

Bruker et lite syntetisk bilde slik at prepare_image kjører på ekte data.
"""

import pytest
from PIL import Image

from agent import vision


def _lag_bilde(tmp_path):
    sti = tmp_path / "v.jpg"
    Image.new("RGB", (50, 50), (100, 100, 100)).save(sti, format="JPEG")
    return sti


def test_analyser_bilde_normaliserer(tmp_path, monkeypatch):
    fake = {
        "kategori": "Elektronikk",
        "underkategori": "Mobiltelefoner",
        "tilstand_score": "7",       # for høy -> skal klampes til 5
        "slitasje_beskrivelse": "Noen riper",
        "finn_sokord": "iphone 12",  # streng -> skal bli liste
        "estimert_alder": "2 år",
    }
    monkeypatch.setattr(vision.llm_utils, "call_claude_json", lambda **kw: dict(fake))

    res = vision.analyser_bilde(_lag_bilde(tmp_path))

    assert res["tilstand_score"] == 5
    assert res["finn_sokord"] == ["iphone 12"]
    assert res["tilstand_tekst"] == "Ny"          # utledet fra score 5
    assert res["kategori"] == "Elektronikk"


def test_analyser_bilde_score_for_lav(tmp_path, monkeypatch):
    monkeypatch.setattr(
        vision.llm_utils,
        "call_claude_json",
        lambda **kw: {"tilstand_score": 0, "finn_sokord": ["sofa"]},
    )

    res = vision.analyser_bilde(_lag_bilde(tmp_path))

    assert res["tilstand_score"] == 1
    assert res["tilstand_tekst"] == "Brukt"


def test_analyser_bilde_mangler_sokord(tmp_path, monkeypatch):
    monkeypatch.setattr(
        vision.llm_utils, "call_claude_json", lambda **kw: {"finn_sokord": []}
    )

    with pytest.raises(ValueError):
        vision.analyser_bilde(_lag_bilde(tmp_path))
