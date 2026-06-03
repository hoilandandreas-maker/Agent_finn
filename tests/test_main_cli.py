"""Tester for CLI-argumentparsing (build_parser har ingen sideeffekter)."""

import pytest

import main


def test_vision_args():
    args = main.build_parser().parse_args(["vision", "--bilde", "foo.jpg"])
    assert args.kommando == "vision"
    assert args.bilde == "foo.jpg"
    assert args.kontekst is None


def test_pris_args():
    args = main.build_parser().parse_args(["pris", "--sokord", "a", "b", "c"])
    assert args.kommando == "pris"
    assert args.sokord == ["a", "b", "c"]


def test_annonse_args():
    args = main.build_parser().parse_args(
        ["annonse", "--bilde", "x.png", "--selger-info", "hei"]
    )
    assert args.bilde == "x.png"
    assert args.selger_info == "hei"


def test_publiser_args():
    args = main.build_parser().parse_args(
        ["publiser", "--bilde", "a.jpg", "--ekstra-bilder", "b.jpg", "c.jpg"]
    )
    assert args.ekstra_bilder == ["b.jpg", "c.jpg"]


def test_mangler_kommando():
    with pytest.raises(SystemExit):
        main.build_parser().parse_args([])


def test_mangler_paakrevd_arg():
    with pytest.raises(SystemExit):
        main.build_parser().parse_args(["vision"])
