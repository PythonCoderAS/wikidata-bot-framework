from collections import defaultdict
from typing import List, MutableMapping

import pywikibot

from .dataclasses import ExtraProperty


def add_claim_locally(item: pywikibot.ItemPage, claim: pywikibot.Claim):
    item.claims.setdefault(claim.getID(), []).append(claim)


def add_qualifier_locally(claim: pywikibot.Claim, qualifier: pywikibot.Claim):
    qualifier.isQualifier = True
    claim.qualifiers.setdefault(qualifier.getID(), []).append(qualifier)


def add_reference_locally(claim: pywikibot.Claim, *reference: pywikibot.Claim):
    claim.sources.append(defaultdict(list))
    for ref_claim in reference:
        append_to_source(claim, ref_claim, len(claim.sources) - 1)


def append_to_source(
    claim: pywikibot.Claim, source: pywikibot.Claim, reference_group_index: int
):
    source.isReference = True
    claim.sources[reference_group_index][source.getID()].append(source)


def merge_reference_groups(
    reference_group: defaultdict[str, list[pywikibot.Claim]],
    new_references: list[pywikibot.Claim],
) -> bool:
    acted = False
    for new_reference in new_references:
        if not new_reference.getID() in reference_group:
            reference_group[new_reference.getID()].append(new_reference)
            acted = True
    return acted


class OutputHelper(
    defaultdict[str, List[ExtraProperty]], MutableMapping[str, List[ExtraProperty]]
):
    def __init__(self):
        super().__init__(list)

    def add_property(self, prop: ExtraProperty):
        self[prop.claim.getID()].append(prop)
