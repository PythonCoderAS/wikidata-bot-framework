from typing import Sequence

import pywikibot
from pywikibot import WbTime

from wikidata_bot_framework import ExtraProperty, OutputHelper, EntityPage, Output, site
from . import load_revision_for_test, TestPAB, sandbox_item

setup_module, teardown_module = load_revision_for_test(2475514922)


class MatchTestPAB(TestPAB):
    def __init__(self, properties: list[ExtraProperty]):
        super().__init__()
        self.output = OutputHelper()
        self.output.add_properties(properties)

    def get_edit_summary(self, page: EntityPage) -> str:
        return "Testing matching"

    def run_item(
        self,
        item: EntityPage,
    ) -> Output | Sequence[Output]:
        return self.output


def test_exact_match():
    prop = ExtraProperty.from_property_id_and_value(
        "P580", WbTime(2025, precision=WbTime.PRECISION["year"])
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match


def test_not_exact_match():
    prop = ExtraProperty.from_property_id_and_value(
        "P580", WbTime(2026, precision=WbTime.PRECISION["year"])
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert not match


def test_exact_match_no_qualifiers_needed():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match
    assert not match.qualifiers.get("P407", [])


def test_exact_match_qualifiers_provided():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    prop.add_qualifier_with_property_id_and_value(
        "P407", pywikibot.ItemPage(site, "Q1321")
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match
    qualifiers = match.qualifiers
    assert len(qualifiers) == 1
    assert len(qualifiers["P407"]) == 1
    assert qualifiers["P407"][0].getTarget() == pywikibot.ItemPage(site, "Q1321")


def test_exact_match_different_qualifier():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    prop.add_qualifier_with_property_id_and_value(
        "P407", pywikibot.ItemPage(site, "Q5287")
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match


def test_exact_match_required_qualifier():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    prop.add_qualifier_with_property_id_and_value(
        "P407", pywikibot.ItemPage(site, "Q1321")
    )
    prop.qualifier_properties_required_to_match.append("P407")
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match
    qualifiers = match.qualifiers
    assert len(qualifiers) == 1
    assert len(qualifiers["P407"]) == 1
    assert qualifiers["P407"][0].getTarget() == pywikibot.ItemPage(site, "Q1321")


def test_not_exact_match_required_qualifier():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    prop.add_qualifier_with_property_id_and_value(
        "P407", pywikibot.ItemPage(site, "Q5287")
    )
    prop.qualifier_properties_required_to_match.append("P407")
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert not match


def test_exact_match_excluded_claim():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match
    excluded = (match,)
    second_match = match_test.match_new_claim(
        prop, item=sandbox_item, exclude_claims=excluded
    )
    assert second_match


def test_exact_match_excluded_claim_lower_score():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    prop.add_qualifier_with_property_id_and_value(
        "P407", pywikibot.ItemPage(site, "Q1321")
    )
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match
    excluded = (match,)
    second_match = match_test.match_new_claim(
        prop, item=sandbox_item, exclude_claims=excluded
    )
    assert second_match
    assert not second_match.qualifiers.get("P407", [])


def test_not_exact_match_excluded_claim():
    prop = ExtraProperty.from_property_id_and_value(
        "P973", "https://www.wikidata.org/wiki/Q4115189?param=anotherarg"
    )
    prop.add_qualifier_with_property_id_and_value(
        "P407", pywikibot.ItemPage(site, "Q1321")
    )
    prop.qualifier_properties_required_to_match.append("P407")
    match_test = MatchTestPAB([prop])
    match = match_test.match_new_claim(prop, item=sandbox_item)
    assert match
    excluded = (match,)
    second_match = match_test.match_new_claim(
        prop, item=sandbox_item, exclude_claims=excluded
    )
    assert not second_match
