"""Rene formatterere for visning i grensesnitt (ingen tunge avhengigheter).

Holdt adskilt fra app.py slik at de kan enhetstestes uten at Gradio er installert.
"""


def analyse_markdown(vision_data: dict) -> str:
    """Formatterer vision-analysen som lesbar Markdown."""
    v = vision_data or {}
    sokord = ", ".join(v.get("finn_sokord", []) or [])
    return (
        f"**Kategori:** {v.get('kategori', '?')} → {v.get('underkategori', '?')}\n\n"
        f"**Tilstand:** {v.get('tilstand_tekst', '?')} ({v.get('tilstand_score', '?')}/5)\n\n"
        f"**Slitasje:** {v.get('slitasje_beskrivelse', '–')}\n\n"
        f"**Estimert alder:** {v.get('estimert_alder', '–')}\n\n"
        f"**Søkeord:** {sokord or '–'}"
    )


def pris_markdown(pris_data: dict) -> str:
    """Formatterer prisstatistikken som lesbar Markdown."""
    p = pris_data or {}
    if not p.get("antall_annonser"):
        feil = p.get("feil")
        suffix = f" ({feil})" if feil else ""
        return f"_Ingen prisreferanser funnet._{suffix}"

    linjer = [
        f"**Basert på {p['antall_annonser']} annonser fra Finn:**",
        "",
        f"- Lavest: **{p['min_pris']} kr**",
        f"- Median: **{p['median_pris']} kr**",
        f"- Snitt: **{p['snitt_pris']} kr**",
        f"- Høyest: **{p['max_pris']} kr**",
    ]
    ref = p.get("referanse_annonser") or []
    if ref:
        linjer += ["", "**Referanseannonser:**"]
        for a in ref[:5]:
            tittel = a.get("tittel") or "(uten tittel)"
            pris = a.get("pris")
            url = a.get("url") or ""
            if url:
                linjer.append(f"- [{tittel}]({url}) - {pris} kr")
            else:
                linjer.append(f"- {tittel} - {pris} kr")
    return "\n".join(linjer)
