# Finn.no Halvautomatisk Annonse-Agent

En halvautomatisk assistent som hjelper deg å lage Finn.no-annonser fra et
produktbilde. Agenten:

1. **Vurderer bildet** (Claude vision) → kategori, tilstand og søkeord
2. **Henter prisreferanser** fra Finn-søk → min/maks/snitt/median
3. **Genererer annonsen** (Claude) → tittel, beskrivelse og anbefalt pris
4. **Forhåndsutfyller** ny-annonse-skjemaet på Finn i en synlig nettleser

Du beholder full kontroll: agenten **publiserer aldri selv** – den fyller bare
ut skjemaet, så gjennomgår du det og klikker **Publiser**.

```
Bilde (+ ev. info)
      ↓
  vision.py          → tilstand + kategori + søkeord
  prisjeger.py       → prisreferanser fra Finn
  annonsegenerator.py→ tittel, beskrivelse, pris
  finn_browser.py    → forhåndsutfylt skjema i nettleseren
      ↓
  Du klikker «Publiser»
```

## Prosjektstruktur

```
.
├── app.py                   # lokal web-UI (Gradio) – dra-og-slipp
├── main.py                  # CLI – én kommando per steg
├── agent/
│   ├── config.py            # laster .env, modell-/bilde-/scraper-konstanter
│   ├── llm_utils.py         # Claude-klient + robust JSON-parsing + retry
│   ├── image_utils.py       # Pillow: orientering, nedskalering, riktig media_type
│   ├── annonse_format.py    # Markdown-formattering for UI
│   ├── vision.py            # steg 1: bilde → tilstand/kategori-JSON
│   ├── prisjeger.py         # steg 2: Finn-søk → prisstatistikk
│   ├── annonsegenerator.py  # steg 3: vision + pris → ferdig annonse
│   └── finn_browser.py      # steg 4: Playwright forhåndsutfylling
├── prompts/
│   ├── tilstand.txt         # systemprompt for tilstandsvurdering
│   └── annonse.txt          # systemprompt for annonsegenerering
├── tests/                   # offline enhetstester (ingen API/nett/browser)
├── requirements.txt
└── .env.example
```

## Oppsett

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium     # bare nødvendig for steg 4

cp .env.example .env                       # legg inn ANTHROPIC_API_KEY i .env
#  (alternativt: export ANTHROPIC_API_KEY=sk-ant-...)
```

Modellen styres av `ANTHROPIC_MODEL` (standard: `claude-sonnet-4-20250514`) og
kan overstyres i `.env` uten å endre kode.

## Web-UI (anbefalt)

Den enkleste måten å bruke agenten på er det lokale web-grensesnittet:

```bash
python app.py        # åpner http://127.0.0.1:7860 i nettleseren
```

Dra inn bilde(r), skriv ev. ekstra info, og klikk **«Analyser & generer annonse»**.
Du får tilstand, prisreferanser og et ferdig annonseforslag du kan redigere rett i
feltene. Når du er fornøyd, klikker du **«Åpne Finn og forhåndsutfyll»** – da åpnes
en ekte nettleser (egen prosess) der du logger inn og klikker Publiser selv.

> Kjøres **lokalt** på din egen maskin: API-nøkkelen blir liggende lokalt, og
> publiseringssteget trenger en synlig nettleser. (Kan ikke hostes på f.eks.
> GitHub Pages, som kun serverer statiske filer.)

## CLI

Hvert steg har også sin egen kommando, så du kan verifisere ett om gangen. JSON
skrives til stdout; statuslinjer går til stderr (lett å pipe videre).

```bash
# Steg 1 – analyser et bilde (verifiser at JSON-output er stabilt)
python main.py vision   --bilde /sti/til/bilde.jpg [--kontekst "Kjøpt 2022, lite brukt"]

# Steg 2 – prisreferanser fra Finn
python main.py pris     --sokord iphone 12 64gb

# Steg 3 – full annonse (vision → pris → tekst), uten nettleser
python main.py annonse  --bilde /sti/til/bilde.jpg --selger-info "Selges pga flytting"

# Steg 4 – full pipeline + åpne Finn for forhåndsutfylling
python main.py publiser --bilde /sti/til/bilde.jpg \
                        --ekstra-bilder bilde2.jpg bilde3.jpg \
                        --selger-info "Røykfritt hjem"
```

Ved steg 4 åpnes en Chromium. Første gang logger du inn på Finn manuelt (håndterer
2FA/BankID/Vipps); innloggingen lagres i `finn_profil/` til neste gang. Deretter
fyller agenten ut feltene, og **du** gjennomgår og publiserer.

## Tester

Enhetstestene kjører helt uten API-nøkkel, nett eller nettleser (Claude-kall er
mocket, scraping testes mot lagrede fixturer):

```bash
pytest -q
```

> Merk: `tests/fixtures/*.html` er håndlagde og etterligner Finn. Finn endrer
> struktur jevnlig – se `tests/fixtures/README.md` for hvordan du oppdaterer dem
> mot en ekte, lagret søkeside hvis parserne trenger justering.

## Robusthet / kjente fallgruver

| Tema | Hvordan det håndteres |
|------|------------------------|
| Modellen pakker JSON i ```-blokk eller prosa | `llm_utils.extract_json` stripper kodeblokk og skanner etter første balanserte `{...}`; prefill + én retry |
| `.env` lastes ikke | `config.py` kaller `load_dotenv()` ved import |
| Feil `media_type` / for store bilder | `image_utils.prepare_image` setter riktig type, retter EXIF og nedskalerer |
| Finn endrer HTML | `prisjeger` foretrekker `__NEXT_DATA__`-JSON, faller tilbake til CSS, med retry + forsinkelse |
| Finn A/B-tester skjemaet | `finn_browser` prøver flere selektorer per felt og hopper over felt som ikke finnes |
| Innlogging utløper | `launch_persistent_context` lagrer sesjonen i `finn_profil/` |

`finn_profil/` (cookies/innlogging) og `.env` er git-ignorert og skal **aldri**
committes.

## Mulige utvidelser

- Gradio-grensesnitt med dra-og-slipp av bilder
- Lagre minstepris i SQLite og varsle ved bud under grensen
- Flere plattformer ved å bytte ut browser-modulen (Tise, eBay, …)
