"""Bildeanalyse (steg 1).

Tar et produktbilde og returnerer strukturert JSON med kategori, tilstand og
søkeord via Claude vision. Svaret valideres og normaliseres slik at
nedstrøms-stegene kan stole på formatet.
"""

from pathlib import Path

from agent import image_utils, llm_utils

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "tilstand.txt"

_PAAKREVDE_FELT = (
    "kategori",
    "underkategori",
    "tilstand_score",
    "tilstand_tekst",
    "slitasje_beskrivelse",
    "finn_sokord",
    "estimert_alder",
)

_TILSTAND_TEKST = {
    1: "Brukt",
    2: "God stand",
    3: "Veldig god stand",
    4: "Som ny",
    5: "Ny",
}


def _les_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def analyser_bilde(bilde_sti, ekstra_kontekst: str | None = None) -> dict:
    """Analyserer et produktbilde og returnerer normalisert tilstands-/kategori-JSON.

    Returnerer felt: kategori, underkategori, tilstand_score (int 1-5),
    tilstand_tekst, slitasje_beskrivelse, finn_sokord (list[str]), estimert_alder.
    """
    base64_data, media_type = image_utils.prepare_image(bilde_sti)

    system = _les_prompt()
    tekst = "Analyser produktet på bildet og returner JSON som spesifisert."
    if ekstra_kontekst:
        tekst += f"\n\nEkstra kontekst fra selger: {ekstra_kontekst}"

    user_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64_data,
            },
        },
        {"type": "text", "text": tekst},
    ]

    data = llm_utils.call_claude_json(system=system, user_content=user_content)
    return _normaliser(data)


def _normaliser(data: dict) -> dict:
    """Sikrer at påkrevde felt finnes og har riktig type."""
    if not isinstance(data, dict):
        raise ValueError("Vision-svaret var ikke et JSON-objekt.")

    # tilstand_score -> int klampet til 1-5
    score = data.get("tilstand_score", 3)
    try:
        score = int(round(float(score)))
    except (TypeError, ValueError):
        score = 3
    score = max(1, min(5, score))
    data["tilstand_score"] = score

    # tilstand_tekst – fyll ut hvis den mangler
    if not data.get("tilstand_tekst"):
        data["tilstand_tekst"] = _TILSTAND_TEKST[score]

    # finn_sokord -> ikke-tom liste av strenger
    sokord = data.get("finn_sokord")
    if isinstance(sokord, str):
        sokord = [sokord]
    if not isinstance(sokord, list):
        sokord = []
    sokord = [str(s).strip() for s in sokord if str(s).strip()]
    if not sokord:
        raise ValueError("Vision-svaret mangler brukbare 'finn_sokord'.")
    data["finn_sokord"] = sokord

    # Fyll inn eventuelle manglende valgfrie felt.
    for felt in _PAAKREVDE_FELT:
        data.setdefault(felt, "")

    return data
