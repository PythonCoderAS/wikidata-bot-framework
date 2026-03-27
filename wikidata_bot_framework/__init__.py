from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass, field
from json import dumps
from typing import (
    Any,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Union,
    overload,
    cast,
    Callable,
)
from typing_extensions import deprecated

import pywikibot
from pywikibot import WbTime, WbQuantity
from sentry_sdk import new_scope

# Make all imports from submodules available here

from .__version__ import __version__, version_info  # noqa: F401

from .constants import (
    session,  # noqa: F401
    url_prop,  # noqa: F401
    retrieved_prop,  # noqa: F401
    archive_date_prop,  # noqa: F401
    archive_url_prop,  # noqa: F401
    deprecated_reason_prop,  # noqa: F401
    link_rot_id,  # noqa: F401
    preferred_rank_reason_prop,  # noqa: F401
    site,  # noqa: F401
    EntityPage,  # noqa: F401
)
from .dataclasses import (
    ClaimShortcutMixin,  # noqa: F401
    ExtraProperty,  # noqa: F401
    ExtraQualifier,  # noqa: F401
    ExtraReference,
    PossibleValueType,
    QualifierResolutionChoice,
    ConflictResolutionChoice,
    OpResult,
    ConflictResolution,  # noqa: F401
)
from .process_reason import (
    ProcessReason,  # noqa: F401
    DifferentRankContext,  # noqa: F401
    ReplaceValueContext,  # noqa: F401
    DeleteValuesContext,  # noqa: F401
    ReplaceQualifierValueContext,  # noqa: F401
    DeleteQualifierValuesContext,  # noqa: F401
    NewClaimFromQualifierContext,  # type: ignore[deprecated] # noqa: F401,UP035
    MergedReferenceContext,  # noqa: F401
)
from .sentry import (
    sentry_avilable,  # noqa: F401
    load_sentry,  # noqa: F401
    report_exception,  # noqa: F401
    start_span,  # noqa: F401
    start_transaction,  # noqa: F401
)
from .transformers import de_archivify_url_property  # noqa: F401
from .utils import (
    add_claim_locally,  # noqa: F401
    add_qualifier_locally,  # noqa: F401
    add_reference_locally,  # noqa: F401
    get_random_hex,  # noqa: F401
    get_sparql_query,  # noqa: F401
    append_to_source,  # noqa: F401
    merge_reference_groups,  # noqa: F401
    OutputHelper,  # noqa: F401
    mark_claim_as_preferred,  # noqa: F401
    remove_qualifiers,  # noqa: F401
    resolve_multiple_property_claims,  # noqa: F401
    get_entity_id_from_entity_url,  # noqa: F401
    more_specific_times,  # noqa: F401
    more_specific_quantities,
    ReferenceDict,  # noqa: F401
)

Output = Mapping[str, List[ExtraProperty]]


@dataclass(frozen=True)
class Config:
    auto_dearchivify_urls: bool = True
    """Automatically get rid of archive.org URLs and turn them into the original URL along with necessary qualifiers"""
    auto_deprecate_archified_urls: bool = True
    """Mark dearchivified URLs as deprecated"""
    create_or_edit_main_property_whitelist_enabled: bool = False
    """Enable the whitelist for creating or editing main properties"""
    create_or_edit_main_property_whitelist: List[str] = field(default_factory=list)
    """The whitelist for creating or editing main properties"""
    copy_ranks_for_nonwhitelisted_main_properties: bool = True
    """Copy the rank of non-whitelisted main properties (requires create_or_edit_main_property_whitelist_enabled)"""
    replace_existing_claims_for_nonwhitelisted_main_properties: bool = False
    """Allow replacing the values of existing claims for non-whitelisted main properties."""
    create_or_edit_qualifiers_for_main_property_whitelist_enabled: bool = False
    """Enable the whitelist for creating or editing qualifiers when the main property is blacklisted (requires create_or_edit_main_property_whitelist_enabled)"""
    create_or_edit_qualifiers_for_main_property_whitelist: List[str] = field(
        default_factory=list
    )
    """The whitelist for creating or editing qualifiers when the main property is blacklisted (requires create_or_edit_main_property_whitelist_enabled)"""
    create_or_edit_references_for_main_property_whitelist_enabled: bool = False
    """Enable the whitelist for creating or editing references when the main property is blacklisted (requires create_or_edit_main_property_whitelist_enabled)"""
    create_or_edit_references_for_main_property_whitelist: List[str] = field(
        default_factory=list
    )
    """The whitelist for creating or editing references when the main property is blacklisted (requires create_or_edit_main_property_whitelist_enabled)"""
    act_on_cycle: bool = False
    """If the bot should do something if it detects a cycle. If False, there is a chance the bot gets stuck in an infinite loop

    .. versionadded:: 7.4.0
    .. deprecated:: 7.4.1
    """
    throw_on_no_edit_cycle: bool = True
    """If the bot should throw an exception if no edits were made to the item but a cycle is being signalled. If False, the loop will silently stop.

    .. versionadded:: 7.4.0
    .. deprecated:: 7.4.1
    """


