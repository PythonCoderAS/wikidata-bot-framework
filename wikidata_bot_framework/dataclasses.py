from enum import Enum, auto
from pywikibot import (
    WbGeoShape,
    Coordinate,
    WbMonolingualText,
    WbQuantity,
    WbTabularData,
    WbTime,
    ItemPage,
    LexemePage,
    LexemeForm,
    LexemeSense,
)
from pywikibot.page import FilePage
from abc import ABC
import dataclasses
import datetime
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Literal,
    Mapping,
    MutableMapping,
    Pattern,
    Union,
    TypeAlias,
    Sequence,
)

import pywikibot
from typing_extensions import Self

from .constants import retrieved_prop, site, url_prop

WikidataReference = MutableMapping[str, list[pywikibot.Claim]]
PossibleValueType: TypeAlias = (
    str
    | None
    | FilePage
    | WbGeoShape
    | Coordinate
    | WbMonolingualText
    | WbQuantity
    | WbTabularData
    | WbTime
    | ItemPage
    | LexemePage
    | LexemeForm
    | LexemeSense
)


class ConflictResolutionChoice(Enum):
    IGNORE = auto()
    """Ignore the conflicting claim and add both claims. This is the default."""
    SKIP = auto()
    """Don't add the claim and skip it. Does not add any qualifiers or references."""
    SKIP_IF_CONFLICTING_LANGUAGE = auto()
    """Same as Skip but only for claims that share the same language."""
    SKIP_MAIN_CLAIM_ONLY = auto()
    """Only skips the main claim. Adds any qualifers and references to the conflicting claim."""
    REPLACE = auto()
    """Replace the claim and ignore any other values."""
    REPLACE_AND_DELETE = auto()
    """Replace the claim and delete any other claims for the property."""
    REFERENCE_ONLY = auto()
    """Only adds the property's references to the conflicting claim."""


class QualifierResolutionChoice(Enum):
    IGNORE = auto()
    """Ignore the conflicting claim and add both claims. This is the default."""
    SKIP = auto()
    """Don't add the claim and skip it."""
    REPLACE = auto()
    """Replace the claim and ignore any other values."""
    REPLACE_AND_DELETE = auto()
    """Replace the claim and delete any other claims for the qualifier."""
    MAKE_NEW_PROPERTY = auto()
    """Make a new property with the same value as the current property and the new qualifier."""


