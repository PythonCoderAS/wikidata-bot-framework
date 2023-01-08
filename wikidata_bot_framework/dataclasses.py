import dataclasses
import datetime
from collections import defaultdict
from typing import Literal, MutableMapping, Pattern, Union

import pywikibot

from .constants import retrieved_prop, site, url_prop

WikidataReference = MutableMapping[str, list[pywikibot.Claim]]


@dataclasses.dataclass
class ExtraQualifier:
    claim: pywikibot.Claim
    """The claim to add as a qualifier."""
    skip_if_conflicting_exists: bool = False
    """If a qualifier with the same value already exists, don't add it."""
    replace_if_conflicting_exists: bool = False
    """If a qualifier with the same value already exists, replace it."""
    delete_other_if_replacing: bool = False
    """If ``replace_if_conflicting_exists`` is True and there are multiple values for the same property, delete all 
    but the one being replaced."""
    skip_if_conflicting_language_exists: bool = False
    """If a qualifier with the same language already exists, don't add it."""
    make_new_if_conflicting: bool = False
    """If a qualifier with the same value already exists, make a new claim with the same value."""
    reference_only: bool = False
    """Do not add the qualifier, instead only use it for adding references."""


@dataclasses.dataclass
class ExtraReference:
    match_property_values: dict[str, pywikibot.Claim] = dataclasses.field(
        default_factory=dict
    )
    url_match_pattern: Union[Pattern[str], None] = None
    new_reference_props: dict[str, pywikibot.Claim] = dataclasses.field(
        default_factory=dict
    )
    retrieved: dataclasses.InitVar[Union[pywikibot.WbTime, Literal[False], None]] = None

    @classmethod
    def from_reference_claim(
        cls, claim: pywikibot.Claim, also_match_property_values: bool = False
    ):
        self = cls()
        self.add_claim(claim, also_match_property_values)
        return self

    def __post_init__(self, retrieved: Union[pywikibot.WbTime, Literal[False], None]):
        if retrieved is None:
            now = pywikibot.Timestamp.now(tz=datetime.timezone.utc)
            retrieved = pywikibot.WbTime(year=now.year, month=now.month, day=now.day)
        if retrieved:
            retrieved_claim = pywikibot.Claim(site, retrieved_prop)
            retrieved_claim.setTarget(retrieved)
            self.new_reference_props[retrieved_prop] = retrieved_claim

    def add_claim(
        self, claim: pywikibot.Claim, also_match_property_values: bool = False
    ):
        if also_match_property_values:
            self.match_property_values[claim.getID()] = claim
        self.new_reference_props[claim.getID()] = claim

    def is_compatible_reference(self, reference: WikidataReference) -> bool:
        if self.url_match_pattern and url_prop in reference:
            for claim in reference[url_prop]:
                if self.url_match_pattern.match(claim.getTarget()):  # type: ignore
                    return True
        for prop, claim in self.match_property_values.items():
            if prop not in reference:
                continue
            for ref_claim in reference[prop]:
                if ref_claim.getTarget() == claim.getTarget():
                    return True
        return False


@dataclasses.dataclass
class ExtraProperty:
    claim: pywikibot.Claim
    """The claim to add."""
    skip_if_conflicting_exists: bool = False
    """If a claim with the same value already exists, don't add it."""
    replace_if_conflicting_exists: bool = False
    """If a claim with the same value already exists, replace it."""
    delete_other_if_replacing: bool = False
    """If ``replace_if_conflicting_exists`` is True and there are multiple values for the same property, delete all
    but the one being replaced."""
    skip_if_conflicting_language_exists: bool = False
    """If a claim with the same language already exists, don't add it."""
    reference_only: bool = False
    """Do not add the claim, instead only use it for adding references."""
    qualifiers: defaultdict[str, list[ExtraQualifier]] = dataclasses.field(
        default_factory=lambda: defaultdict(list)
    )
    extra_references: list[ExtraReference] = dataclasses.field(default_factory=list)

    def add_qualifier(self, qualifier: ExtraQualifier):
        self.qualifiers[qualifier.claim.getID()].append(qualifier)

    def add_reference(self, reference: ExtraReference):
        self.extra_references.append(reference)
