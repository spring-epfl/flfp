import pytest
from filterlist_parser.aglintparser import AGLintBinding


def parse_filter_rule(rule):
    aglintbinding = AGLintBinding()
    return aglintbinding.parse_filter_rule(rule)


def test_filterlrule_parser():

    parsed = parse_filter_rule("##amp-ad")
    assert parsed.is_generic_rule is True
    assert parsed.is_exception is False
    assert parsed.is_cosmetic_rule is True
    assert parsed.is_html_rule is False

    parsed = parse_filter_rule("||example.com^")
    assert parsed.is_generic_rule is True
    assert parsed.is_exception is False
    assert parsed.is_cosmetic_rule is False
    assert parsed.is_html_rule is False

    parsed = parse_filter_rule("@@||example.com^")
    assert parsed.is_generic_rule is False
    assert parsed.is_exception is True
    assert parsed.is_cosmetic_rule is False
    assert parsed.is_html_rule is False

    parsed = parse_filter_rule("example.com")
    assert parsed.is_generic_rule is True
    assert parsed.is_exception is False
    assert parsed.is_cosmetic_rule is False
    assert parsed.is_html_rule is False

    parsed = parse_filter_rule("example.com##.example")
    assert parsed.is_generic_rule is False
    assert parsed.is_exception is False
    assert parsed.is_cosmetic_rule is True

    parsed = parse_filter_rule("||example.com/img1.png^$important,domain=a.com")
    assert parsed.is_generic_rule is False
    assert parsed.is_exception is False
    assert parsed.is_cosmetic_rule is False
    assert parsed.is_network_rule is True
    assert "important" in parsed.options
    assert parsed.options["important"] is True

    parsed = parse_filter_rule("||example.com/img1.png$domain=a.com")
    assert parsed.is_generic_rule is False
    assert parsed.is_exception is False
    assert parsed.is_cosmetic_rule is False
    assert parsed.is_network_rule is True
    assert "domain" in parsed.options
    assert parsed.options["domain"] == "a.com"
    assert parsed.is_third_party_rule is True
