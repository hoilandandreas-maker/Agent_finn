"""Tester for de rene Markdown-formatterne (uten Gradio)."""

from agent.annonse_format import analyse_markdown, pris_markdown


def test_analyse_markdown():
    md = analyse_markdown(
        {
            "kategori": "Elektronikk",
            "underkategori": "Mobiltelefoner",
            "tilstand_tekst": "Som ny",
            "tilstand_score": 4,
            "slitasje_beskrivelse": "Lite riper",
            "estimert_alder": "2 år",
            "finn_sokord": ["iphone", "12"],
        }
    )
    assert "Elektronikk" in md
    assert "Mobiltelefoner" in md
    assert "4/5" in md
    assert "iphone, 12" in md


def test_pris_markdown_med_data():
    md = pris_markdown(
        {
            "antall_annonser": 3,
            "min_pris": 1000,
            "median_pris": 1500,
            "snitt_pris": 1600,
            "max_pris": 2000,
            "referanse_annonser": [
                {"tittel": "Sofa", "pris": 1500, "url": "https://www.finn.no/x"}
            ],
        }
    )
    assert "3 annonser" in md
    assert "1000 kr" in md
    assert "[Sofa](https://www.finn.no/x)" in md


def test_pris_markdown_uten_url():
    md = pris_markdown(
        {
            "antall_annonser": 1,
            "min_pris": 500,
            "median_pris": 500,
            "snitt_pris": 500,
            "max_pris": 500,
            "referanse_annonser": [{"tittel": "Ting", "pris": 500, "url": ""}],
        }
    )
    assert "Ting - 500 kr" in md


def test_pris_markdown_tom():
    md = pris_markdown({"antall_annonser": 0, "feil": "Kunne ikke hente data fra Finn."})
    assert "Ingen prisreferanser" in md
    assert "Kunne ikke hente data fra Finn." in md
