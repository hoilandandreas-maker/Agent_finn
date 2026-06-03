# Testfixturer

`finn_next_data.html` og `finn_css_fallback.html` er håndlagde, minimale
HTML-filer som etterligner Finn.nos søkeresultatside. De brukes av
`tests/test_prisjeger.py` slik at parserne kan testes uten nettverkstilgang.

## Oppdatere mot ekte Finn-data

Finn endrer HTML- og JSON-strukturen jevnlig. For å verifisere parserne mot
virkeligheten:

1. Åpne et Finn-søk i nettleseren, f.eks.
   `https://www.finn.no/recommerce/forsale/search?q=iphone+12`
2. Lagre siden (Ctrl/Cmd+S → "Webside, kun HTML") eller bruk "Vis kilde".
3. Erstatt `finn_next_data.html` med den lagrede filen og kjør
   `pytest tests/test_prisjeger.py`.
4. Juster om nødvendig JSON-stien i `agent/prisjeger.py` (`_samle_annonser`,
   `_finn_pris`, `_finn_url`) eller CSS-selektorene i `parse_css_fallback` slik
   at de matcher dagens struktur.
