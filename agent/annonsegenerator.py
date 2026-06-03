"""Annonsegenerering (steg 3).

Kombinerer vision-analyse, prisreferanser og selgerens ekstra info til en ferdig
annonse (tittel, beskrivelse, anbefalt pris m.m.) via Claude. Svaret valideres
og prisen klampes mot referansespennet.
"""

import json
from pathlib import Path

from agent import llm_utils

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "annonse.txt"


def _les_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def generer_annonse(
    vision_data: dict, pris_data: dict, selger_info: str | None = None
) -> dict:
    """Genererer en ferdig annonse som normalisert JSON.

    Returnerer felt: tittel, beskrivelse, anbefalt_pris (int), pris_begrunnelse,
    finn_kategori, finn_underkategori.
    """
    system = _les_prompt()
    kontekst = _bygg_kontekst(vision_data, pris_data, selger_info)
    data = llm_utils.call_claude_json(system=system, user_content=kontekst)
    return _normaliser(data, pris_data)


def _bygg_kontekst(vision_data: dict, pris_data: dict, selger_info: str | None) -> str:
    return (
        "Produktanalyse (JSON):\n"
        f"{json.dumps(vision_data, ensure_ascii=False, indent=2)}\n\n"
        "Prisreferanser fra Finn.no (JSON):\n"
        f"{json.dumps(pris_data, ensure_ascii=False, indent=2)}\n\n"
        f"Ekstra info fra selger: {selger_info or 'Ingen'}"
    )


def _coerce_pris(verdi):
    """Gjør 3500, 3500.0, '3500' eller '3 500 kr' om til int.

    Tall håndteres direkte; strenger reduseres til sifrene (norske priser er
    hele kroner, så tusenskilletegn og 'kr' faller bort). None ved feil.
    """
    if verdi is None or isinstance(verdi, bool):
        return None
    if isinstance(verdi, (int, float)):
        return int(round(verdi))
    siffer = "".join(ch for ch in str(verdi) if ch.isdigit())
    return int(siffer) if siffer else None


def _normaliser(data: dict, pris_data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Annonse-svaret var ikke et JSON-objekt.")

    pris = _coerce_pris(data.get("anbefalt_pris"))

    # Klamp mot referansespennet (med romslig slingringsmonn) når vi har data.
    lav, hoy = pris_data.get("min_pris"), pris_data.get("max_pris")
    if pris is not None and isinstance(lav, int) and isinstance(hoy, int) and lav <= hoy:
        nedre, ovre = int(lav * 0.5), int(hoy * 1.5)
        pris = max(nedre, min(ovre, pris))
    data["anbefalt_pris"] = pris if pris is not None else 0

    if not data.get("tittel"):
        raise ValueError("Annonse-svaret mangler tittel.")
    if not data.get("beskrivelse"):
        raise ValueError("Annonse-svaret mangler beskrivelse.")

    for felt in ("pris_begrunnelse", "finn_kategori", "finn_underkategori"):
        data.setdefault(felt, "")

    return data
