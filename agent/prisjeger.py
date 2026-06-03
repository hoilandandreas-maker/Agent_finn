"""Prisreferanser fra Finn.no (steg 2).

Foretrekker å lese annonser fra den innebygde ``__NEXT_DATA__``-JSON-blokken
(stabil) og faller tilbake til CSS-selektorer hvis den mangler. Nettverkskall
har retry og høflig forsinkelse. Parse-/statistikkfunksjonene er rene og
testes mot lagrede fixturer uten nettverk.
"""

import json
import statistics
import time
import urllib.parse

from bs4 import BeautifulSoup

from agent import config


def bygg_sok_url(sokord: list[str]) -> str:
    """Bygger Finn-søke-URL fra søkeord."""
    query = " ".join(s for s in sokord if s).strip()
    params = urllib.parse.urlencode({"q": query})
    return f"{config.FINN_SEARCH_URL}?{params}"


def hent_prisstatistikk(sokord: list[str], maks_annonser: int | None = None) -> dict:
    """Henter og beregner prisreferanser fra Finn for de gitte søkeordene."""
    url = bygg_sok_url(sokord)
    html = _hent_html(url)
    if html is None:
        stats = beregn_statistikk([], maks_annonser)
        stats["feil"] = "Kunne ikke hente data fra Finn."
        return stats

    annonser = parse_next_data(html)
    if not annonser:
        annonser = parse_css_fallback(html)
    return beregn_statistikk(annonser, maks_annonser)


def _hent_html(url: str) -> str | None:
    """Henter HTML med retry og høflig forsinkelse. Importerer httpx lazy."""
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pakken 'httpx' er ikke installert.") from exc

    headers = {"User-Agent": config.USER_AGENT, "Accept-Language": "nb-NO,nb;q=0.9"}
    for forsok in range(config.HTTP_RETRIES):
        try:
            resp = httpx.get(
                url,
                headers=headers,
                timeout=config.HTTP_TIMEOUT,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.text
        except httpx.HTTPError:
            pass
        if forsok < config.HTTP_RETRIES - 1:
            time.sleep(config.POLITE_DELAY_SECONDS)
    return None


def parse_next_data(html: str) -> list[dict]:
    """Henter annonser fra ``__NEXT_DATA__``-JSON-blokken hvis den finnes."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []
    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return []

    samlet: list[dict] = []
    _samle_annonser(data, samlet)

    # Fjern duplikater (samme annonse kan dukke opp flere steder i treet).
    sett = set()
    unike = []
    for a in samlet:
        nøkkel = (a["tittel"], a["pris"], a["url"])
        if nøkkel not in sett:
            sett.add(nøkkel)
            unike.append(a)
    return unike


def _samle_annonser(node, ut: list[dict]) -> None:
    """Går rekursivt gjennom JSON og plukker objekter som ser ut som annonser."""
    if isinstance(node, dict):
        pris = _finn_pris(node)
        tittel = node.get("heading") or node.get("title")
        if pris is not None and tittel:
            ut.append({"tittel": str(tittel), "pris": pris, "url": _finn_url(node)})
        for verdi in node.values():
            _samle_annonser(verdi, ut)
    elif isinstance(node, list):
        for verdi in node:
            _samle_annonser(verdi, ut)


def _finn_pris(node: dict):
    """Forsøker å hente et prisbeløp fra et annonse-objekt."""
    price = node.get("price")
    if isinstance(price, dict):
        for key in ("amount", "value", "total"):
            if isinstance(price.get(key), (int, float)):
                return int(price[key])
    elif isinstance(price, (int, float)):
        return int(price)
    return None


def _finn_url(node: dict) -> str:
    for key in ("canonical_url", "url", "link"):
        val = node.get(key)
        if isinstance(val, str) and val:
            return val if val.startswith("http") else f"https://www.finn.no{val}"
    return ""


def parse_css_fallback(html: str) -> list[dict]:
    """Fallback: plukker annonser via CSS-selektorer."""
    soup = BeautifulSoup(html, "html.parser")
    annonser = []
    kort = soup.select("[data-testid='ads'] article") or soup.select("article")
    for k in kort:
        pris_el = k.select_one("[class*='price'], [class*='Price']")
        if not pris_el:
            continue
        pris = _tall_fra_tekst(pris_el.get_text())
        if pris is None:
            continue
        tittel_el = k.select_one("h2, h3")
        lenke_el = k.select_one("a[href]")
        url = ""
        if lenke_el and lenke_el.get("href"):
            href = lenke_el["href"]
            url = href if href.startswith("http") else f"https://www.finn.no{href}"
        annonser.append(
            {
                "tittel": tittel_el.get_text(strip=True) if tittel_el else "",
                "pris": pris,
                "url": url,
            }
        )
    return annonser


def _tall_fra_tekst(tekst: str):
    """Ekstraherer et heltall fra f.eks. '1 500 kr'."""
    siffer = "".join(ch for ch in tekst if ch.isdigit())
    return int(siffer) if siffer else None


def beregn_statistikk(annonser: list[dict], maks_annonser: int | None = None) -> dict:
    """Regner ut prisstatistikk fra en liste annonser.

    Ignorerer manglende/0-priser. Returnerer None-felt og antall 0 dersom det
    ikke finnes gyldige priser, slik at pipelinen ikke krasjer.
    """
    if maks_annonser is None:
        maks_annonser = config.MAX_REFERENCE_LISTINGS

    gyldige = [
        a for a in annonser if isinstance(a.get("pris"), int) and a["pris"] > 0
    ]
    priser = [a["pris"] for a in gyldige]

    if not priser:
        return {
            "min_pris": None,
            "max_pris": None,
            "snitt_pris": None,
            "median_pris": None,
            "antall_annonser": 0,
            "referanse_annonser": [],
        }

    return {
        "min_pris": min(priser),
        "max_pris": max(priser),
        "snitt_pris": int(round(statistics.mean(priser))),
        "median_pris": int(statistics.median(priser)),
        "antall_annonser": len(priser),
        "referanse_annonser": gyldige[:maks_annonser],
    }
