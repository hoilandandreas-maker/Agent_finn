"""Browser-forutfylling (steg 4).

Åpner Finn.no i en synlig Chromium med vedvarende profil (innlogging
gjenbrukes mellom kjøringer), venter på manuell innlogging, og forhåndsutfyller
ny-annonse-skjemaet. Agenten klikker ALDRI Publiser – det gjør brukeren selv
etter å ha gjennomgått skjemaet.

Playwright importeres lazy slik at resten av prosjektet og testene fungerer
uten at en browser er installert. Den rene ``_felt_verdier`` er enhetstestbar.
"""

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


def aapne_og_forhandsutfyll(
    annonse: dict,
    bilde_stier: list[str] | None = None,
    profil_dir: str = "finn_profil",
) -> None:
    """Åpner Finn i synlig browser, venter på innlogging og forhåndsutfyller skjemaet."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Pakken 'playwright' er ikke installert. Kjør:\n"
            "  pip install -r requirements.txt\n"
            "  python -m playwright install chromium"
        ) from exc

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

        # Manuell innlogging (håndterer 2FA/BankID/Vipps/CAPTCHA).
        if "login" in page.url or "logg-inn" in page.url:
            print("\n⚠️  Logg inn på Finn.no i browser-vinduet.")
            input("Trykk Enter her når du er innlogget...")
            page.goto(FINN_NY_ANNONSE)

        _fyll_felt(page, _TITTEL_SELEKTORER, verdier.get("tittel"))
        _fyll_felt(page, _PRIS_SELEKTORER, verdier.get("pris"))
        _fyll_felt(page, _BESKRIVELSE_SELEKTORER, verdier.get("beskrivelse"))

        if bilde_stier:
            try:
                page.locator("input[type='file']").first.set_input_files(bilde_stier)
            except Exception as exc:  # noqa: BLE001 – best effort
                print(f"⚠️  Bildeopplasting feilet: {exc}. Last opp manuelt.")

        print("\n✅ Skjemaet er forhåndsutfylt.")
        print("📋 Sjekk kategori og øvrige felter i browseren.")
        print("🚀 Klikk 'Publiser' når du er klar – agenten publiserer ikke selv.")
        input("\nTrykk Enter her for å avslutte (browseren forblir åpen)...")


def _fyll_felt(page, selektorer: list[str], verdi: str | None) -> None:
    """Best-effort utfylling: prøver flere selektorer, hopper over ved feil."""
    if not verdi:
        return
    for sel in selektorer:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.fill(verdi)
                return
        except Exception:  # noqa: BLE001 – prøv neste selektor
            continue
    print(f"⚠️  Fant ikke felt for: {selektorer}. Fyll ut manuelt i browseren.")