class ClaimShortcutMixin(ABC):
    """A mixin class for anything that takes a claim as the only required init argument."""

    if TYPE_CHECKING:
        claim: pywikibot.Claim

        def __init__(self, claim: pywikibot.Claim) -> None: ...

    @classmethod
    def from_property_id_and_value(
        cls, property_id: str, value: PossibleValueType
    ) -> Self:
        """Easily make a new instance of the class from a property ID and a value.

        :param property_id: The property ID.
        :param value: The value.
        :return: The new instance.
        """
        claim = pywikibot.Claim(site, property_id)
        claim.setTarget(value)
        return cls(claim)

    @classmethod
    def from_property_id_and_values(
        cls, property_id: str, values: list[PossibleValueType]
    ) -> list[Self]:
        """Easily make a new instance of the class from a property ID and a list of values.

        :param property_id: The property ID.
        :param values: The values.
        :return: The new instance.
        """
        return [cls.from_property_id_and_value(property_id, value) for value in values]

    @classmethod
    def from_property_ids_and_values(
        cls,
        mapping: Union[
            Mapping[str, Union[PossibleValueType, list[PossibleValueType]]], None
        ] = None,
        /,
        **kwargs: Union[PossibleValueType, list[PossibleValueType]],
    ) -> list[Self]:
        """Easily make a new instance of the class from a mapping of property IDs and values.

        :param mapping: The mapping of property IDs and values.
        :param kwargs: The mapping of property IDs and values.
        :return: The new instance.
        """
        final = {**(mapping or {}), **kwargs}
        retvals: list[Self] = []
        for key, value in final.items():
            if not isinstance(value, PossibleValueType):
                items: list[PossibleValueType] = value
                new_values: list[Self] = cls.from_property_id_and_values(key, items)
                retvals.extend(new_values)
            else:
                new_val: Self = cls.from_property_id_and_value(key, value)
                retvals.append(new_val)
        return retvals

    @classmethod
    def from_property_id_and_item_id_value(cls, property_id: str, item_id: str) -> Self:
        """Easily make a new instance of the class from a property ID and an item ID.

        :param property_id: The property ID.
        :param item_id: The item ID.
        :return: The new instance.
        """
        claim = pywikibot.Claim(site, property_id)
        claim.setTarget(pywikibot.ItemPage(site, item_id))
        return cls(claim)

    @classmethod
    def from_property_id_and_item_id_values(
        cls, property_id: str, values: list[str]
    ) -> list[Self]:
        """Easily make a new instance of the class from a property ID and a list of item ID values.

        :param property_id: The property ID.
        :param values: The item ID values.
        :return: The new instance.
        """
        return [
            cls.from_property_id_and_item_id_value(property_id, value)
            for value in values
        ]

    @classmethod
    def from_property_ids_and_item_id_values(
        cls,
        mapping: Union[Mapping[str, Union[str, list[str]]], None] = None,
        /,
        **kwargs: Union[str, list[str]],
    ) -> list[Self]:
        """Easily make a new instance of the class from a mapping of property IDs and item ID values.

        :param mapping: The mapping of property IDs and item ID values.
        :param kwargs: The mapping of property IDs and item ID values.
        :return: The new instance.
        """
        final = {**(mapping or {}), **kwargs}
        retvals = []
        for key, value in final.items():
            if isinstance(value, list):
                retvals.extend(cls.from_property_id_and_item_id_values(key, value))
            else:
                retvals.append(cls.from_property_id_and_item_id_value(key, value))
        return retvals

    def get_property_id(self) -> str:
        return self.claim.getID(False)  # type: ignore

    def same_claim(self, other: Self) -> bool:
        return self.claim == other.claim


@dataclasses.dataclass
class ExtraQualifier(ClaimShortcutMixin):
    claim: pywikibot.Claim
    """The claim to add as a qualifier."""
    reference_only: bool = False
    """Do not add the qualifier, instead only use it for adding references."""
    on_conflict: QualifierResolutionChoice = QualifierResolutionChoice.IGNORE
    """If another qualifier exists for the given property ID and a different value, the action to take."""
    on_conflict_more_specific_value: QualifierResolutionChoice = (
        QualifierResolutionChoice.SKIP
    )
    """If another qualifier exists for the given property ID and a different value that is more specific than the given
     value (for example, if the current value is a timestamp of just a year, while the conflicting value is a timestamp
     with the same year but has a month and day attached), the action to take."""
    on_conflict_less_specific_value: QualifierResolutionChoice = (
        QualifierResolutionChoice.REPLACE
    )
    """The inverse of the more specific situation, where we have a more specific qualifier and the existing qualifier
    is less specific."""
    score: int = 1
    """The score of the qualifier. Used to match properties where missing the qualifier will deduct that many units."""

    def __post_init__(self):
        self.claim.isQualifier = True
        self.claim.isReference = False


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
            retrieved_claim = pywikibot.Claim(site, retrieved_prop, is_reference=True)
            retrieved_claim.setTarget(retrieved)
            self.new_reference_props[retrieved_prop] = retrieved_claim

    def add_claim(
        self, claim: pywikibot.Claim, also_match_property_values: bool = False
    ):
        claim_id: str = claim.getID(False)  # type: ignore
        if also_match_property_values:
            self.match_property_values[claim_id] = claim
        self.new_reference_props[claim_id] = claim

    def is_compatible_reference(self, reference: WikidataReference) -> bool:
        if self.url_match_pattern and url_prop in reference:
            for claim in reference[url_prop]:
                target = claim.getTarget()
                if target and self.url_match_pattern.match(target):  # type: ignore
                    return True
        for prop, claim in self.match_property_values.items():
            if prop not in reference:
                continue
            for ref_claim in reference[prop]:
                if ref_claim.getTarget() == claim.getTarget():
                    return True
        return False

    def set_reference(self):
        for prop, claim in self.new_reference_props.items():
            claim.isReference = True


