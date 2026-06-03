"""Browser-forutfylling (steg 4).

Åpner Finn.no i en synlig Chromium med vedvarende profil (innlogging
gjenbrukes mellom kjøringer) og forhåndsutfyller ny-annonse-skjemaet. Agenten
klikker ALDRI Publiser – det gjør brukeren selv.

To moduser:
- ``interaktiv=True`` (CLI): bruker ``input()`` som port for innlogging og for
  å holde vinduet åpent.
- ``interaktiv=False`` (web-UI / subprosess): ingen stdin. Gir tid til manuell
  innlogging, fyller best-effort, og holder vinduet åpent til brukeren lukker det.

Kan også startes som subprosess fra web-UI-en:
    python -m agent.finn_browser <payload.json>
der payload er ``{"annonse": {...}, "bilder": [...]}``.

Playwright importeres lazy slik at resten av prosjektet og testene fungerer
uten at en browser er installert. Den rene ``_felt_verdier`` er enhetstestbar.
"""

import sys

FINN_NY_ANNONSE = "https://www.finn.no/bap/forsale/new"

# Flere selektor-kandidater per felt; Finn A/B-tester UI-et, så vi prøver i tur.
_TITTEL_SELEKTORER = ["input[name='title']", "input[placeholder*='ittel']"]
_PRIS_SELEKTORER = ["input[name='price']", "input[type='number']"]
_BESKRIVELSE_SELEKTORER = ["textarea[name='description']", "textarea"]


def _felt_verdier(annonse: dict) -> dict:
    """Ren hjelpefunksjon: mapper annonse-dict til skjemaverdier (uten tomme).

    Faktorert ut slik at felt-mappingen kan enhetstestes uten en browser.
    """
    verdier = {
        "tittel": str(annonse.get("tittel", "")).strip(),
        "pris": str(annonse.get("anbefalt_pris", "")).strip(),
        "beskrivelse": str(annonse.get("beskrivelse", "")).strip(),
    }
    return {k: v for k, v in verdier.items() if v and v != "0"}


def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Pakken 'playwright' er ikke installert. Kjør:\n"
            "  pip install -r requirements.txt\n"
            "  python -m playwright install chromium"
        ) from exc


def aapne_og_forhandsutfyll(
    annonse: dict,
    bilde_stier: list[str] | None = None,
    profil_dir: str = "finn_profil",
    interaktiv: bool = True,
) -> None:
    """Åpner Finn i synlig browser og forhåndsutfyller skjemaet."""
    sync_playwright = _import_playwright()
    verdier = _felt_verdier(annonse)

    with sync_playwright() as p:
        # persistent_context lagrer innlogging/cookies i profil_dir mellom kjøringer.
        context = p.chromium.launch_persistent_context(
            user_data_dir=profil_dir,
            headless=False,  # ALLTID synlig – brukeren må se og godkjenne.
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(FINN_NY_ANNONSE)

        if interaktiv:
            # Manuell innlogging via terminal (håndterer 2FA/BankID/Vipps/CAPTCHA).
            if "login" in page.url or "logg-inn" in page.url:
                print("\n⚠️  Logg inn på Finn.no i browser-vinduet.")
                input("Trykk Enter her når du er innlogget...")
                page.goto(FINN_NY_ANNONSE)
            _fyll_skjema(page, verdier, bilde_stier, forste_vent_ms=10_000)
            print("\n✅ Skjemaet er forhåndsutfylt.")
            print("📋 Sjekk kategori og øvrige felter i browseren.")
            print("🚀 Klikk 'Publiser' når du er klar – agenten publiserer ikke selv.")
            input("\nTrykk Enter her for å avslutte (browseren forblir åpen)...")
        else:
            # Web-UI / subprosess: ingen stdin tilgjengelig.
            print("🌐 Åpner Finn. Logg inn om nødvendig; feltene fylles ut automatisk.")
            # Lang ventetid på første felt gir tid til manuell innlogging.
            _fyll_skjema(page, verdier, bilde_stier, forste_vent_ms=180_000)
            print("📋 Gå gjennom skjemaet og klikk 'Publiser' selv. Lukk vinduet når du er ferdig.")
            try:
                # Hold prosessen (og dermed browseren) i live til brukeren lukker fanen.
                page.wait_for_event("close", timeout=0)
            except Exception:  # noqa: BLE001 – vinduet ble lukket / context borte
                pass


def _fyll_skjema(page, verdier: dict, bilde_stier, forste_vent_ms: int) -> None:
    """Fyller tittel/pris/beskrivelse best-effort og laster opp bilder om mulig."""
    _fyll_felt(page, _TITTEL_SELEKTORER, verdier.get("tittel"), vent_ms=forste_vent_ms)
    _fyll_felt(page, _PRIS_SELEKTORER, verdier.get("pris"), vent_ms=5_000)
    _fyll_felt(page, _BESKRIVELSE_SELEKTORER, verdier.get("beskrivelse"), vent_ms=5_000)

    if bilde_stier:
        try:
            page.locator("input[type='file']").first.set_input_files(bilde_stier)
        except Exception as exc:  # noqa: BLE001 – best effort
            print(f"⚠️  Bildeopplasting feilet: {exc}. Last opp manuelt.")


def _fyll_felt(page, selektorer: list[str], verdi: str | None, vent_ms: int = 0) -> bool:
    """Best-effort utfylling: prøver flere selektorer, hopper over ved feil."""
    if not verdi:
        return False
    for sel in selektorer:
        try:
            if vent_ms:
                page.wait_for_selector(sel, timeout=vent_ms, state="visible")
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.fill(verdi)
                return True
        except Exception:  # noqa: BLE001 – prøv neste selektor
            continue
    print(f"⚠️  Fant ikke felt for: {selektorer}. Fyll ut manuelt i browseren.")
    return False


def _main(argv: list[str] | None = None) -> int:
    """Subprosess-inngang: ``python -m agent.finn_browser <payload.json>``."""
    import json

    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Bruk: python -m agent.finn_browser <payload.json>", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        payload = json.load(f)
    aapne_og_forhandsutfyll(
        payload.get("annonse", {}),
        payload.get("bilder") or None,
        interaktiv=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
