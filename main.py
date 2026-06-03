"""CLI for Finn.no halvautomatisk annonse-agent.

Kommandoer per steg, slik at hvert trinn kan verifiseres for seg:

    python main.py vision   --bilde bilde.jpg [--kontekst "..."]
    python main.py pris     --sokord ord1 ord2 ord3
    python main.py annonse  --bilde bilde.jpg [--selger-info "..."]
    python main.py publiser --bilde bilde.jpg [--ekstra-bilder b2.jpg ...] [--selger-info "..."]
"""

import argparse
import json
import sys


def build_parser() -> argparse.ArgumentParser:
    """Bygger argument-parser. Ingen sideeffekter – enhetstestbar."""
    parser = argparse.ArgumentParser(
        prog="finn-agent",
        description="Halvautomatisk Finn.no annonse-agent.",
    )
    sub = parser.add_subparsers(dest="kommando", required=True)

    p_vision = sub.add_parser("vision", help="Analyser et produktbilde.")
    p_vision.add_argument("--bilde", required=True, help="Sti til bildefil.")
    p_vision.add_argument("--kontekst", default=None, help="Ekstra kontekst fra selger.")

    p_pris = sub.add_parser("pris", help="Hent prisreferanser fra Finn.")
    p_pris.add_argument("--sokord", required=True, nargs="+", help="Ett eller flere søkeord.")

    p_annonse = sub.add_parser(
        "annonse", help="Generer full annonse (vision -> pris -> tekst)."
    )
    p_annonse.add_argument("--bilde", required=True, help="Sti til bildefil.")
    p_annonse.add_argument("--selger-info", dest="selger_info", default=None)

    p_pub = sub.add_parser(
        "publiser", help="Full pipeline og åpne Finn for forhåndsutfylling."
    )
    p_pub.add_argument("--bilde", required=True, help="Sti til primærbilde.")
    p_pub.add_argument(
        "--ekstra-bilder", dest="ekstra_bilder", nargs="*", default=[],
        help="Flere bilder som lastes opp i tillegg til primærbildet.",
    )
    p_pub.add_argument("--selger-info", dest="selger_info", default=None)

    return parser


def _skriv_json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _kjor_vision(args) -> dict:
    from agent.vision import analyser_bilde

    print(f"🔍 Analyserer bilde: {args.bilde}", file=sys.stderr)
    return analyser_bilde(args.bilde, args.kontekst)


def _kjor_pris(args) -> dict:
    from agent.prisjeger import hent_prisstatistikk

    print(f"💰 Henter prisreferanser for: {' '.join(args.sokord)}", file=sys.stderr)
    return hent_prisstatistikk(args.sokord)


def _kjor_annonse(args) -> dict:
    from agent.annonsegenerator import generer_annonse
    from agent.prisjeger import hent_prisstatistikk
    from agent.vision import analyser_bilde

    print(f"🔍 Analyserer bilde: {args.bilde}", file=sys.stderr)
    vision = analyser_bilde(args.bilde, args.selger_info)
    print(
        f"📦 {vision['kategori']} → {vision['underkategori']} "
        f"(tilstand {vision['tilstand_score']}/5)",
        file=sys.stderr,
    )
    print(f"💰 Henter prisreferanser for: {' '.join(vision['finn_sokord'])}", file=sys.stderr)
    pris = hent_prisstatistikk(vision["finn_sokord"])
    print("✍️  Genererer annonse...", file=sys.stderr)
    return generer_annonse(vision, pris, args.selger_info)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.kommando == "vision":
        _skriv_json(_kjor_vision(args))
    elif args.kommando == "pris":
        _skriv_json(_kjor_pris(args))
    elif args.kommando == "annonse":
        _skriv_json(_kjor_annonse(args))
    elif args.kommando == "publiser":
        annonse = _kjor_annonse(args)
        _skriv_json(annonse)
        from agent.finn_browser import aapne_og_forhandsutfyll

        bilder = [args.bilde, *args.ekstra_bilder]
        aapne_og_forhandsutfyll(annonse, bilder)

    return 0


if __name__ == "__main__":
    sys.exit(main())
