"""Felles Claude-hjelpere.

Inneholder Anthropic-klientfabrikk, robust JSON-tolkning (tåler kodeblokker og
omkringliggende tekst) og ``call_claude_json`` som tvinger JSON-svar via
assistant-prefill og prøver én gang til med strammere instruksjon ved feil.
"""

import json
import re

from agent import config


class LLMError(RuntimeError):
    """Feil ved kall mot Claude eller ved tolkning av svaret."""


def get_client():
    """Lager en Anthropic-klient. Importeres lazy så modulens rene funksjoner
    kan brukes (og testes) uten at SDK-et er installert."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise LLMError(
            "Pakken 'anthropic' er ikke installert. "
            "Kjør: pip install -r requirements.txt"
        ) from exc
    return anthropic.Anthropic(api_key=config.get_api_key())


def strip_code_fences(text: str) -> str:
    """Fjerner ```json ... ``` eller ``` ... ``` rundt et svar."""
    t = text.strip()
    match = re.match(r"^```[a-zA-Z0-9]*\s*\n?(.*?)\n?```$", t, re.DOTALL)
    if match:
        return match.group(1).strip()
    return t


def _first_json_object(text: str) -> str | None:
    """Finner første balanserte {...}-blokk og respekterer nesting og strenger."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(text: str) -> dict:
    """Tolker JSON fra et modellsvar, tolerant for kodeblokker og ekstra tekst."""
    # 1) Rett fram
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # 2) Strip kodeblokk-innpakning
    stripped = strip_code_fences(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # 3) Skann etter første balanserte objekt
    candidate = _first_json_object(stripped)
    if candidate is not None:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Fant ikke gyldig JSON i svaret: {text[:200]!r}")


def _message_text(response) -> str:
    """Slår sammen all tekst fra et Anthropic-svar."""
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def call_claude_json(
    *,
    system: str,
    user_content,
    max_tokens: int = config.MAX_TOKENS,
    model: str | None = None,
    prefill: str = "{",
    retries: int = 1,
    temperature: float | None = None,
) -> dict:
    """Kaller Claude og returnerer parset JSON.

    Bruker assistant-prefill (``prefill``) for å tvinge JSON, og prøver
    ``retries`` ganger til med en strammere systeminstruksjon dersom svaret
    ikke lar seg tolke.
    """
    model = model or config.MODEL
    client = get_client()

    messages = [{"role": "user", "content": user_content}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})

    sys_prompt = system
    last_err: Exception | None = None
    attempt = 0
    while attempt <= retries:
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": sys_prompt,
            "messages": messages,
        }
        # Tving determinisme ved retry; ellers bruk oppgitt temperatur.
        temp = 0 if attempt > 0 else temperature
        if temp is not None:
            kwargs["temperature"] = temp

        try:
            response = client.messages.create(**kwargs)
        except Exception as exc:  # nettverks-/API-feil
            raise LLMError(f"Claude-kall feilet: {exc}") from exc

        raw = _message_text(response)
        if prefill:
            raw = prefill + raw

        try:
            return extract_json(raw)
        except ValueError as exc:
            last_err = exc
            attempt += 1
            sys_prompt = (
                system
                + "\n\nVIKTIG: Returner KUN gyldig, minifisert JSON. "
                "Ingen forklaring, ingen markdown, ingen kodeblokk."
            )

    raise LLMError(
        f"Klarte ikke å tolke JSON etter {retries + 1} forsøk: {last_err}"
    )
