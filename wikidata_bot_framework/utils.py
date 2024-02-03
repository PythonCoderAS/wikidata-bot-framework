import re
import secrets
from collections import defaultdict
from copy import copy
from typing import Iterable, List, Literal, Mapping, MutableMapping, Union, overload
from typing_extensions import Self

import pywikibot

from .constants import EntityPage, session, preferred_rank_reason_prop, site
from .dataclasses import ExtraProperty, PossibleValueType

entity_url_regex = re.compile(
    r"^https?://(?:www\.)?wikidata\.org/entity/(Q|P|L)(\d+)$", re.IGNORECASE
)


def add_claim_locally(item: EntityPage, claim: pywikibot.Claim):
    item.claims.setdefault(claim.getID(), []).append(claim)


def add_qualifier_locally(claim: pywikibot.Claim, qualifier: pywikibot.Claim):
    qualifier.isQualifier = True
    claim.qualifiers.setdefault(qualifier.getID(), []).append(qualifier)


def remove_qualifiers(claim: pywikibot.Claim, qualifiers: List[pywikibot.Claim]):
    for qualifier in qualifiers:
        if qualifier in claim.qualifiers.get(qualifier.getID(), []):
            claim.qualifiers[qualifier.getID()].remove(qualifier)


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
        new_reference_id: str = new_reference.getID(False)  # type: ignore
        if new_reference not in reference_group:
            reference_group.setdefault(new_reference_id, []).append(new_reference)
            acted = True
    return acted


class OutputHelper(
    defaultdict[str, list[ExtraProperty]], MutableMapping[str, list[ExtraProperty]]
):
    def __init__(self):
        super().__init__(list)

    def add_property(self, prop: ExtraProperty):
        prop_id: str = prop.claim.getID(False)  # type: ignore
        self[prop_id].append(prop)

    def add_properties(self, props: list[ExtraProperty]):
        for prop in props:
            self.add_property(prop)

    def __copy__(self) -> Self:
        oh = type(self)()
        oh.update(self)
        return oh

    def __deepcopy__(self, memo) -> Self:
        raise NotImplementedError("OutputHelper cannot be deepcopied.")

    def copy(self) -> Self:
        return copy(self)

    def add_property_from_property_id_and_value(
        self, property_id: str, value: PossibleValueType
    ):
        """Easily add an ExtraProperty from a property ID and a value.

        :param property_id: The property ID.
        :param value: The value.
        """
        self.add_property(ExtraProperty.from_property_id_and_value(property_id, value))

    def add_property_from_property_id_and_values(
        self, property_id: str, values: list[PossibleValueType]
    ):
        """Easily add an ExtraProperty from a property ID and multiple values.

        :param property_id: The property ID.
        :param values: The values.
        """
        self.add_properties(
            ExtraProperty.from_property_id_and_values(property_id, values)
        )

    def add_property_from_property_ids_and_values(
        self,
        mapping: Union[
            Mapping[str, Union[PossibleValueType, list[PossibleValueType]]], None
        ] = None,
        /,
        **kwargs: Union[PossibleValueType, list[PossibleValueType]],
    ):
        """Easily add ExtraProperties from a mapping of property IDs and values.

        :param mapping: The mapping of property IDs and values.
        :param kwargs: The mapping of property IDs and values.
        """
        self.add_properties(
            ExtraProperty.from_property_ids_and_values(mapping, **kwargs)
        )

    def add_property_from_property_id_and_item_id_value(
        self, property_id: str, value: str
    ):
        """Easily add an ExtraProperty from a property ID and an item ID value.

        :param property_id: The property ID.
        :param value: The item ID value.
        """
        self.add_property(
            ExtraProperty.from_property_id_and_item_id_value(property_id, value)
        )

    def add_property_from_property_id_and_item_id_values(
        self, property_id: str, values: list[str]
    ):
        """Easily add an ExtraProperty from a property ID and multiple item ID values.

        :param property_id: The property ID.
        :param values: The item ID values.
        """
        self.add_properties(
            ExtraProperty.from_property_id_and_item_id_values(property_id, values)
        )

    def add_property_from_property_ids_and_item_id_values(
        self,
        mapping: Union[Mapping[str, Union[str, list[str]]], None] = None,
        /,
        **kwargs: Union[str, list[str]],
    ):
        """Easily add ExtraProperties from a mapping of property IDs and item ID values.

        :param mapping: The mapping of property IDs and item ID values.
        :param kwargs: The mapping of property IDs and item ID values.
        """
        self.add_properties(
            ExtraProperty.from_property_ids_and_item_id_values(mapping, **kwargs)
        )


@overload
def get_sparql_query(
    property_val: str,
    *,
    filter_out_unknown_value: bool = True,
) -> Mapping[str, set[str]]:
    ...


@overload
def get_sparql_query(
    property_val: str,
    *property_values: str,
    multiple_or: Literal[True],
    or_return_value: Literal[False],
    filter_out_unknown_value: bool = True,
) -> set[str]:
    ...


@overload
def get_sparql_query(
    property_val: str,
    *property_values: str,
    multiple_or: Literal[True],
    or_return_value: Literal[True],
    filter_out_unknown_value: bool = True,
) -> Mapping[str, Mapping[str, set[str]]]:
    ...


@overload
def get_sparql_query(
    property_val: str,
    *property_values: str,
    multiple_or: Literal[False],
    or_return_value: bool = True,
    filter_out_unknown_value: bool = True,
) -> Mapping[str, Mapping[str, set[str]]]:
    ...


