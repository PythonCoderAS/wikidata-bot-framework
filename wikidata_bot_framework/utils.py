import secrets
from collections import defaultdict
from typing import Literal, MutableMapping, overload

import pywikibot

from .constants import session
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
    reference_group: MutableMapping[str, list[pywikibot.Claim]],
    new_references: list[pywikibot.Claim],
) -> bool:
    acted = False
    for new_reference in new_references:
        if not new_reference.getID() in reference_group:
            reference_group.setdefault(new_reference.getID(), []).append(new_reference)
            acted = True
    return acted


class OutputHelper(
    defaultdict[str, list[ExtraProperty]], MutableMapping[str, list[ExtraProperty]]
):
    def __init__(self):
        super().__init__(list)

    def add_property(self, prop: ExtraProperty):
        self[prop.claim.getID()].append(prop)


@overload
def get_sparql_query(
    property_val: str,
    *,
    multiple_or=True,
    or_return_value=False,
    filter_out_unknown_value: bool = True,
) -> dict[str, set[str]]:
    ...


@overload
def get_sparql_query(
    *property_values: str,
    multiple_or: Literal[True] = True,
    or_return_value: Literal[False] = False,
    filter_out_unknown_value: bool = True,
) -> set[str]:
    ...


@overload
def get_sparql_query(
    *property_values: str,
    multiple_or: Literal[True] = True,
    or_return_value: Literal[True] = True,
    filter_out_unknown_value: bool = True,
) -> dict[str, dict[str, set[str]]]:
    ...


@overload
def get_sparql_query(
    *property_values: str,
    multiple_or: Literal[False] = False,
    or_return_value: bool = True,
    filter_out_unknown_value: bool = True,
) -> dict[str, dict[str, set[str]]]:
    ...


def get_sparql_query(
    *property_values: str,
    multiple_or=True,
    or_return_value=False,
    filter_out_unknown_value: bool = True,
):
    """Get the requests of a SPARQL query.

    :param property_values: The properties to query.
    :param multiple_or: When specifying multiple values, whether to check for any one of them or all of them. Defaults to True.
    :param or_return_value: When multiple_or is True, return the values. Defaults to False.
    :param filter_out_unknown_value: Whether to filter out unknown/no values. Defaults to True.
    """
    if len(property_values) == 0:
        raise ValueError("No property values specified.")
    elif len(property_values) == 1:
        multiple_or = False
    if not multiple_or:
        or_return_value = True
    query = ""
    if or_return_value:
        query = "SELECT ?item " + " ".join(f"?prop{prop}" for prop in property_values)
    else:
        query = "SELECT ?item"
    query += " WHERE {\n"
    join_val = "UNION \n" if multiple_or else "\n"
    if or_return_value:
        query += join_val.join(
            "{" + f"?item wdt:{prop} ?prop{prop} ." + "}" for prop in property_values
        )
    else:
        query += join_val.join(
            "{" + f"?item wdt:{prop} ?_ ." + "}" for prop in property_values
        )
    query += "\n}"
    r = session.get(
        "https://query.wikidata.org/sparql",
        params={"query": query},
        headers={"Accept": "application/sparql-results+json;charset=utf-8"},
    )
    r.raise_for_status()
    data = r.json()
    if not or_return_value:
        return {
            item["item"]["value"].split("/")[-1] for item in data["results"]["bindings"]
        }
    elif len(property_values) == 1:
        retval = defaultdict(set)
        for item in data["results"]["bindings"]:
            if filter_out_unknown_value and ".well-known" in str(
                item[f"prop{property_values[0]}"]["value"]
            ):
                continue
            retval[item["item"]["value"].split("/")[-1]].add(
                item[f"prop{property_values[0]}"]["value"]
            )
        return dict(retval)
    else:
        retval = defaultdict(lambda: defaultdict(set))
        for item in data["results"]["bindings"]:
            for prop in property_values:
                if filter_out_unknown_value and ".well-known" in str(
                    item[f"prop{prop}"]["value"]
                ):
                    continue
                retval[item["item"]["value"].split("/")[-1]][prop].add(
                    item[f"prop{prop}"]["value"]
                )
        return dict(retval)


def get_random_hex(num_chars: int = 32):
    """Generate a random hex suitable for EditGrouos.

    :param num_chars: The number of hexadecimal digits wanted, defaults to 32
    :return: A random hex string.
    """
    return secrets.token_hex(num_chars // 2)
