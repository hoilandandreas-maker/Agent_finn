"""Tester for robust JSON-tolkning og call_claude_json (med mock-klient)."""

import pytest

from agent import llm_utils


def test_extract_json_bare():
    assert llm_utils.extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    text = '```json\n{"a": 1, "b": [1, 2]}\n```'
    assert llm_utils.extract_json(text) == {"a": 1, "b": [1, 2]}


def test_extract_json_with_prose():
    text = 'Her er svaret:\n{"a": 1}\nHåper det hjelper!'
    assert llm_utils.extract_json(text) == {"a": 1}


def test_extract_json_nested_and_brace_in_string():
    text = 'prefix {"a": {"b": {"c": 1}}, "d": "}"} suffix'
    assert llm_utils.extract_json(text) == {"a": {"b": {"c": 1}}, "d": "}"}


def test_extract_json_invalid_raises():
    with pytest.raises(ValueError):
        llm_utils.extract_json("ingen json her")


def test_strip_code_fences():
    assert llm_utils.strip_code_fences("```json\n{}\n```") == "{}"
    assert llm_utils.strip_code_fences("```\nhei\n```") == "hei"
    assert llm_utils.strip_code_fences("uendret") == "uendret"


# --- call_claude_json med mock-klient ---------------------------------------


class _Block:
    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_Block(text)]


class _FakeClient:
    def __init__(self, svar):
        self._svar = list(svar)
        self.kall = []

        class _Messages:
            def create(_self, **kwargs):
                self.kall.append(kwargs)
                return _Resp(self._svar.pop(0))

        self.messages = _Messages()


def test_call_claude_json_prefill_reprepend(monkeypatch):
    # Modellen fortsetter etter prefill "{", så svaret mangler ledende klamme.
    fake = _FakeClient(['"tittel": "Test"}'])
    monkeypatch.setattr(llm_utils, "get_client", lambda: fake)

    result = llm_utils.call_claude_json(system="sys", user_content="hei")

    assert result == {"tittel": "Test"}
    # Verifiser at assistant-prefill faktisk ble sendt.
    sendte_meldinger = fake.kall[0]["messages"]
    assert sendte_meldinger[-1] == {"role": "assistant", "content": "{"}


def test_call_claude_json_retry(monkeypatch):
    # Første svar er ubrukelig, andre er gyldig -> retry-stien skal lykkes.
    fake = _FakeClient(["noe rart uten json", '"ok": true}'])
    monkeypatch.setattr(llm_utils, "get_client", lambda: fake)

    result = llm_utils.call_claude_json(system="sys", user_content="hei", retries=1)

    assert result == {"ok": True}
    assert len(fake.kall) == 2  # det ble gjort ett ekstra forsøk


def test_call_claude_json_gir_opp(monkeypatch):
    fake = _FakeClient(["tull", "fortsatt tull"])
    monkeypatch.setattr(llm_utils, "get_client", lambda: fake)

    with pytest.raises(llm_utils.LLMError):
        llm_utils.call_claude_json(system="sys", user_content="hei", retries=1)