def get_sparql_query(
    property_val: str,
    *property_values: str,
    multiple_or: bool = True,
    or_return_value: bool = False,
    filter_out_unknown_value: bool = True,
) -> Union[set[str], Mapping[str, Mapping[str, set[str]]], Mapping[str, set[str]]]:
    """Get the requests of a SPARQL query.

    :param property_values: The properties to query.
    :param multiple_or: When specifying multiple values, whether to check for any one of them or all of them. Defaults to True.
    :param or_return_value: When multiple_or is True, return the values. Defaults to False.
    :param filter_out_unknown_value: Whether to filter out unknown/no values. Defaults to True.
    """
    property_values = (property_val,) + property_values
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
    r = session.post(
        "https://query.wikidata.org/sparql",
        data={"query": query},
        headers={"Accept": "application/sparql-results+json;charset=utf-8"},
    )
    r.raise_for_status()
    data = r.json()
    if not or_return_value:
        return {
            item["item"]["value"].split("/")[-1] for item in data["results"]["bindings"]
        }
    elif len(property_values) == 1:
        retval1 = defaultdict(set)
        for item in data["results"]["bindings"]:
            if filter_out_unknown_value and ".well-known" in str(
                item[f"prop{property_values[0]}"]["value"]
            ):
                continue
            retval1[item["item"]["value"].split("/")[-1]].add(
                item[f"prop{property_values[0]}"]["value"]
            )
        return dict(retval1)
    else:
        retval2: defaultdict[str, defaultdict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for item in data["results"]["bindings"]:
            for prop in property_values:
                if filter_out_unknown_value and ".well-known" in str(
                    item[f"prop{prop}"]["value"]
                ):
                    continue
                retval2[item["item"]["value"].split("/")[-1]][prop].add(
                    item[f"prop{prop}"]["value"]
                )
        return dict(retval2)


def get_random_hex(num_chars: int = 32):
    """Generate a random hex suitable for EditGrouos.

    :param num_chars: The number of hexadecimal digits wanted, defaults to 32
    :return: A random hex string.
    """
    return secrets.token_hex(num_chars // 2)


def mark_claim_as_preferred(
    claim: Union[pywikibot.Claim, list[pywikibot.Claim]],
    claim_list: list[pywikibot.Claim],
    reason_for_preferred_rank_item: Union[pywikibot.ItemPage, None] = None,
) -> bool:
    """Mark a claim as preferred.

    :param claim: The claim or list of claims to mark as preferred.
    :param claim_list: The list of claims that have the same property as the target claim The target claim(s) will be marked preferred while all other claims will be unmarked.
    :param reason_for_preferred_rank_item: The item to use as the value for the qualifer "reason for preferred rank". Leave blank to not include the qualifier.
    :return: True if the rank of any claims were changed.
    """
    if not isinstance(claim, list):
        claim = [claim]
    changed = False
    for c in claim_list:
        if c in claim:
            if not c.rank == "preferred":
                c.rank = "preferred"
                changed = True
            if reason_for_preferred_rank_item:
                qual = pywikibot.Claim(
                    site, preferred_rank_reason_prop, is_qualifier=True
                )
                qual.setTarget(reason_for_preferred_rank_item)
                if c.qualifiers.get(preferred_rank_reason_prop, None) != [qual]:
                    c.qualifiers[preferred_rank_reason_prop] = [qual]
                    changed = True
        else:
            if c.rank == "preferred":
                c.rank = "normal"
                changed = True
            if preferred_rank_reason_prop in c.qualifiers:
                del c.qualifiers[preferred_rank_reason_prop]
                changed = True
    return changed


def resolve_multiple_property_claims(
    query_values: Mapping[str, set[str]],
) -> Mapping[tuple[str, str], set[str]]:
    """Get the items for multiple different claims.

    For example, if you want to know if any items have PXXX=QYYY, or any items that have PAAA=QBBB, this function will return any items that match either of those claims.

    This is useful for doing multiple resolutions really fast.

    Precondition: The property IDs in query_values must be external IDs. Any other type may not work.

    :param query_values: The mapping of property IDs and values to search for
    :return: A Mapping where the key is a tuple consisting of a property ID and a given value, and the value is a set of matching item IDs.
    """
    flattened_values: list[tuple[str, str]] = []
    for prop, values in query_values.items():
        flattened_values.extend([(prop, value) for value in values])
    props: Iterable[str] = query_values.keys()
    template_string = (
        '{ ?item wdt:%(prop)s "%(value)s" . ?item wdt:%(prop)s ?val%(prop)s . }'
    )
    filled = [
        template_string % {"prop": prop, "value": value}
        for prop, value in flattened_values
    ]
    query_variables = "?item " + " ".join(f"?val{prop}" for prop in props)
    query_string = (
        "SELECT DISTINCT "
        + query_variables
        + " WHERE { "
        + " UNION ".join(filled)
        + " }"
    )
    r = session.post(
        "https://query.wikidata.org/sparql",
        data={"query": query_string},
        headers={"Accept": "application/sparql-results+json;charset=utf-8"},
    )
    r.raise_for_status()
    data = r.json()
    retval: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for item in data["results"]["bindings"]:
        valKey = next(key for key in item.keys() if key.startswith("val"))
        propID = valKey[3:]
        propValue = item[valKey]["value"]
        itemValue = item["item"]["value"]
        retval[(propID, propValue)].add(itemValue)
    return retval


def get_entity_id_from_entity_url(entity_url: str) -> str:
    """Get the entity ID from an entity URL.

    :param entity_url: The entity URL.
    :return: The entity ID.
    """
    assert entity_url_regex.match(entity_url), "Invalid entity URL"
    return entity_url.split("/")[-1]
