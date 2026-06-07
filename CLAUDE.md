# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**Finn.no halvautomatisk annonse-agent** — a semi-automatic assistant that turns a
product photo into a ready-to-review Finn.no listing. It is deliberately *human-in-the-loop*:
the agent **never publishes**. It only prefills the new-listing form in a visible browser;
the user reviews and clicks **Publiser**.

Pipeline (one step per CLI command):

```
photo → vision.py            → condition + category + keywords
      → prisjeger.py         → price references from Finn search (min/max/avg/median)
      → annonsegenerator.py  → title, description, recommended price
      → finn_browser.py      → prefilled form in a real browser (Playwright)
```

## Layout

- `main.py` — CLI entry point, one subcommand per pipeline step.
- `agent/` — the package:
  - `vision.py` (Claude vision), `prisjeger.py` (price scraping),
    `annonsegenerator.py` (listing text), `finn_browser.py` (Playwright form-fill),
    `llm_utils.py`, `image_utils.py`, `config.py`.
- `prompts/` — `annonse.txt`, `tilstand.txt` (prompt templates).
- `tests/` — pytest suite + `tests/fixtures/` (saved Finn HTML for offline parsing tests).

## Commands

```bash
pip install -r requirements.txt
python -m playwright install chromium   # one-time, for finn_browser.py
pytest                                  # config in pyproject.toml (-q, testpaths=tests)
python main.py <step> ...               # see main.py for available steps
```

## Conventions

- **Domain language is Norwegian** (annonse, tilstand, prisjeger) — keep it; tests assert on it.
- Claude API via the `anthropic` SDK; scraping via `httpx` + `beautifulsoup4`; images via `Pillow`.
- Secrets live in `.env` (see `.env.example`) — never hardcode keys.
- The agent must stay non-publishing: changes that auto-submit the Finn form are out of scope.
- New parsing logic should come with a fixture in `tests/fixtures/` and an offline test.
