"""Lokal Gradio-web-UI for Finn.no annonse-agenten.

Kjør lokalt:
    python app.py            # åpner http://127.0.0.1:7860 i nettleseren

Krever ANTHROPIC_API_KEY i .env eller miljøet. Steg 1–3 (analyse, priser,
annonsetekst) kjører i appen; «Åpne Finn» starter en egen prosess som åpner en
ekte nettleser for forhåndsutfylling – du logger inn og klikker Publiser selv.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import gradio as gr

# Importene under laster også .env (via agent.config) og må komme før key-sjekk.
from agent.annonse_format import analyse_markdown, pris_markdown
from agent.annonsegenerator import generer_annonse
from agent.prisjeger import hent_prisstatistikk
from agent.vision import analyser_bilde

ROOT = Path(__file__).resolve().parent

# Antall UI-utdata fra analyse-handleren (brukt for konsistente retur-tupler).
_TOMME_UTDATA = ("", "", "", 0, "", "", "")


def _har_api_nokkel() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _bildestier(bilder) -> list[str]:
    """gr.File(type="filepath") gir strenger; eldre versjoner gir objekter med .name."""
    return [getattr(b, "name", b) for b in (bilder or [])]


def analyser_og_generer(bilder, selger_info):
    """Kjører vision → pris → annonse og fyller UI-feltene.

    Returnerer (analyse_md, pris_md, tittel, pris, beskrivelse, begrunnelse_md, status).
    """
    if not _har_api_nokkel():
        return (*_TOMME_UTDATA[:-1],
                "⚠️ **ANTHROPIC_API_KEY er ikke satt.** Legg den i `.env` og start appen på nytt.")

    stier = _bildestier(bilder)
    if not stier:
        return (*_TOMME_UTDATA[:-1], "⚠️ Last opp minst ett bilde.")

    try:
        vision = analyser_bilde(stier[0], selger_info or None)
    except Exception as exc:  # noqa: BLE001
        return (*_TOMME_UTDATA[:-1], f"⚠️ Bildeanalyse feilet: {exc}")
    analyse_md = analyse_markdown(vision)

    try:
        pris = hent_prisstatistikk(vision["finn_sokord"])
    except Exception as exc:  # noqa: BLE001 – pris er ikke kritisk
        pris = {"antall_annonser": 0, "feil": str(exc)}
    pris_md = pris_markdown(pris)

    try:
        annonse = generer_annonse(vision, pris, selger_info or None)
    except Exception as exc:  # noqa: BLE001
        return (analyse_md, pris_md, "", 0, "", "", f"⚠️ Annonsegenerering feilet: {exc}")

    begrunnelse_md = (
        f"**Prisbegrunnelse:** {annonse.get('pris_begrunnelse', '–')}\n\n"
        f"**Finn-kategori:** {annonse.get('finn_kategori', '–')} → "
        f"{annonse.get('finn_underkategori', '–')}"
    )
    return (
        analyse_md,
        pris_md,
        annonse.get("tittel", ""),
        annonse.get("anbefalt_pris", 0),
        annonse.get("beskrivelse", ""),
        begrunnelse_md,
        "✅ Forslag generert. Rediger fritt, og klikk «Åpne Finn» når du er fornøyd.",
    )


def apne_finn(bilder, tittel, pris, beskrivelse):
    """Starter forhåndsutfylling i en egen prosess (ekte nettleser)."""
    try:
        pris_int = int(pris) if pris else 0
    except (TypeError, ValueError):
        pris_int = 0
    annonse = {
        "tittel": tittel or "",
        "anbefalt_pris": pris_int,
        "beskrivelse": beskrivelse or "",
    }
    if not annonse["tittel"] and not annonse["beskrivelse"]:
        return "⚠️ Generer eller skriv inn en annonse først."

    payload = {"annonse": annonse, "bilder": _bildestier(bilder)}
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(payload, tmp, ensure_ascii=False)
    tmp.close()

    try:
        subprocess.Popen(
            [sys.executable, "-m", "agent.finn_browser", tmp.name], cwd=str(ROOT)
        )
    except Exception as exc:  # noqa: BLE001
        return f"⚠️ Klarte ikke å starte nettleser-prosessen: {exc}"

    return (
        "🌐 Et nettleservindu åpnes i en egen prosess. Logg inn på Finn om nødvendig – "
        "feltene fylles ut automatisk. Gå gjennom skjemaet og klikk **Publiser** selv."
    )


def build_ui() -> gr.Blocks:
    """Bygger Gradio-grensesnittet (ingen sideeffekter – kan bygges i test)."""
    with gr.Blocks(title="Finn annonse-agent") as demo:
        gr.Markdown(
            "# 🛒 Finn.no annonse-agent\n"
            "Last opp bilde(r) → få tilstand, prisreferanser og ferdig annonse. "
            "Du gjennomgår og publiserer selv."
        )
        if not _har_api_nokkel():
            gr.Markdown(
                "> ⚠️ **ANTHROPIC_API_KEY er ikke satt.** Legg den i `.env` "
                "(se `.env.example`) og start appen på nytt."
            )

        with gr.Row():
            with gr.Column(scale=1):
                bilder = gr.File(
                    file_count="multiple",
                    file_types=["image"],
                    type="filepath",
                    label="Produktbilder (det første brukes til analyse)",
                )
                selger_info = gr.Textbox(
                    label="Ekstra info fra selger (valgfritt)",
                    placeholder="F.eks. «Røykfritt hjem, kjøpt 2022»",
                    lines=2,
                )
                analyser_btn = gr.Button(
                    "🔍 Analyser & generer annonse", variant="primary"
                )
                gr.Markdown("### Analyse")
                analyse_md = gr.Markdown()
                gr.Markdown("### Prisreferanser")
                pris_md = gr.Markdown()

            with gr.Column(scale=1):
                gr.Markdown("### Forslag til annonse (rediger fritt)")
                tittel = gr.Textbox(label="Tittel", max_lines=2)
                pris = gr.Number(label="Anbefalt pris (kr)", precision=0)
                beskrivelse = gr.Textbox(label="Beskrivelse", lines=10)
                begrunnelse_md = gr.Markdown()
                apne_btn = gr.Button(
                    "🌐 Åpne Finn og forhåndsutfyll", variant="secondary"
                )
                status = gr.Markdown()

        analyser_btn.click(
            analyser_og_generer,
            inputs=[bilder, selger_info],
            outputs=[analyse_md, pris_md, tittel, pris, beskrivelse, begrunnelse_md, status],
        )
        apne_btn.click(
            apne_finn,
            inputs=[bilder, tittel, pris, beskrivelse],
            outputs=[status],
        )
    return demo


if __name__ == "__main__":
    build_ui().launch()
