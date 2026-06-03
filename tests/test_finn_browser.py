"""Test for den rene felt-mappingen i finn_browser (uten browser)."""

from agent import finn_browser


def test_felt_verdier_mapper_og_filtrerer():
    annonse = {
        "tittel": "  Sofa 3-seter  ",
        "anbefalt_pris": 1500,
        "beskrivelse": "Pen sofa.",
        "pris_begrunnelse": "ignoreres",
    }
    verdier = finn_browser._felt_verdier(annonse)
    assert verdier == {
        "tittel": "Sofa 3-seter",
        "pris": "1500",
        "beskrivelse": "Pen sofa.",
    }


def test_felt_verdier_dropper_tomme_og_null():
    annonse = {"tittel": "", "anbefalt_pris": 0, "beskrivelse": "Noe"}
    verdier = finn_browser._felt_verdier(annonse)
    assert verdier == {"beskrivelse": "Noe"}
