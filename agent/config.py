"""Sentral konfigurasjon.

Laster ``.env`` én gang og eksponerer felles konstanter. Alle andre moduler
importerer herfra i stedet for å lese miljøvariabler direkte.
"""

import os

# Last .env fra prosjektroten hvis python-dotenv er installert (idempotent og
# trygt selv om filen mangler). Pakkes inn slik at modulen kan importeres i
# testmiljøer uten python-dotenv.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


# --- Modell ---------------------------------------------------------------
# Standardmodell kan overstyres med miljøvariabelen ANTHROPIC_MODEL uten å
# endre kode.
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MODEL = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
MAX_TOKENS = 1500


# --- Bildebehandling ------------------------------------------------------
IMAGE_MAX_EDGE = 1568            # Anthropics anbefalte maks lengste kant (px)
IMAGE_TARGET_BYTES = 3_500_000   # Mål for kodet bildestørrelse
IMAGE_HARD_LIMIT_BYTES = 5_000_000  # Hard grense i API-et
JPEG_QUALITY = 85


# --- Scraping -------------------------------------------------------------
FINN_SEARCH_URL = "https://www.finn.no/recommerce/forsale/search"
HTTP_TIMEOUT = 20
HTTP_RETRIES = 3
POLITE_DELAY_SECONDS = 1.5
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
MAX_REFERENCE_LISTINGS = 8


def get_api_key() -> str:
    """Returnerer ANTHROPIC_API_KEY, eller feiler med en tydelig melding."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY er ikke satt. Legg den i .env (se .env.example) "
            "eller kjør: export ANTHROPIC_API_KEY=sk-ant-..."
        )
    return key
