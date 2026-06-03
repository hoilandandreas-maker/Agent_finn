"""Tester for annonsegenerator: prisnormalisering/klamping med mocket kall."""

import pytest

from agent import annonsegenerator


def test_generer_annonse_normaliserer_pris(monkeypatch):
    fake = {
        "tittel": "iPhone 12 64GB",
        "beskrivelse": "Fin telefon.",
        "anbefalt_pris": "3 500 kr",  # streng -> int
        "pris_begrunnelse": "Markedspris",
        "finn_kategori": "Elektronikk",
        "finn_underkategori": "Mobiltelefoner",
    }
    monkeypatch.setattr(
        annonsegenerator.llm_utils, "call_claude_json", lambda **kw: dict(fake)
    )
    pris = {"min_pris": 3000, "max_pris": 5000}

    res = annonsegenerator.generer_annonse({"kategori": "x"}, pris, "selges pga flytting")

    assert res["anbefalt_pris"] == 3500


def test_generer_annonse_klamper_pris(monkeypatch):
    fake = {"tittel": "t", "beskrivelse": "b", "anbefalt_pris": 999999}
    monkeypatch.setattr(
        annonsegenerator.llm_utils, "call_claude_json", lambda **kw: dict(fake)
    )
    pris = {"min_pris": 1000, "max_pris": 2000}

    res = annonsegenerator.generer_annonse({}, pris)

    assert res["anbefalt_pris"] == 3000  # klampet til max * 1.5


def test_generer_annonse_uten_prisdata(monkeypatch):
    fake = {"tittel": "t", "beskrivelse": "b", "anbefalt_pris": 4321}
    monkeypatch.setattr(
        annonsegenerator.llm_utils, "call_claude_json", lambda **kw: dict(fake)
    )

    res = annonsegenerator.generer_annonse({}, {"min_pris": None, "max_pris": None})

    assert res["anbefalt_pris"] == 4321  # ingen klamping uten referansespenn


def test_generer_annonse_mangler_tittel(monkeypatch):
    monkeypatch.setattr(
        annonsegenerator.llm_utils,
        "call_claude_json",
        lambda **kw: {"beskrivelse": "b", "anbefalt_pris": 100},
    )

    with pytest.raises(ValueError):
        annonsegenerator.generer_annonse({}, {})
