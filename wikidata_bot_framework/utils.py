from datetime import timedelta
import re
import secrets
from collections import defaultdict
from copy import copy
from typing import (
    Iterable,
    List,
    Literal,
    Mapping,
    MutableMapping,
    Union,
    overload,
    Sequence,
)
from typing_extensions import Self

import pywikibot

from .constants import EntityPage, session, preferred_rank_reason_prop, site
from .dataclasses import ExtraProperty, PossibleValueType, ExtraQualifier

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
        if new_reference_id not in reference_group:
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
    /,
    *,
    filter_out_unknown_value: bool = True,
) -> Mapping[str, set[str]]: ...


@overload
def get_sparql_query(
    property_val: str,
    property_val2: str,
    /,
    *property_values: str,
    multiple_or: Literal[True],
    or_return_value: Literal[False],
    filter_out_unknown_value: bool = True,
) -> set[str]: ...


@overload
def get_sparql_query(
    property_val: str,
    property_val2: str,
    /,
    *property_values: str,
    multiple_or: Literal[True],
    or_return_value: Literal[True],
    filter_out_unknown_value: bool = True,
) -> Mapping[str, Mapping[str, set[str]]]: ...


@overload
def get_sparql_query(
    property_val: str,
    property_val2: str,
    /,
    *property_values: str,
    multiple_or: Literal[False],
    or_return_value: bool = True,
    filter_out_unknown_value: bool = True,
) -> Mapping[str, Mapping[str, set[str]]]: ...