class PropertyAdderBot(ABC):
    """A bot that adds properties to pages.

    Supports merging existing properties with the internal representation.
    """

    def __init__(self):
        load_sentry()
        self.config = Config()
        self.__random_hex = get_random_hex()

    def set_config(self, config: Config):
        self.config = config

    def get_edit_group_id(self) -> Union[str, None]:
        """Get the edit group ID for the bot.

        This is used to identify the bot in the edit summary.

        :return: The edit group ID for the bot. Return None to omit it.
        """
        return self.__random_hex

    @abstractmethod
    def get_edit_summary(self, page: EntityPage) -> str:
        """Get the edit summary for the bot.

        :param page: The item page that was edited.
        :return: The edit summary to use.
        """
        pass

    def get_full_summary(self, message: str) -> str:
        """Get a fully formatted summary that can be used to update the API and track it to the EditGroup.

        :param message: The message to format with. To use the default summary, pass in the result of :meth:`.get_edit_summary`.
        :return: The fully formatted summary.
        """
        if edit_group_id := self.get_edit_group_id():
            return f"{message} ([[:toolforge:editgroups/b/CB/{edit_group_id}|details]])"
        return message

    @abstractmethod
    def run_item(
        self,
        item: EntityPage,
    ) -> Output | Sequence[Output]:
        """The main work that should be done externally.

        This method will take an item and return a dictionary of list of ExtraProperties.
        The keys are the property IDs.

        :param item: The item to work on.
        :return: A dictionary of list of ExtraProperties. Recommended to use :class:`.OutputHelper`.
        """
        pass

    def can_add_main_property(self, extra_property: ExtraProperty) -> bool:
        """Return if the property can be added or edited"""
        return not extra_property.reference_only

    @deprecated("No longer used, override the compare_targets_equal method.")
    def same_main_property(
        self,
        existing_claim: pywikibot.Claim,
        new_claim: pywikibot.Claim,
        page: EntityPage,
    ) -> bool:
        """Return if the main property is the same.

        :param existing_claim: The existing claim to compare to.
        :param new_claim: The new claim to compare to.
        :param page: The item page that is being edited.
        :return: If the main property is the same.
        """
        return existing_claim.getTarget() == new_claim.getTarget()

    @deprecated("No longer used, override the compare_targets_equal method.")
    def same_qualifier(
        self,
        existing_qualifier: pywikibot.Claim,
        new_qualifier: pywikibot.Claim,
        main_claim: pywikibot.Claim,
        page: EntityPage,
    ) -> bool:
        """Return if the qualifier is the same.

        :param existing_qualifier: The existing qualifier to compare to.
        :param new_qualifier: The new qualifier to compare to.
        :param main_claim: The main claim that the qualifier is on.
        :param page: The item page that is being edited.
        :return: If the qualifier is the same.
        """
        return existing_qualifier.getTarget() == new_qualifier.getTarget()

    def ensure_output_sequence(
        self, output: Output | Sequence[Output]
    ) -> Sequence[Output]:
        """Convert a single output to a sequence of Output if necessary.

        :param output: The output to ensure is a sequence.
        :return: A sequence of Outputs.
        """
        if isinstance(output, Sequence):
            assert not isinstance(output, Mapping)
            return output
        return [output]

    def post_output_process_hook(
        self, output: Output | Sequence[Output], item: EntityPage
    ) -> bool:
        """Do additional processing after all output has been processed.

        :param output: The output that was processed.
        :param item: The item that was edited.
        :return: Return whether or not the item was changed. This will be used
            to determine if an API request should be made.
        """
        return False

    def pre_edit_process_hook(
        self, output: Output | Sequence[Output], item: EntityPage
    ) -> None:
        """Do additional processing before the item is edited.

        This hook only fires if an API request will be made.

        :param output: The output that was processed.
        :param item: The item that will be edited.
        """

    def post_edit_process_hook(
        self, output: Output | Sequence[Output], item: EntityPage
    ) -> None:
        """Do additional processing after the item is edited.

        This hook only fires if an API request was made.

        :param output: The output that was processed.
        :param item: The item that was edited.
        """

    def whitelisted_claim(self, prop: ExtraProperty) -> bool:
        """Return if the claim is whitelisted.

        :param prop: The property to check.
        :return: If the claim is whitelisted.
        """
        if self.config.create_or_edit_main_property_whitelist_enabled:
            if prop.claim.getID() in self.config.create_or_edit_main_property_whitelist:
                return True
            return False
        return True

    def whitelisted_qualifier(
        self, prop: ExtraProperty, qualifier: ExtraQualifier
    ) -> bool:
        """Return if the qualifier is whitelisted.

        :param prop: The property to check.
        :param qualifier: The qualifier to check.
        :return: If the qualifier is whitelisted.
        """
        if self.config.create_or_edit_qualifiers_for_main_property_whitelist_enabled:
            if (
                qualifier.claim.getID()
                in self.config.create_or_edit_qualifiers_for_main_property_whitelist
            ):
                return True
            return False
        return True

    def whitelisted_reference(
        self, prop: ExtraProperty, reference: ExtraReference
    ) -> bool:
        """Return if the reference is whitelisted.

        :param prop: The property to check.
        :param reference: The reference to check.
        :return: If the reference is whitelisted.
        """
        if self.config.create_or_edit_references_for_main_property_whitelist_enabled:
            if any(
                claim.getID(False)
                in self.config.create_or_edit_references_for_main_property_whitelist
                for claim in reference.new_reference_props.values()
            ):
                return True
            return False
        return True

    def more_specific_property_claim(
        self,
        existing_property_claim: pywikibot.Claim,
        new_property_claim: pywikibot.Claim,
        extra_property: ExtraProperty,
    ) -> bool:
        """Return if the existing claim is a more specific value of the new claim.

        :param existing_property_claim: The existing claim to compare to.
        :param new_property_claim: The new claim to compare to.
        :param extra_property: The extra property that has the new claim.
        :return: If the new claim is a more specific value of the existing claim.
        """
        existing_target: PossibleValueType = cast(
            PossibleValueType, existing_property_claim.getTarget()
        )
        new_target: PossibleValueType = cast(
            PossibleValueType, new_property_claim.getTarget()
        )
        if new_target is None or existing_target is None:
            return False  # This will use the general conflict resolution mechanism
        if type(new_target) is not type(existing_target):
            # This handles the "unknown" type
            return False
        elif isinstance(new_target, WbTime):
            assert isinstance(existing_target, WbTime)
            more_specific_time = more_specific_times(existing_target, new_target)
            if more_specific_time is None:
                return False  # No overlap or same precision
            return more_specific_time == existing_target
        elif isinstance(new_target, WbQuantity):
            assert isinstance(existing_target, WbQuantity)
            more_specific_quantity = more_specific_quantities(
                existing_target, new_target
            )
            if more_specific_quantity is None:
                return False
            return more_specific_quantity == existing_target
        else:
            return False  # We don't support this type yet

    def less_specific_property_claim(
        self,
        existing_property_claim: pywikibot.Claim,
        new_property_claim: pywikibot.Claim,
        extra_property: ExtraProperty,
    ) -> bool:
        """Return if the existing claim is a less specific value of the new claim.

        This is implemented in the opposite logic of :meth:`.more_specific_property_claim`. Therefore, if you utilize the
        extra_property attribute, make sure to override this class.

        :param existing_property_claim: The existing claim to compare to.
        :param new_property_claim: The new claim to compare to.
        :param extra_property: The extra property that has the new claim.
        :return: If the new claim is a less specific value of the existing claim.
        """
        return self.more_specific_property_claim(
            new_property_claim, existing_property_claim, extra_property
        )

    def more_specific_qualifier_claim(
        self,
        existing_property_claim: pywikibot.Claim,
        new_property_claim: pywikibot.Claim,
        extra_property: ExtraProperty,
        extra_qualifier: ExtraQualifier,
    ) -> bool:
        """Return if the existing qualifier claim is a more specific value of the new qualifier claim.

        This is implemented using :meth:`.more_specific_property_claim`.

        :param existing_property_claim: The existing claim to compare to.
        :param new_property_claim: The new claim to compare to.
        :param extra_property: The extra property that has the new claim.
        :param extra_qualifier: The extra qualifier that has the new claim.
        :return: If the new claim is a more specific value of the existing claim.
        """
        return self.more_specific_property_claim(
            new_property_claim, existing_property_claim, extra_property
        )

    def less_specific_qualifier_claim(
        self,
        existing_property_claim: pywikibot.Claim,
        new_property_claim: pywikibot.Claim,
        extra_property: ExtraProperty,
        extra_qualifier: ExtraQualifier,
    ) -> bool:
        """Return if the existing claim is a less specific value of the new claim.

        This is implemented in the opposite logic of :meth:`.more_specific_property_claim`. Therefore, if you utilize the
        extra_property attribute, make sure to override this class.

        :param existing_property_claim: The existing claim to compare to.
        :param new_property_claim: The new claim to compare to.
        :param extra_property: The extra property that has the new claim.
        :param extra_qualifier: The extra qualifier that has the new claim.
        :return: If the new claim is a less specific value of the existing claim.
        """
        return self.less_specific_property_claim(
            new_property_claim, existing_property_claim, extra_property
        )

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.missing_property, ProcessReason.missing_value],
        *,
        claim: ExtraProperty,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.different_rank],
        *,
        claim: ExtraProperty,
        context: DifferentRankContext,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.replace_value],
        *,
        claim: ExtraProperty,
        context: ReplaceValueContext,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.delete_values],
        *,
        context: DeleteValuesContext,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[
            ProcessReason.missing_qualifier_property,
            ProcessReason.missing_qualifier_value,
        ],
        *,
        claim: ExtraProperty,
        qualifier: ExtraQualifier,
    ): ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.replace_qualifier_value],
        *,
        claim: ExtraProperty,
        qualifier: ExtraQualifier,
        context: ReplaceQualifierValueContext,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.delete_qualifier_values],
        *,
        claim: ExtraProperty,
        context: DeleteQualifierValuesContext,
    ) -> bool: ...

    @overload
    @deprecated("No longer called, listen for missing_qualifier_value instead")
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.new_claim_from_qualifier],
        *,
        claim: ExtraProperty,
        qualifier: ExtraQualifier,
        context: NewClaimFromQualifierContext,  # type: ignore[deprecated]
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.missing_reference],
        *,
        claim: ExtraProperty,
        reference: ExtraReference,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.merged_reference],
        *,
        claim: ExtraProperty,
        reference: ExtraReference,
        context: MergedReferenceContext,
    ) -> bool: ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.post_output],
    ) -> bool: ...

    def processed_hook(
        self,
        item: EntityPage,
        reason: ProcessReason,
        *,
        claim: Optional[ExtraProperty] = None,
        qualifier: Optional[ExtraQualifier] = None,
        reference: Optional[ExtraReference] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        """Do processing whenever the item is modified. This method is called directly after the item is modified.

        .. versionadded:: 5.8.0

        :param item: The item that was modified.
        :param reason: The reason the item was modified.
        :param claim: The main claim that was added or is having qualifiers/references added, defaults to None
        :param qualifier: The qualifier that was modified, defaults to None
        :param reference: The reference that was modified, defaults to None
        :param context: Additional context with the operation, defaults to None
        :return: If the item was modified. This will cause a re-cycle of the process loop so only use this if something on the same tier or higher was modified.

            +--------------------+-----------------------+-----------------------+-----------------------+
            | Thing being added  | Thing being modified                                                  |
            +                    +-----------------------+-----------------------+-----------------------+
            |                    | Main statement        | Qualifier             | Reference             |
            +====================+=======================+=======================+=======================+
            | Main statement     | Yes                   | Yes                   | Yes                   |
            +--------------------+-----------------------+-----------------------+-----------------------+
            | Qualifier          | No                    | Yes                   | Yes                   |
            +--------------------+-----------------------+-----------------------+-----------------------+
            | Reference          | No                    | No                    | Yes                   |
            +--------------------+-----------------------+-----------------------+-----------------------+
        """
        return False

    def compare_targets_equal(
        self,
        first_claim: pywikibot.Claim,
        second_claim: pywikibot.Claim,
        first_extra: ExtraProperty | ExtraQualifier | ExtraReference | None,
        second_extra: ExtraProperty | ExtraQualifier | ExtraReference | None,
    ) -> bool:
        """Compare if two claim's targets (values) are equal.

        :param first_claim: The first claim to compare.
        :param second_claim: The second claim to compare.
        :param first_extra: The ExtraProperty, ExtraQualifier, or ExtraReference associated with the first claim to compare.
        :param second_extra: The ExtraProperty, ExtraQualifier, or ExtraReference associated with the second claim to compare
        :return: If the two targets are equal
        """
        first_target: PossibleValueType = first_claim.getTarget()
        second_target: PossibleValueType = second_claim.getTarget()
        first_target_type = type(first_target)
        second_target_type = type(second_target)
        if first_target_type != second_target_type:
            return False
        if isinstance(first_target, pywikibot.WbTime):
            assert isinstance(second_target, pywikibot.WbTime)
            first_normalized = first_target.normalize()
            second_normalized = second_target.normalize()
            return first_normalized == second_normalized
        else:
            return first_target == second_target

    def match_new_qualifer(
        self,
        qualifier: ExtraQualifier,
        qualifier_matching_function: Callable[
            [pywikibot.Claim, pywikibot.Claim, ExtraQualifier, None], bool
        ]
        | None = None,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
        main_claim: pywikibot.Claim,
        property: ExtraProperty,
    ) -> pywikibot.Claim | None:
        """This is called to match a new qualifier to an existing qualifier if possible.

        Precondition: The main claim has already been matched by :meth:`.match_new_claim`.

        :param item: The item to process
        :param qualifier: The qualifier to process
        :param qualifier_matching_function: The function to use to match the qualifier. By default, it checks for
            equality.
        :param exclude_claims: List of claims to exclude
        :param main_claim: The main claim that the qualifier will go on.
        :param property: The property that was matched to the main claim.
        :return: An existing Claim if it can be matched, otherwise None
        """
        # Qualifiers are simple
        qualifier_claims_for_qualifier_property = list(
            main_claim.qualifiers.get(qualifier.get_property_id(), [])
        )
        if qualifier_matching_function is None:
            qualifier_matching_function = self.compare_targets_equal
        for potential_match in qualifier_claims_for_qualifier_property:
            if potential_match in exclude_claims:
                continue
            if qualifier_matching_function(
                qualifier.claim,
                potential_match,
                qualifier,
                None,
            ):
                return potential_match
        return None

    def _cache_or_match_new_qualifier(
        self,
        cache: ReferenceDict[ExtraQualifier, pywikibot.Claim | None],
        qualifier: ExtraQualifier,
        qualifier_matching_function: Callable[
            [pywikibot.Claim, pywikibot.Claim, ExtraQualifier, None], bool
        ]
        | None = None,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
        main_claim: pywikibot.Claim,
        property: ExtraProperty,
    ) -> pywikibot.Claim | None:
        if qualifier in cache:
            return cache[qualifier]
        matched = self.match_new_qualifer(
            qualifier,
            qualifier_matching_function,
            item=item,
            exclude_claims=exclude_claims,
            main_claim=main_claim,
            property=property,
        )
        cache[qualifier] = matched
        return matched

    def _determine_score(
        self,
        property: ExtraProperty,
        potential_match: pywikibot.Claim,
        *,
        matched_qualifier_cache: ReferenceDict[ExtraQualifier, pywikibot.Claim | None],
        qualifier_matching_function: Callable[
            [pywikibot.Claim, pywikibot.Claim, ExtraQualifier, None], bool
        ]
        | None = None,
        item: EntityPage,
    ) -> int:
        """Determine the score of a matched claim.

        :param property: The property to compare to
        :param potential_match: A potential match claim
        :param item: The item to process
        :param matched_qualifier_cache: The cached qualifier matches
        :param qualifier_matching_function: The function to use to match the qualifier. By default, it checks for
            equality.
        :return: The score
        """
        score = 0
        for qualifier_prop, qualifiers in property.qualifiers.items():
            for qualifier in qualifiers:
                qualifier_matched = self._cache_or_match_new_qualifier(
                    matched_qualifier_cache,
                    qualifier,
                    qualifier_matching_function,
                    item=item,
                    property=property,
                    main_claim=potential_match,
                )
                if not qualifier_matched:
                    score -= qualifier.score
        for (
            qualifier_prop,
            potential_match_qualifiers,
        ) in potential_match.qualifiers.items():
            for expected_qualifier in potential_match_qualifiers:
                if not any(
                    self.compare_targets_equal(
                        actual_qualifier.claim,
                        expected_qualifier,
                        first_extra=actual_qualifier,
                        second_extra=None,
                    )
                    for actual_qualifier in property.qualifiers.get(qualifier_prop, [])
                ):
                    score -= 1
        return score

    def match_new_claim(
        self,
        property: ExtraProperty,
        value_matching_function: Callable[
            [pywikibot.Claim, pywikibot.Claim, ExtraProperty, None], bool
        ]
        | None = None,
        qualifier_matching_function: Callable[
            [pywikibot.Claim, pywikibot.Claim, ExtraQualifier, None], bool
        ]
        | None = None,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
    ) -> pywikibot.Claim | None:
        """This is called to match a new claim to an existing claim if possible.

        :param property: The property to process
        :param value_matching_function: The function to compare values and determine if they match the desired criteria.
            By default, this tests for equality.
        :param qualifier_matching_function: The function to use to match the qualifier. By default, it checks for
            equality.
        :param exclude_claims: A sequence of claims to exclude (such as if they have been matched to other claims).
        :param item: The item to process
        :return: An existing Claim if it can be matched, otherwise None
        """
        matched_qualifier_cache: ReferenceDict[
            ExtraQualifier, pywikibot.Claim | None
        ] = ReferenceDict()
        # We need to calculate a score for matched claims. Multiple claims can match to a given property, so we'd like
        # to find the statement that best matches. A claim that is *identical* (the value is equal and all qualifiers on
        # property are on the matched claim) gets a score of 0. For each qualifier value that is on the property but
        # not on the target, the score goes down by one. For each qualifier value that is not on the property but on the
        # target, the score goes down by one. This means that conflicting values (where both the property and the
        # existing claim have a value but they're different) get penalized by two.
        matches_by_score: ReferenceDict[pywikibot.Claim, int] = ReferenceDict()

        claims_for_property: list[pywikibot.Claim] = list(
            item.claims.get(property.get_property_id(), [])
        )
        if value_matching_function is None:
            value_matching_function = self.compare_targets_equal
        for potential_match in claims_for_property:
            if potential_match in exclude_claims:
                continue
            if value_matching_function(property.claim, potential_match, property, None):
                # Then, match required qualifiers
                property._check_qualifiers_required()
                matched = True
                for (
                    required_qualifier
                ) in property.qualifier_properties_required_to_match:
                    new_qualifiers = property.qualifiers.get(required_qualifier, [])
                    for new_qualifier in new_qualifiers:
                        if matched and not self._cache_or_match_new_qualifier(
                            matched_qualifier_cache,
                            new_qualifier,
                            qualifier_matching_function,
                            item=item,
                            main_claim=potential_match,
                            property=property,
                        ):
                            matched = False
                            break
                if not matched:
                    continue
                for qualifier_prop, qualifiers in property.qualifiers.items():
                    for qualifier in qualifiers:
                        qualifier_matched = self._cache_or_match_new_qualifier(
                            matched_qualifier_cache,
                            qualifier,
                            qualifier_matching_function,
                            item=item,
                            property=property,
                            main_claim=potential_match,
                        )
                        if (
                            matched
                            and qualifier.on_conflict
                            == QualifierResolutionChoice.MAKE_NEW_PROPERTY
                            and not qualifier_matched
                        ):
                            matched = False
                            break
                if not matched:
                    continue

                matches_by_score[potential_match] = self._determine_score(
                    property,
                    potential_match,
                    item=item,
                    matched_qualifier_cache=matched_qualifier_cache,
                    qualifier_matching_function=qualifier_matching_function,
                )
        if not matches_by_score:
            return None
        return max(matches_by_score.items(), key=lambda matched_item: matched_item[1])[
            0
        ]

    def match_more_specific_claim(
        self,
        property: ExtraProperty,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
    ) -> pywikibot.Claim | None:
        """Match a more specific claim if one exists.

        :param property: The property to match
        :param exclude_claims: The claims to exclude
        :param item: The item to process
        :return: A more specific claim if one exists, otherwise None
        """
        return self.match_new_claim(
            property,
            value_matching_function=lambda first_claim, second_claim, first_extra, second_extra: (
                self.more_specific_property_claim(
                    second_claim, first_claim, first_extra
                )
            ),
            exclude_claims=exclude_claims,
            item=item,
        )

    def match_more_specific_qualifier(
        self,
        qualifier: ExtraQualifier,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
        main_claim: pywikibot.Claim,
        property: ExtraProperty,
    ):
        """Match a more specific qualifier if one exists.

        :param qualifier: The qualifier to match against
        :param exclude_claims: The qualifier claims to exclude
        :param item: The item to process
        :param main_claim: The main claim the qualifier is for
        :param property: The extra property associated with the main claim
        :return:
        """
        return self.match_new_qualifer(
            qualifier,
            lambda first_qualifier, second_qualifier, first_extra, second_extra: (
                self.more_specific_qualifier_claim(
                    second_qualifier, first_qualifier, property, first_extra
                )
            ),
            exclude_claims=exclude_claims,
            item=item,
            main_claim=main_claim,
            property=property,
        )

    def match_less_specific_claim(
        self,
        property: ExtraProperty,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
    ) -> pywikibot.Claim | None:
        """Match a less specific claim if one exists.

        :param property: The property to match
        :param exclude_claims: The claims to exclude
        :param item: The item to process
        :return: A more less specific claim if one exists, otherwise None
        """
        return self.match_new_claim(
            property,
            value_matching_function=lambda first_claim, second_claim, first_extra, second_extra: (
                self.less_specific_property_claim(
                    second_claim, first_claim, first_extra
                )
            ),
            exclude_claims=exclude_claims,
            item=item,
        )

    def match_less_specific_qualifier(
        self,
        qualifier: ExtraQualifier,
        *,
        exclude_claims: Sequence[pywikibot.Claim] = (),
        item: EntityPage,
        main_claim: pywikibot.Claim,
        property: ExtraProperty,
    ):
        """Match a less specific qualifier if one exists.

        :param qualifier: The qualifier to match against
        :param exclude_claims: The qualifier claims to exclude
        :param item: The item to process
        :param main_claim: The main claim the qualifier is for
        :param property: The extra property associated with the main claim
        :return:
        """
        return self.match_new_qualifer(
            qualifier,
            lambda first_qualifier, second_qualifier, first_extra, second_extra: (
                self.less_specific_qualifier_claim(
                    second_qualifier, first_qualifier, property, first_extra
                )
            ),
            exclude_claims=exclude_claims,
            item=item,
            main_claim=main_claim,
            property=property,
        )

    def op_add_property(
        self,
        item: EntityPage,
        new_claim: pywikibot.Claim,
        extra_prop_data: ExtraProperty,
    ) -> OpResult:
        """Handle the "add new claim" operation

        :param item: The item to process
        :param new_claim: The new claim to add
        :param extra_prop_data: The extra property the new claim belongs to
        :return: The result of adding the new claim
        """
        res = OpResult()
        if self.can_add_main_property(extra_prop_data) and self.whitelisted_claim(
            extra_prop_data
        ):
            # This is triggered if there are no statements for the property
            missing_property = len(item.claims[extra_prop_data.get_property_id()]) == 0
            add_claim_locally(item, new_claim)
            res.re_cycle |= self.processed_hook(
                item,
                reason=ProcessReason.missing_property
                if missing_property
                else ProcessReason.missing_value,
                claim=extra_prop_data,
            )
            res.acted = True
        return res

    def op_change_rank(
        self,
        item: EntityPage,
        new_claim: pywikibot.Claim,
        existing_claim: pywikibot.Claim,
        extra_prop_data: ExtraProperty,
    ) -> OpResult:
        """Handle the "change rank" operation

        :param item: The item to process
        :param new_claim: The claim with the new rank
        :param existing_claim: The existing claim with the old rank
        :param extra_prop_data: The extra property the new claim belongs to
        :return: The result of changing the rank
        """
        res = OpResult()
        if new_claim.getRank() != existing_claim.getRank():
            if (
                self.whitelisted_claim(extra_prop_data)
                or self.config.copy_ranks_for_nonwhitelisted_main_properties
            ):
                old_rank = existing_claim.getRank()
                existing_claim.rank = new_claim.getRank()
                res.re_cycle |= self.processed_hook(
                    item,
                    ProcessReason.different_rank,
                    claim=extra_prop_data,
                    context=DifferentRankContext(
                        existing_claim=existing_claim,
                        old_rank=old_rank,
                    ),
                )
                res.acted = True
        return res

    def has_conflicting_language_value(
        self, item: EntityPage, prop: ExtraProperty | ExtraQualifier
    ) -> bool:
        """Returns if the item has a conflicting language value. This filters the conflict choice to just the claims
        with the same language as the prop.

        :param item: The item to process
        :param prop: The extra property or qualifier to process
        :return: Whether the item has conflicting language value
        """
        found_conflicting_language = False
        new_claim = prop.claim
        new_claim_target = new_claim.getTarget()
        if not isinstance(new_claim_target, pywikibot.WbMonolingualText):
            return False  # This check makes no sense if it doesn't have language
        for existing_claim in item.claims[prop.get_property_id()]:
            assert isinstance(existing_claim, pywikibot.Claim)
            if isinstance(
                (lang_target := existing_claim.getTarget()),
                pywikibot.WbMonolingualText,
            ):
                if (
                    lang_target.language == new_claim_target.language
                    and not self.compare_targets_equal(
                        existing_claim, new_claim, prop, None
                    )
                ):
                    found_conflicting_language = True
                    break
        return found_conflicting_language

    def op_replace_value(
        self,
        item: EntityPage,
        new_claim: pywikibot.Claim,
        existing_claim: pywikibot.Claim,
        extra_prop_data: ExtraProperty,
        qualifier: ExtraQualifier | None = None,
    ) -> OpResult:
        """Handle the "replace value" operation

        :param item: The item to process
        :param new_claim: The new claim to replace the old claim
        :param existing_claim: The existing claim to replace
        :param extra_prop_data: The extra property the new claim belongs to
        :param qualifier: The qualifier, if this is replacing a qualifier and not a claim
        :return: If any edits were made to the item.
        """
        if not qualifier:
            res = self.op_change_rank(item, new_claim, existing_claim, extra_prop_data)
        else:
            res = OpResult()
        old_value = existing_claim.getTarget()
        if (
            self.whitelisted_claim(extra_prop_data)
            or self.config.replace_existing_claims_for_nonwhitelisted_main_properties
        ) and (not qualifier or self.whitelisted_qualifier(extra_prop_data, qualifier)):
            existing_claim.setTarget(new_claim.getTarget())
            original_new_claim = new_claim
            if qualifier:
                res.re_cycle |= self.processed_hook(
                    item,
                    ProcessReason.replace_qualifier_value,
                    claim=extra_prop_data,
                    qualifier=qualifier,
                    context=ReplaceQualifierValueContext(
                        existing_qualifier=existing_claim,
                        new_qualifier=new_claim,
                        old_value=old_value,
                    ),
                )
            else:
                res.re_cycle |= self.processed_hook(
                    item,
                    ProcessReason.replace_value,
                    claim=extra_prop_data,
                    context=ReplaceValueContext(
                        existing_claim=existing_claim,
                        new_claim=original_new_claim,
                        old_value=old_value,
                    ),
                )
            res.acted = True
        return res

    @overload
    def op_delete_value(
        self,
        item: EntityPage,
        claimed_values: Sequence[pywikibot.Claim],
        prop_data_for_property_id: Sequence[ExtraProperty],
        extra_prop_data: None = None,
    ) -> OpResult: ...

    @overload
    def op_delete_value(
        self,
        item: EntityPage,
        claimed_values: Sequence[pywikibot.Claim],
        prop_data_for_property_id: Sequence[ExtraQualifier],
        extra_prop_data: ExtraProperty,
    ) -> OpResult: ...

    def op_delete_value(
        self,
        item: EntityPage,
        claimed_values: Sequence[pywikibot.Claim],
        prop_data_for_property_id: Sequence[ExtraProperty] | Sequence[ExtraQualifier],
        extra_prop_data: ExtraProperty | None = None,
    ) -> OpResult:
        """Handle the "delete other values" operation

        :param item: The item to process
        :param claimed_values: The claims that have been claimed. All claims part of the item for the property ID not in this sequence will get deleted.
        :param prop_data_for_property_id: A Sequence of all ExtraProperty or ExtraQualifier for a given property ID
        :param extra_prop_data: If prop_data_for_property_id is ExtraQualifier, this has to be provided
        :return: If any edits were made to the item.
        """
        # Precondition: All ExtraProperty for the given property ID is ConflictResolutionChoice.REPLACE_AND_DELETE
        res = OpResult()
        assert len(prop_data_for_property_id) >= 1
        property_id = prop_data_for_property_id[0].get_property_id()
        if isinstance(prop_data_for_property_id[0], ExtraQualifier):
            if not extra_prop_data:
                raise ValueError("Must be provided for deleting qualifiers")
            deleted_claims = [
                claim
                for claim in extra_prop_data.claim.qualifiers[property_id]
                if claim not in claimed_values
            ]
            kept_claims = [
                claim
                for claim in extra_prop_data.claim.qualifiers[property_id]
                if claim in claimed_values
            ]
            res.acted = len(deleted_claims) > 0
            first_qual = prop_data_for_property_id[0]
            assert isinstance(first_qual, ExtraQualifier)
            if self.whitelisted_claim(extra_prop_data) or self.whitelisted_qualifier(
                extra_prop_data, first_qual
            ):
                res.re_cycle |= self.processed_hook(
                    item,
                    ProcessReason.delete_qualifier_values,
                    context=DeleteQualifierValuesContext(
                        deleted_qualifiers=deleted_claims, kept_qualifiers=kept_claims
                    ),
                    claim=extra_prop_data,
                )
                item.claims[property_id] = kept_claims
        else:
            deleted_claims = [
                claim
                for claim in item.claims[property_id]
                if claim not in claimed_values
            ]
            kept_claims = [
                claim for claim in item.claims[property_id] if claim in claimed_values
            ]
            res.acted = len(deleted_claims) > 0
            if self.whitelisted_claim(prop_data_for_property_id[0]):
                res.re_cycle |= self.processed_hook(
                    item,
                    ProcessReason.delete_values,
                    context=DeleteValuesContext(
                        deleted_claims=deleted_claims, kept_claims=kept_claims
                    ),
                )
                item.claims[property_id] = kept_claims
        return res

    def handle_property_claim_conflict(
        self,
        item: EntityPage,
        extra_prop_data: ExtraProperty,
        conflicting_claim: pywikibot.Claim,
        conflict_value: ConflictResolutionChoice,
    ) -> ConflictResolution:
        """Handle a conflict resolution operation for property claims

        :param item: The item to process
        :param extra_prop_data: The extra property the new claim belongs to
        :param conflicting_claim: The conflicting claim
        :param conflict_value: The enum value representing what operations to do
        :param claimed: The list of claimed claims for the property ID.
        :return: The conflict resolution result
        """
        new_claim = extra_prop_data.claim
        match conflict_value:
            case ConflictResolutionChoice.IGNORE:
                create_op = self.op_add_property(item, new_claim, extra_prop_data)
                if not create_op.acted:
                    # This means we can't add the property
                    return ConflictResolution(create_op, (conflicting_claim,))
                else:
                    return ConflictResolution(create_op, (new_claim, conflicting_claim))
            case ConflictResolutionChoice.SKIP:
                return ConflictResolution(OpResult(), (conflicting_claim,)).skip_all()
            case ConflictResolutionChoice.SKIP_MAIN_CLAIM_ONLY:
                return ConflictResolution(OpResult(), (conflicting_claim,))
            case ConflictResolutionChoice.REFERENCE_ONLY:
                ret = ConflictResolution(OpResult(), (conflicting_claim,))
                ret.skip_qualifier = True
                return ret
            case ConflictResolutionChoice.SKIP_IF_CONFLICTING_LANGUAGE:
                # Precondition, this will never be for a more or less specific value
                conflicting_language = self.has_conflicting_language_value(
                    item, extra_prop_data
                )
                if conflicting_language:
                    # Skip branch
                    return ConflictResolution(
                        OpResult(), (conflicting_claim,)
                    ).skip_all()
                else:
                    # Ignore branch
                    create_op = self.op_add_property(item, new_claim, extra_prop_data)
                    if not create_op.acted:
                        # This means we can't add the property
                        return ConflictResolution(create_op, (conflicting_claim,))
                    else:
                        return ConflictResolution(
                            create_op, (new_claim, conflicting_claim)
                        )
            case (
                ConflictResolutionChoice.REPLACE
                | ConflictResolutionChoice.REPLACE_AND_DELETE
            ):
                replace_op = self.op_replace_value(
                    item, new_claim, conflicting_claim, extra_prop_data
                )
                return ConflictResolution(replace_op, (new_claim,))
            case _:
                raise NotImplementedError(
                    f"Unknown conflict resolution choice: {conflict_value.name}"
                )

    def handle_qualifier_claim_conflict(
        self,
        item: EntityPage,
        qualifier: ExtraQualifier,
        conflicting_claim: pywikibot.Claim,
        conflict_value: QualifierResolutionChoice,
        extra_prop_data: ExtraProperty,
    ) -> ConflictResolution:
        """Handle a conflict resolution operation for qualifier claims

        :param item: The item to process
        :param qualifier: The qualifier to process
        :param extra_prop_data: The extra property the qualifier belongs to
        :param conflicting_claim: The conflicting claim
        :param conflict_value: The enum value representing what operations to do
        :param claimed: The list of claimed claims for the qualifier property ID.
        :return: The conflict resolution result
        """
        match conflict_value:
            case QualifierResolutionChoice.IGNORE:
                create_op = self.op_add_qualifier(item, qualifier, extra_prop_data)
                if not create_op.acted:
                    # This means we can't add the property
                    return ConflictResolution(create_op, (conflicting_claim,))
                else:
                    return ConflictResolution(
                        create_op, (qualifier.claim, conflicting_claim)
                    )
            case QualifierResolutionChoice.SKIP:
                return ConflictResolution(OpResult(), (conflicting_claim,)).skip_all()
            case (
                QualifierResolutionChoice.REPLACE
                | QualifierResolutionChoice.REPLACE_AND_DELETE
            ):
                replace_op = self.op_replace_value(
                    item,
                    qualifier.claim,
                    conflicting_claim,
                    extra_prop_data,
                    qualifier=qualifier,
                )
                return ConflictResolution(replace_op, (qualifier.claim,))
            case _:
                raise NotImplementedError(
                    f"Unknown conflict resolution choice: {conflict_value.name}"
                )

    def op_add_qualifier(
        self,
        item: EntityPage,
        qualifier: ExtraQualifier,
        extra_prop_data: ExtraProperty,
    ) -> OpResult:
        res = OpResult()
        new_claim = extra_prop_data.claim
        qualifier_prop = qualifier.get_property_id()
        missing_qualifier_property = (
            len(new_claim.qualifiers.get(qualifier_prop, [])) == 0
        )
        if self.whitelisted_claim(extra_prop_data) or self.whitelisted_qualifier(
            extra_prop_data, qualifier
        ):
            add_qualifier_locally(new_claim, qualifier.claim)
            res.re_cycle |= self.processed_hook(
                item,
                ProcessReason.missing_qualifier_property
                if missing_qualifier_property
                else ProcessReason.missing_qualifier_value,
                claim=extra_prop_data,
                qualifier=qualifier,
            )
            res.acted = True
        return res

    def merge_output_with_item(self, output: Output, item: EntityPage) -> bool:
        """Actually does the main work of merging the output with the item.

        :param output: The output to process
        :param item: The item to process
        :return: If any edits were made to the item.
        """
        acted = False
        re_cycle = True
        # This is an (inefficient) way to prevent cycles. If an actual change is made, the hash will change.
        second_previous_hash = None
        previous_hash = hash(dumps(item.toJSON()))
        while re_cycle and second_previous_hash != previous_hash:
            re_cycle = False
            for property_id, extra_props in copy(output).items():
                claimed: list[pywikibot.Claim] = []
                is_replace_and_delete = [
                    extra_prop.on_conflict
                    == ConflictResolutionChoice.REPLACE_AND_DELETE
                    for extra_prop in extra_props
                ]
                if any(is_replace_and_delete) and not all(is_replace_and_delete):
                    raise ValueError(
                        "In order to use ConflictResolutionChoice.REPLACE_AND_DELETE, all claims must have it"
                    )
                for extra_prop_data in extra_props.copy():
                    new_claim = extra_prop_data.claim
                    conflict_resolution: ConflictResolution | None = None
                    if new_claim.type == "url" and self.config.auto_dearchivify_urls:
                        de_archivify_url_property(
                            extra_prop_data,
                            deprecate=self.config.auto_deprecate_archified_urls,
                        )
                    if property_id not in item.claims:
                        res = self.op_add_property(item, new_claim, extra_prop_data)
                        re_cycle |= res.re_cycle
                        acted |= res.acted
                        claimed.append(new_claim)
                    else:
                        matched_equal_claim = self.match_new_claim(
                            extra_prop_data,
                            exclude_claims=claimed,
                            item=item,
                        )
                        matched_more_specific_claim = self.match_more_specific_claim(
                            extra_prop_data,
                            exclude_claims=claimed,
                            item=item,
                        )
                        matched_less_specific_claim = self.match_less_specific_claim(
                            extra_prop_data,
                            exclude_claims=claimed,
                            item=item,
                        )
                        if matched_equal_claim:
                            claimed.append(matched_equal_claim)
                            extra_prop_data.claim = matched_equal_claim
                            rank_op = self.op_change_rank(
                                item, new_claim, matched_equal_claim, extra_prop_data
                            )
                            re_cycle |= rank_op.re_cycle
                            acted |= rank_op.acted
                        elif matched_more_specific_claim:
                            conflict_res = self.handle_property_claim_conflict(
                                item,
                                extra_prop_data,
                                matched_more_specific_claim,
                                extra_prop_data.on_conflict_more_specific_value,
                            )
                            claimed.extend(conflict_res.new_claims)
                            extra_prop_data.claim = conflict_res.primary_new_claim
                            re_cycle |= conflict_res.result.re_cycle
                            acted |= conflict_res.result.acted
                            conflict_resolution = conflict_res
                        elif matched_less_specific_claim:
                            conflict_res = self.handle_property_claim_conflict(
                                item,
                                extra_prop_data,
                                matched_less_specific_claim,
                                extra_prop_data.on_conflict_less_specific_value,
                            )
                            claimed.extend(conflict_res.new_claims)
                            extra_prop_data.claim = conflict_res.primary_new_claim
                            re_cycle |= conflict_res.result.re_cycle
                            acted |= conflict_res.result.acted
                            conflict_resolution = conflict_res
                        else:
                            first_conflicting = next(
                                (
                                    claim
                                    for claim in item.claims[
                                        extra_prop_data.get_property_id()
                                    ]
                                    if claim not in claimed
                                ),
                                None,
                            )
                            if first_conflicting:
                                conflict_res = self.handle_property_claim_conflict(
                                    item,
                                    extra_prop_data,
                                    first_conflicting,
                                    extra_prop_data.on_conflict,
                                )
                                claimed.extend(conflict_res.new_claims)
                                extra_prop_data.claim = conflict_res.primary_new_claim
                                re_cycle |= conflict_res.result.re_cycle
                                acted |= conflict_res.result.acted
                                conflict_resolution = conflict_res
                            else:
                                create_res = self.op_add_property(
                                    item, new_claim, extra_prop_data
                                )
                                re_cycle |= create_res.re_cycle
                                acted |= create_res.acted
                                claimed.append(new_claim)
                    if (
                        not conflict_resolution
                        or not conflict_resolution.skip_qualifier
                    ):
                        extra_prop_data.sort_qualifiers()
                        new_claim = extra_prop_data.claim
                        for (
                            qualifier_prop,
                            qualifiers,
                        ) in extra_prop_data.qualifiers.copy().items():
                            claimed_qualifiers: list[pywikibot.Claim] = []
                            is_replace_and_delete_qualifier = [
                                extra_qual.on_conflict
                                == QualifierResolutionChoice.REPLACE_AND_DELETE
                                for extra_qual in qualifiers
                            ]
                            if any(is_replace_and_delete_qualifier) and not all(
                                is_replace_and_delete_qualifier
                            ):
                                raise ValueError(
                                    "In order to use QualifierResolutionChoice.REPLACE_AND_DELETE, all claims must have it"
                                )
                            for qualifier in qualifiers.copy():
                                if not new_claim.qualifiers.get(qualifier_prop, []):
                                    create_res = self.op_add_qualifier(
                                        item, qualifier, extra_prop_data
                                    )
                                    re_cycle |= create_res.re_cycle
                                    acted |= create_res.acted
                                else:
                                    matched_equal_qualifier = self.match_new_qualifer(
                                        qualifier,
                                        exclude_claims=claimed_qualifiers,
                                        item=item,
                                        main_claim=new_claim,
                                        property=extra_prop_data,
                                    )
                                    matched_more_specific_qualifier = (
                                        self.match_more_specific_qualifier(
                                            qualifier,
                                            exclude_claims=claimed_qualifiers,
                                            item=item,
                                            main_claim=new_claim,
                                            property=extra_prop_data,
                                        )
                                    )
                                    matched_less_specific_qualifier = (
                                        self.match_less_specific_qualifier(
                                            qualifier,
                                            exclude_claims=claimed_qualifiers,
                                            item=item,
                                            main_claim=new_claim,
                                            property=extra_prop_data,
                                        )
                                    )
                                    if matched_equal_qualifier:
                                        claimed_qualifiers.append(
                                            matched_equal_qualifier
                                        )
                                        qualifier.claim = matched_equal_qualifier
                                    elif matched_more_specific_qualifier:
                                        conflict_res = self.handle_qualifier_claim_conflict(
                                            item,
                                            qualifier,
                                            matched_more_specific_qualifier,
                                            qualifier.on_conflict_more_specific_value,
                                            extra_prop_data=extra_prop_data,
                                        )
                                        re_cycle |= conflict_res.result.re_cycle
                                        acted |= conflict_res.result.acted
                                        claimed_qualifiers.extend(
                                            conflict_res.new_claims
                                        )
                                    elif matched_less_specific_qualifier:
                                        conflict_res = self.handle_qualifier_claim_conflict(
                                            item,
                                            qualifier,
                                            matched_less_specific_qualifier,
                                            qualifier.on_conflict_less_specific_value,
                                            extra_prop_data=extra_prop_data,
                                        )
                                        re_cycle |= conflict_res.result.re_cycle
                                        acted |= conflict_res.result.acted
                                        claimed_qualifiers.extend(
                                            conflict_res.new_claims
                                        )
                                    else:
                                        first_conflicting_qualifier = next(
                                            (
                                                claim
                                                for claim in new_claim.qualifiers[
                                                    qualifier.get_property_id()
                                                ]
                                                if claim not in claimed_qualifiers
                                            ),
                                            None,
                                        )
                                        if first_conflicting_qualifier:
                                            conflict_res = (
                                                self.handle_qualifier_claim_conflict(
                                                    item,
                                                    qualifier,
                                                    first_conflicting_qualifier,
                                                    qualifier.on_conflict,
                                                    extra_prop_data=extra_prop_data,
                                                )
                                            )
                                            claimed.extend(conflict_res.new_claims)
                                            extra_prop_data.claim = (
                                                conflict_res.primary_new_claim
                                            )
                                            re_cycle |= conflict_res.result.re_cycle
                                            acted |= conflict_res.result.acted
                                        else:
                                            create_res = self.op_add_qualifier(
                                                item, qualifier, extra_prop_data
                                            )
                                            re_cycle |= create_res.re_cycle
                                            acted |= create_res.acted
                                            claimed.append(new_claim)
                            if any(is_replace_and_delete_qualifier):
                                delete_res = self.op_delete_value(
                                    item,
                                    claimed_qualifiers,
                                    qualifiers,
                                    extra_prop_data=extra_prop_data,
                                )
                                re_cycle |= delete_res.re_cycle
                                acted |= delete_res.acted
                    if not conflict_resolution or conflict_resolution.skip_reference:
                        for extra_reference in extra_prop_data.extra_references.copy():
                            compatible = False
                            new_claim = extra_prop_data.claim
                            for existing_reference in new_claim.getSources().copy():
                                if extra_reference.is_compatible_reference(
                                    existing_reference
                                ) and (
                                    self.whitelisted_claim(extra_prop_data)
                                    or self.whitelisted_reference(
                                        extra_prop_data, extra_reference
                                    )
                                ):
                                    compatible = True
                                    if merge_reference_groups(
                                        existing_reference,
                                        list(
                                            extra_reference.new_reference_props.values()
                                        ),
                                    ):
                                        re_cycle |= self.processed_hook(
                                            item,
                                            ProcessReason.merged_reference,
                                            claim=extra_prop_data,
                                            reference=extra_reference,
                                            context=MergedReferenceContext(
                                                old_reference_group=existing_reference,
                                            ),
                                        )
                                        acted = True
                                    break
                            if not compatible and (
                                self.whitelisted_claim(extra_prop_data)
                                or self.whitelisted_reference(
                                    extra_prop_data, extra_reference
                                )
                            ):
                                re_cycle |= self.processed_hook(
                                    item,
                                    ProcessReason.missing_reference,
                                    claim=extra_prop_data,
                                    reference=extra_reference,
                                )
                                add_reference_locally(
                                    new_claim,
                                    *extra_reference.new_reference_props.values(),
                                )
                                acted = True
                if any(is_replace_and_delete):
                    delete_res = self.op_delete_value(item, claimed, extra_props)
                    re_cycle |= delete_res.re_cycle
                    acted |= delete_res.acted
            second_previous_hash = previous_hash
            previous_hash = hash(dumps(item.toJSON()))
        return acted

    def process(self, output: Output | Sequence[Output], item: EntityPage) -> bool:
        """Processes the output from run_item.

        :param output: The output to process
        :param item: The item to process
        :return: If any edits were made to the item.
        """
        acted = False
        output = self.ensure_output_sequence(output)
        for individual_output in output:
            assert not isinstance(individual_output, str)
            acted |= self.merge_output_with_item(individual_output, item)
        with start_span(
            op="post_output_process", description="Post Output Process Hook"
        ):
            if self.post_output_process_hook(output, item):
                self.processed_hook(item, ProcessReason.post_output)
                if not acted:
                    acted = True
        if acted:
            with start_span(op="pre_edit_process", description="Pre Edit Process Hook"):
                self.pre_edit_process_hook(output, item)
            with start_span(op="edit_entity", description="Edit Entity"):
                retries = 3
                while retries >= 0:
                    with start_span(
                        op="edit_entity_try", description="Edit Entity Attempt"
                    ):
                        try:
                            item.editEntity(
                                summary=self.get_full_summary(
                                    self.get_edit_summary(item)
                                ),
                                bot=True,
                            )
                            break
                        except pywikibot.exceptions.APIError as e:
                            retries -= 1
                            if retries < 0:
                                raise e
            with start_span(
                op="post_edit_process", description="Post Edit Process Hook"
            ):
                self.post_edit_process_hook(output, item)
        return acted

    def act_on_item(self, item: EntityPage) -> bool:
        """Act on an item.

        :param item: The item to act on.
        :return: If any edits were made to the item.
        """
        with new_scope(), start_transaction(op="act_on_item", name="Process Item"):
            with start_span(op="get_output", description="Get Output"):
                output = self.run_item(item)
            with start_span(op="process_output", description="Process Output"):
                return self.process(output, item)

    def feed_items(
        self, items: Iterable[EntityPage], skip_errored_items: bool = False
    ) -> None:
        """Feed items to the bot.

        :param items: The items to feed.
        :param skip_errored_items: If the bot should skip items that errored.
        """
        for item in items:
            try:
                self.act_on_item(item)
            except Exception as e:
                if skip_errored_items:
                    report_exception(e)
                else:
                    raise e
