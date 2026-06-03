"""Tester for prisjeger: parsing av __NEXT_DATA__/CSS og statistikk (fixturer)."""

from pathlib import Path

from agent import prisjeger

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _les(navn: str) -> str:
    return (FIXTURES / navn).read_text(encoding="utf-8")


def test_parse_next_data():
    annonser = prisjeger.parse_next_data(_les("finn_next_data.html"))
    priser = sorted(a["pris"] for a in annonser)
    assert priser == [3500, 4200, 5000]
    assert all(a["tittel"] for a in annonser)
    assert any(a["url"].startswith("https://www.finn.no") for a in annonser)


def test_parse_next_data_uten_blokk():
    assert prisjeger.parse_next_data("<html><body>tomt</body></html>") == []


def test_parse_css_fallback():
    annonser = prisjeger.parse_css_fallback(_les("finn_css_fallback.html"))
    priser = sorted(a["pris"] for a in annonser)
    assert priser == [1500, 2000]  # annonsen uten pris hoppes over


def test_beregn_statistikk():
    annonser = [
        {"tittel": "a", "pris": 1000, "url": ""},
        {"tittel": "b", "pris": 2000, "url": ""},
        {"tittel": "c", "pris": 3000, "url": ""},
    ]
    stats = prisjeger.beregn_statistikk(annonser)
    assert stats["min_pris"] == 1000
    assert stats["max_pris"] == 3000
    assert stats["snitt_pris"] == 2000
    assert stats["median_pris"] == 2000
    assert stats["antall_annonser"] == 3
    assert len(stats["referanse_annonser"]) == 3


def test_beregn_statistikk_tom():
    stats = prisjeger.beregn_statistikk([{"tittel": "a", "pris": None, "url": ""}])
    assert stats["antall_annonser"] == 0
    assert stats["min_pris"] is None
    assert stats["referanse_annonser"] == []


def test_beregn_statistikk_maks():
    annonser = [{"tittel": str(i), "pris": 100 * (i + 1), "url": ""} for i in range(20)]
    stats = prisjeger.beregn_statistikk(annonser, maks_annonser=5)
    assert len(stats["referanse_annonser"]) == 5
    assert stats["antall_annonser"] == 20


def test_bygg_sok_url():
    url = prisjeger.bygg_sok_url(["iphone", "12"])
    assert url.startswith(prisjeger.config.FINN_SEARCH_URL)
    assert "q=iphone+12" in url