def get_sparql_query(
    property_val: str,
    /,
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


def qualifiers_equal(
    first: list[ExtraQualifier],
    second: list[ExtraQualifier],
    require_rank_to_match: bool = True,
) -> bool:
    """Compares two lists of ExtraQualifiers, and returns if they are equal without respecting order.

    :param first: The first list to be compared.
    :param second: The second list to be compared.
    :param require_rank_to_match: If the ranks of the claims have to match.
    :return:
    """
    for first_qualifier in first:
        found_match = False
        for second_qualifier in second:
            if first_qualifier.same_claim(second_qualifier) and (
                not require_rank_to_match
                or first_qualifier.claim.rank == second_qualifier.claim.rank
            ):
                found_match = True
                break
        if not found_match:
            return False
    return True


def get_precision_range(
    time: pywikibot.WbTime,
) -> tuple[pywikibot.WbTime, pywikibot.WbTime]:
    """Get the range of WbTimes for a given time and precision, where the given time is in the range
    (start <= time < end).

    :param time: The time to be compared.
    :return: A tuple containing (start, end)
    """
    start = time.normalize()
    end: pywikibot.WbTime = time.normalize()  # Copy of start for now

    if time.precision == pywikibot.WbTime.PRECISION["1000000000"]:
        end.year += 1000000000
    elif time.precision == pywikibot.WbTime.PRECISION["100000000"]:
        end.year += 100000000
    elif time.precision == pywikibot.WbTime.PRECISION["10000000"]:
        end.year += 10000000
    elif time.precision == pywikibot.WbTime.PRECISION["1000000"]:
        end.year += 1000000
    elif time.precision == pywikibot.WbTime.PRECISION["100000"]:
        end.year += 100000
    elif time.precision == pywikibot.WbTime.PRECISION["10000"]:
        end.year += 10000
    elif time.precision == pywikibot.WbTime.PRECISION["millennium"]:
        end.year += 1000
    elif time.precision == pywikibot.WbTime.PRECISION["century"]:
        end.year += 100
    elif time.precision == pywikibot.WbTime.PRECISION["decade"]:
        end.year += 10
    elif time.precision == pywikibot.WbTime.PRECISION["year"]:
        end.year += 1
    elif time.precision == pywikibot.WbTime.PRECISION["month"]:
        if time.month == 12:
            end.year += 1
            end.month = 1
        else:
            end.month += 1
    elif time.precision >= pywikibot.WbTime.PRECISION["day"]:
        end_ts = end.toTimestamp()
        if time.precision == pywikibot.WbTime.PRECISION["day"]:
            end_ts += timedelta(days=1)
        elif time.precision == pywikibot.WbTime.PRECISION["hour"]:
            end_ts += timedelta(hours=1)
        elif time.precision == pywikibot.WbTime.PRECISION["minute"]:
            end_ts += timedelta(minutes=1)
        elif time.precision == pywikibot.WbTime.PRECISION["second"]:
            end_ts += timedelta(seconds=1)
        else:
            raise ValueError(f"Unknown precision: {time.precision}")
        end = pywikibot.WbTime.fromTimestamp(end_ts)
    else:
        raise ValueError(f"Unknown precision: {time.precision}")
    return start, end


def more_specific_times(
    first: pywikibot.WbTime,
    second: pywikibot.WbTime,
) -> pywikibot.WbTime | None:
    """Return which of the two times are more specific.

    If they have no overlap (such as one time is the year 2021 and the other time is 05/15/2020), return None.

    If they are the same precision and value (such as both being the year 2020), return None.

    :param first: The first time to be compared.
    :param second:  The second time to be compared.
    :return: The more specific time or None if there is no overlap or if they are the same.
    """
    if first.precision == second.precision:
        return None
    elif first.precision > second.precision:
        second_start, second_end = get_precision_range(second)
        if second_start <= first < second_end:
            # This check means that first is more precise and fits in second's bounds
            # Example: first = 05/05/2020, second = 2020
            # second_start = 01/01/2020, second_end = 01/01/2021
            return first
        else:
            return None
    else:
        # This is the elif branch flipped around
        first_start, first_end = get_precision_range(first)
        if first_start <= second < first_end:
            return second
        else:
            return None


def more_specific_quantities(
    first: pywikibot.WbQuantity,
    second: pywikibot.WbQuantity,
) -> pywikibot.WbQuantity | None:
    """Return which of the two quantities are more specific
    (has aa smaller delta between upperBound/lowerBound and the value).

    If they have the same delta (or both are None), return None.

    If the value is different, return None.

    :param first: The first quantity to be compared.
    :param second: The second quantity to be compared.
    :return: The more specific quantity or None if there is no more specific quantity.
    """
    if first.amount != second.amount:
        return None
    if first.amount is None or second.amount is None:
        return None
    first_lower_delta = (
        first.amount - first.lowerBound if first.lowerBound is not None else None
    )
    first_upper_delta = (
        first.upperBound - first.amount if first.upperBound is not None else None
    )
    if first_lower_delta is None or first_upper_delta is None:
        assert first_lower_delta == first_upper_delta
    second_lower_delta = (
        second.amount - second.lowerBound if second.lowerBound is not None else None
    )
    second_upper_delta = (
        second.upperBound - second.amount if second.upperBound is not None else None
    )
    if second_lower_delta is None or second_upper_delta is None:
        assert second_lower_delta == second_upper_delta
    if first_lower_delta is None and second_lower_delta is None:
        return None  # Both are unknown delts
    elif first_lower_delta is None and second_lower_delta is not None:
        return second  # First is unknown, second is known AKA more specific
    elif first_lower_delta is not None and second_lower_delta is None:
        return first  # Second is unknown, first is known AKA more specific
    else:
        assert first_lower_delta is not None
        assert second_lower_delta is not None
        assert first_upper_delta is not None
        assert second_upper_delta is not None
        if (
            first_lower_delta > second_lower_delta
            and first_upper_delta > second_upper_delta
        ):
            return second  # Second has smaller delta AKA more specific
        elif (
            first_lower_delta < second_lower_delta
            and first_upper_delta < second_upper_delta
        ):
            return first
        else:
            return None  # The upper and lower deltas are different so can't make a choice automatically


class ReferenceDict[K, V](MutableMapping[K, V]):
    """A Dictionary like class that stores data by using the exact reference (id(key)) as the key.
    This allows storing unhashable objects as keys.
    """

    def __init__(self, data: Sequence[tuple[K, V]] | None = None):
        self._data: dict[int, V] = {}
        self._keys: dict[int, K] = {}
        if data:
            self.update(data)

    def __getitem__(self, item: K, /) -> V:
        key = id(item)
        return self._data[key]

    def __setitem__(self, key: K, value: V, /) -> None:
        self._data[id(key)] = value
        self._keys[id(key)] = key

    def __delitem__(self, key: K, /) -> None:
        self._data.pop(id(key))
        self._keys.pop(id(key))

    def __iter__(self):
        return iter(self._keys.values())

    def __len__(self) -> int:
        return len(self._data)
