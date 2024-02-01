from enum import Enum, auto
from typing import Any, TypedDict

import pywikibot

from .dataclasses import WikidataReference


class ProcessReason(Enum):
    """The reason the item will be modified."""

    missing_property = auto()
    """The item has no statements for the property."""
    missing_value = auto()
    """The item does not have a statement for the property with the given value, but does have other statements with the property."""
    different_rank = auto()
    """The item has a statement for the property with the given value, but the rank is different."""
    replace_value = auto()
    """The item does not have a statement for the property with the given value, but does have other statements with the property and :attr:`.ExtraProperty.replace_if_conflicting_exists` is set to ``True``."""
    delete_values = auto()
    """The item has more than one value for the statement and :attr:`.ExtraProperty.delete_other_if_replacing` is set to ``True``. Will always come after :attr:`.ProcessReason.replace_value` if triggered."""
    missing_qualifier_property = auto()
    """There are no qualifiers with the given property for the statement."""
    missing_qualifier_value = auto()
    """The statement does not have a qualifier for the property with the given value, but does have other qualifiers with the property."""
    replace_qualifier_value = auto()
    """The statement does not have a qualifier for the property with the given value, but does have other qualifiers with the property and :attr:`.ExtraQualifier.replace_if_conflicting_exists` is set to ``True``."""
    delete_qualifier_values = auto()
    """The statement has more than one value for the qualifier and :attr:`.ExtraQualifier.delete_other_if_replacing` is set to ``True``. Will always come after :attr:`.ProcessReason.replace_qualifier_value` if triggered."""
    new_claim_from_qualifier = auto()
    """The item had a matching main property, but no matching qualifier. :attr:`.ExtraQualifier.make_new_if_conflicting` is set to ``True``, and so a new main claim was made."""
    merged_reference = auto()
    """The statement had a matching reference but was missing one or more properties and so the two reference groups were merged."""
    missing_reference = auto()
    """The statement did not have a reference group that was similar to the target reference group."""
    post_output = auto()
    """The :meth:`.post_output_process_hook` method reported that the item was modified."""

    def new_claim_was_added(self) -> bool:
        """Returns if the enum value means a new claim was added."""
        return self in [
            self.missing_property,
            self.missing_value,
            self.new_claim_from_qualifier,
        ]

    def claim_modified(self) -> bool:
        """Returns if the enum value means a claim was modified."""
        return self.new_claim_was_added() or self in [
            self.different_rank,
            self.replace_value,
            self.delete_values,
        ]

    def new_qualifier_was_added(self) -> bool:
        """Returns if the enum value means a new qualifier was added."""
        return self in [self.missing_qualifier_property, self.missing_qualifier_value]

    def qualifier_modified(self) -> bool:
        """Returns if the enum value means a qualifier was modified."""
        return self.new_qualifier_was_added() or self in [
            self.replace_qualifier_value,
            self.delete_qualifier_values,
        ]

    def reference_modified(self) -> bool:
        """Returns if the enum value means a reference was modified."""
        return self in [self.missing_reference, self.merged_reference]


class DifferentRankContext(TypedDict):
    existing_claim: pywikibot.Claim
    old_rank: str


class ReplaceValueContext(TypedDict):
    existing_claim: pywikibot.Claim
    """This is the claim that has its value changed."""
    new_claim: pywikibot.Claim
    """This is the claim that had the value that was changed."""
    old_value: Any


class DeleteValuesContext(TypedDict):
    deleted_claims: list[pywikibot.Claim]


class ReplaceQualifierValueContext(TypedDict):
    existing_qualifier: pywikibot.Claim
    """This is the qualifier that has its value changed."""
    new_qualifier: pywikibot.Claim
    """This is the qualifier that had the value that was changed."""
    old_value: Any


class DeleteQualifierValuesContext(TypedDict):
    deleted_qualifiers: list[pywikibot.Claim]


class NewClaimFromQualifierContext(TypedDict):
    old_claim: pywikibot.Claim


class MergedReferenceContext(TypedDict):
    old_reference_group: WikidataReference
    """.. note:: Until T328811 is resolved, if a claim's value is replaced (not likely) then the new value will be in the old reference group."""