@dataclasses.dataclass
class ExtraProperty(ClaimShortcutMixin):
    claim: pywikibot.Claim
    """The claim to add."""
    on_conflict: ConflictResolutionChoice = ConflictResolutionChoice.IGNORE
    """If another claim exists for the given property ID and a different value, the action to take."""
    on_conflict_more_specific_value: ConflictResolutionChoice = (
        ConflictResolutionChoice.SKIP
    )
    """If another claim exists for the given property ID and a different value that is more specific than the given
     value (for example, if the current value is a timestamp of just a year, while the conflicting value is a timestamp
     with the same year but has a month and day attached), the action to take."""
    on_conflict_less_specific_value: ConflictResolutionChoice = (
        ConflictResolutionChoice.REPLACE
    )
    """The inverse situation, where the new claim has a more specific value than the existing claim."""
    reference_only: bool = False
    """Do not add the claim, instead only use it for adding references."""
    qualifiers: defaultdict[str, list[ExtraQualifier]] = dataclasses.field(
        default_factory=lambda: defaultdict(list), init=False
    )
    """Qualifiers to add to the claim."""
    qualifier_properties_required_to_match: list[str] = dataclasses.field(
        default_factory=list
    )
    """In order to count as the "same claim", the existing claim must have these qualifier properties
    (and they also need to be exist in :attr:`qualifiers`)."""
    extra_references: list[ExtraReference] = dataclasses.field(default_factory=list)
    """References to add to the claim."""

    def add_qualifier(self, qualifier: ExtraQualifier):
        """Add a qualifier to the claim.

        :param qualifier: The qualifier to add.
        """
        self.qualifiers[qualifier.claim.getID(False)].append(qualifier)  # type: ignore

    def add_qualifiers(self, qualifiers: list[ExtraQualifier]):
        """Add qualifiers to the claim.

        :param qualifiers: The qualifiers to add.
        """
        for qualifier in qualifiers:
            self.add_qualifier(qualifier)

    def add_qualifier_with_property_id_and_value(
        self, property_id: str, value: PossibleValueType
    ):
        """Easily add a qualifier to the claim from a property ID and a value.

        :param property_id: The property ID.
        :param value: The value.
        """
        self.add_qualifier(
            ExtraQualifier.from_property_id_and_value(property_id, value)
        )

    def add_qualifiers_with_property_id_and_values(
        self, property_id: str, values: list[PossibleValueType]
    ):
        """Easily add qualifiers to the claim from a property ID and a list of values.

        :param property_id: The property ID.
        :param values: The values.
        """
        self.add_qualifiers(
            ExtraQualifier.from_property_id_and_values(property_id, values)
        )

    def add_qualifiers_with_property_ids_and_values(
        self,
        mapping: Union[
            Mapping[str, Union[PossibleValueType, list[PossibleValueType]]], None
        ] = None,
        /,
        **kwargs: Union[PossibleValueType, list[PossibleValueType]],
    ):
        """Easily add a mapping of qualifiers to the claim from a mapping of property IDs and values.

        :param mapping: A mapping of property ID and either a single value or a list of values.
        :param kwargs: Extra keys for the mapping.
        """
        self.add_qualifiers(
            ExtraQualifier.from_property_ids_and_values(mapping, **kwargs)
        )

    def add_qualifier_with_property_id_and_item_id_value(
        self, property_id: str, item_id: str
    ):
        """Easily add a qualifier to the claim from a property ID and an item ID.

        :param property_id: The property ID.
        :param item_id: The item ID.
        """
        self.add_qualifier(
            ExtraQualifier.from_property_id_and_item_id_value(property_id, item_id)
        )

    def add_qualifiers_with_property_id_and_item_id_values(
        self, property_id: str, item_ids: list[str]
    ):
        """Easily add qualifiers to the claim from a property ID and a list of item IDs.

        :param property_id: The property ID.
        :param item_ids: The item IDs.
        """
        self.add_qualifiers(
            ExtraQualifier.from_property_id_and_item_id_values(property_id, item_ids)
        )

    def add_qualifiers_with_property_ids_and_item_id_values(
        self,
        mapping: Union[Mapping[str, Union[str, list[str]]], None] = None,
        /,
        **kwargs: Union[str, list[str]],
    ):
        """Easily add a mapping of qualifiers to the claim from a mapping of property IDs and item IDs.

        :param mapping: A mapping of property ID and either a single item ID or a list of item IDs.
        :param kwargs: Extra keys for the mapping.
        """
        self.add_qualifiers(
            ExtraQualifier.from_property_ids_and_item_id_values(mapping, **kwargs)
        )

    def add_reference(self, reference: ExtraReference):
        """Add a reference to the claim.

        :param reference: The reference to add.
        """
        self.extra_references.append(reference)

    @staticmethod
    def _qualifier_sorter(item: tuple[str, list[ExtraQualifier]]):
        return any(
            qual.on_conflict == QualifierResolutionChoice.MAKE_NEW_PROPERTY
            for qual in item[1]
        )

    def _check_qualifiers_required(self):
        for required_qualifier in self.qualifier_properties_required_to_match:
            if not self.qualifiers.get(required_qualifier, []):
                raise ValueError(
                    f"Qualifier {required_qualifier} is required but does not exist."
                )

    def sort_qualifiers(self):
        """Sorts qualifiers so the ones with :attr:`.ExtraQualifier.make_new_if_conflicting` are first."""
        self.qualifiers = defaultdict(
            list,
            sorted(self.qualifiers.items(), key=self._qualifier_sorter, reverse=True),
        )

    def __post_init__(self):
        self.claim.isQualifier = self.claim.isReference = False
        if (
            self.on_conflict_more_specific_value
            == ConflictResolutionChoice.SKIP_IF_CONFLICTING_LANGUAGE
        ):
            raise ValueError(
                "ConflictResolutionChoice.SKIP_IF_CONFLICTING_LANGUAGE is not a valid option for on_conflict_more_specific_value."
            )
        if (
            self.on_conflict_less_specific_value
            == ConflictResolutionChoice.SKIP_IF_CONFLICTING_LANGUAGE
        ):
            raise ValueError(
                "ConflictResolutionChoice.SKIP_IF_CONFLICTING_LANGUAGE is not a valid option for on_conflict_less_specific_value."
            )

    def conflicts_with(self, other: "ExtraProperty") -> bool:
        """Returns if thw two claims cannot be merged together. They can be merged if other is the same value and other's
        qualifiers are either not in self, or their values match. The qualifiers do not need to be in the same order."""
        from .utils import qualifiers_equal

        for qualifier_prop, qualifiers in self.qualifiers.items():
            if qualifier_prop in other.qualifiers:
                other_qualifiers = other.qualifiers[qualifier_prop]
                if qualifiers_equal(qualifiers, other_qualifiers):
                    continue
                else:
                    return True
            else:
                continue
        return not other.same_claim(self)


@dataclasses.dataclass
class OpResult:
    acted: bool = False
    re_cycle: bool = False


@dataclasses.dataclass
class ConflictResolution:
    result: OpResult
    new_claims: Sequence[pywikibot.Claim]
    skip_qualifier: bool = False
    skip_reference: bool = False

    def skip_all(self) -> Self:
        self.skip_qualifier = True
        self.skip_reference = True
        return self

    def __post_init__(self):
        if isinstance(self.new_claims, Sequence):
            if len(self.new_claims) < 1:
                raise ValueError("At least one new claim is required.")

    @property
    def primary_new_claim(self) -> pywikibot.Claim:
        return self.new_claims[0]
