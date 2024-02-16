from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass, field
from json import dumps
from typing import Any, Iterable, List, Literal, Mapping, Optional, Union, overload

import pywikibot
from sentry_sdk import push_scope

# Make all imports from submodules available here

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
    ExtraReference,  # noqa: F401
)
from .process_reason import (
    ProcessReason,  # noqa: F401
    DifferentRankContext,  # noqa: F401
    ReplaceValueContext,  # noqa: F401
    DeleteValuesContext,  # noqa: F401
    ReplaceQualifierValueContext,  # noqa: F401
    DeleteQualifierValuesContext,  # noqa: F401
    NewClaimFromQualifierContext,  # noqa: F401
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
    ) -> Output:
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

    def post_output_process_hook(self, output: Output, item: EntityPage) -> bool:
        """Do additional processing after all output has been processed.

        :param output: The output that was processed.
        :param item: The item that was edited.
        :return: Return whether or not the item was changed. This will be used
            to determine if an API request should be made.
        """
        return False

    def pre_edit_process_hook(self, output: Output, item: EntityPage) -> None:
        """Do additional processing before the item is edited.

        This hook only fires if an API request will be made.

        :param output: The output that was processed.
        :param item: The item that will be edited.
        """

    def post_edit_process_hook(self, output: Output, item: EntityPage) -> None:
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

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.missing_property, ProcessReason.missing_value],
        *,
        claim: ExtraProperty,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.different_rank],
        *,
        claim: ExtraProperty,
        context: DifferentRankContext,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.replace_value],
        *,
        claim: ExtraProperty,
        context: ReplaceValueContext,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.delete_values],
        *,
        claim: ExtraProperty,
        context: DeleteValuesContext,
    ) -> bool:
        ...

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
    ):
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.replace_qualifier_value],
        *,
        claim: ExtraProperty,
        qualifier: ExtraQualifier,
        context: ReplaceQualifierValueContext,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.delete_qualifier_values],
        *,
        claim: ExtraProperty,
        qualifier: ExtraQualifier,
        context: DeleteQualifierValuesContext,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.new_claim_from_qualifier],
        *,
        claim: ExtraProperty,
        qualifier: ExtraQualifier,
        context: NewClaimFromQualifierContext,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.missing_reference],
        *,
        claim: ExtraProperty,
        reference: ExtraReference,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.merged_reference],
        *,
        claim: ExtraProperty,
        reference: ExtraReference,
        context: MergedReferenceContext,
    ) -> bool:
        ...

    @overload
    def processed_hook(
        self,
        item: EntityPage,
        reason: Literal[ProcessReason.post_output],
    ) -> bool:
        ...

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

    def process(self, output: Output, item: EntityPage) -> bool:
        """Processes the output from run_item.

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
                for extra_prop_data in extra_props.copy():
                    new_claim = original_claim = extra_prop_data.claim
                    if new_claim.type == "url" and self.config.auto_dearchivify_urls:
                        de_archivify_url_property(
                            extra_prop_data,
                            deprecate=self.config.auto_deprecate_archified_urls,
                        )
                    if property_id not in item.claims:
                        if self.can_add_main_property(
                            extra_prop_data
                        ) and self.whitelisted_claim(extra_prop_data):
                            # This is triggered if there are no statements for the property
                            add_claim_locally(item, new_claim)
                            re_cycle |= self.processed_hook(
                                item,
                                reason=ProcessReason.missing_property,
                                claim=extra_prop_data,
                            )
                            acted = True
                        else:
                            continue
                    else:
                        for existing_claim in item.claims[property_id].copy():
                            assert isinstance(existing_claim, pywikibot.Claim)
                            if self.same_main_property(existing_claim, new_claim, item):
                                # This is triggered if there is a statement for the property exactly matching the one we want to add
                                if new_claim.getRank() != existing_claim.getRank():
                                    if (
                                        self.whitelisted_claim(extra_prop_data)
                                        or self.config.copy_ranks_for_nonwhitelisted_main_properties
                                    ):
                                        old_rank = existing_claim.getRank()
                                        existing_claim.rank = new_claim.getRank()
                                        re_cycle |= self.processed_hook(
                                            item,
                                            ProcessReason.different_rank,
                                            claim=extra_prop_data,
                                            context=DifferentRankContext(
                                                existing_claim=existing_claim,
                                                old_rank=old_rank,
                                            ),
                                        )
                                        acted = True
                                new_claim = extra_prop_data.claim = existing_claim
                                break
                            else:
                                if (
                                    extra_prop_data.replace_if_conflicting_exists
                                    and self.whitelisted_claim(extra_prop_data)
                                ):
                                    # This is triggered if `extra_prop_data.replace_if_conflicting_exists` is set to True
                                    # and this is the first statement with the property that is not exactly matching the one we want to add
                                    old_value = existing_claim.getTarget()
                                    existing_claim.setTarget(new_claim.getTarget())
                                    if new_claim.getRank() != existing_claim.getRank():
                                        old_rank = existing_claim.getRank()
                                        existing_claim.rank = new_claim.getRank()
                                        re_cycle |= self.processed_hook(
                                            item,
                                            ProcessReason.different_rank,
                                            claim=extra_prop_data,
                                            context=DifferentRankContext(
                                                existing_claim=existing_claim,
                                                old_rank=old_rank,
                                            ),
                                        )
                                    original_new_claim = new_claim
                                    new_claim = extra_prop_data.claim = existing_claim
                                    re_cycle |= self.processed_hook(
                                        item,
                                        ProcessReason.replace_value,
                                        claim=extra_prop_data,
                                        context=ReplaceValueContext(
                                            existing_claim=existing_claim,
                                            new_claim=original_new_claim,
                                            old_value=old_value,
                                        ),
                                    )
                                    if (
                                        len(item.claims[property_id]) > 1
                                        and extra_prop_data.delete_other_if_replacing
                                    ):
                                        deleted = item.claims[property_id].copy()
                                        deleted.remove(new_claim)
                                        re_cycle |= self.processed_hook(
                                            item,
                                            ProcessReason.delete_values,
                                            claim=extra_prop_data,
                                            context=DeleteValuesContext(
                                                deleted_claims=deleted
                                            ),
                                        )
                                        item.claims[property_id] = [new_claim]
                                    acted = True
                                    break
                        else:
                            # This code section triggers if there are statements for the property but none of them match the one we want to add
                            # and we did not opt for replacement.
                            if (
                                extra_prop_data.skip_if_conflicting_language_exists
                                and property_id in item.claims
                            ):  # type: ignore
                                found_conflicting_language = False
                                for existing_claim in item.claims[property_id]:
                                    assert isinstance(existing_claim, pywikibot.Claim)
                                    if isinstance(
                                        existing_claim.getTarget(),
                                        pywikibot.WbMonolingualText,
                                    ):
                                        lang_target: pywikibot.WbMonolingualText = (
                                            existing_claim.getTarget()
                                        )  # type: ignore
                                        if (
                                            lang_target.language
                                            == new_claim.getTarget().language  # type: ignore
                                            and lang_target != new_claim.getTarget()
                                        ):  # type: ignore
                                            found_conflicting_language = True
                                            break
                                    else:
                                        # The existing claim is not a monolingual text, so we can't compare it to the new one
                                        continue
                                else:
                                    # If we're here, we did not find a conflicting language
                                    if self.can_add_main_property(
                                        extra_prop_data
                                    ) and self.whitelisted_claim(extra_prop_data):
                                        re_cycle |= self.processed_hook(
                                            item,
                                            ProcessReason.missing_value,
                                            claim=extra_prop_data,
                                        )
                                        add_claim_locally(item, new_claim)
                                        acted = True
                                    else:
                                        continue
                                if found_conflicting_language:
                                    continue
                            elif extra_prop_data.skip_if_conflicting_exists:
                                continue
                            if self.can_add_main_property(
                                extra_prop_data
                            ) and self.whitelisted_claim(extra_prop_data):
                                add_claim_locally(item, new_claim)
                                re_cycle |= self.processed_hook(
                                    item,
                                    ProcessReason.missing_value,
                                    claim=extra_prop_data,
                                )
                                acted = True
                            else:
                                continue
                    extra_prop_data.sort_qualifiers()
                    added_qualifiers = []
                    for (
                        qualifier_prop,
                        qualifiers,
                    ) in extra_prop_data.qualifiers.copy().items():
                        for qualifier_data in qualifiers.copy():
                            qualifier = qualifier_data.claim
                            if not new_claim.qualifiers.get(qualifier_prop, []) and (
                                self.whitelisted_claim(extra_prop_data)
                                or self.whitelisted_qualifier(
                                    extra_prop_data, qualifier_data
                                )
                            ):
                                add_qualifier_locally(new_claim, qualifier)
                                added_qualifiers.append(qualifier)
                                re_cycle |= self.processed_hook(
                                    item,
                                    ProcessReason.missing_qualifier_property,
                                    claim=extra_prop_data,
                                    qualifier=qualifier_data,
                                )
                                acted = True
                            else:
                                for existing_qualifier in new_claim.qualifiers[
                                    qualifier_prop
                                ].copy():
                                    if self.same_qualifier(
                                        existing_qualifier, qualifier, new_claim, item
                                    ):
                                        break
                                    else:
                                        if (
                                            qualifier_data.replace_if_conflicting_exists
                                            and (
                                                self.whitelisted_claim(extra_prop_data)
                                                or self.whitelisted_qualifier(
                                                    extra_prop_data, qualifier_data
                                                )
                                            )
                                        ):
                                            old_value = existing_qualifier.getTarget()
                                            existing_qualifier.setTarget(
                                                qualifier.getTarget()
                                            )
                                            re_cycle |= self.processed_hook(
                                                item,
                                                ProcessReason.replace_qualifier_value,
                                                claim=extra_prop_data,
                                                qualifier=qualifier_data,
                                                context=ReplaceQualifierValueContext(
                                                    existing_qualifier=existing_qualifier,
                                                    new_qualifier=qualifier,
                                                    old_value=old_value,
                                                ),
                                            )
                                            qualifier = (
                                                qualifier_data.claim
                                            ) = existing_qualifier
                                            if (
                                                len(
                                                    new_claim.qualifiers[qualifier_prop]
                                                )
                                                > 1
                                                and qualifier_data.delete_other_if_replacing
                                            ):
                                                deleted = new_claim.qualifiers[
                                                    qualifier_prop
                                                ].copy()
                                                deleted.remove(qualifier)
                                                re_cycle |= self.processed_hook(
                                                    item,
                                                    ProcessReason.delete_qualifier_values,
                                                    claim=extra_prop_data,
                                                    qualifier=qualifier_data,
                                                    context=DeleteQualifierValuesContext(
                                                        deleted_qualifiers=deleted
                                                    ),
                                                )
                                                new_claim.qualifiers[qualifier_prop] = [
                                                    qualifier
                                                ]
                                            acted = True
                                            break
                                else:
                                    made_new_claim = False
                                    if qualifier_data.skip_if_conflicting_exists:
                                        continue
                                    elif (
                                        qualifier_data.make_new_if_conflicting
                                        and self.whitelisted_claim(extra_prop_data)
                                    ):
                                        if self.can_add_main_property(extra_prop_data):
                                            old_claim = new_claim
                                            new_claim = (
                                                extra_prop_data.claim
                                            ) = original_claim
                                            add_claim_locally(item, new_claim)
                                            for qualifier in added_qualifiers:
                                                add_qualifier_locally(
                                                    new_claim, qualifier
                                                )
                                            remove_qualifiers(
                                                old_claim, added_qualifiers
                                            )
                                            added_qualifiers = []
                                            re_cycle |= self.processed_hook(
                                                item,
                                                ProcessReason.new_claim_from_qualifier,
                                                claim=extra_prop_data,
                                                qualifier=qualifier_data,
                                                context=NewClaimFromQualifierContext(
                                                    old_claim=old_claim
                                                ),
                                            )
                                            acted = True
                                            made_new_claim = True
                                        else:
                                            continue
                                    add_qualifier_locally(new_claim, qualifier)
                                    added_qualifiers.append(qualifier)
                                    if not made_new_claim:
                                        re_cycle |= self.processed_hook(
                                            item,
                                            ProcessReason.missing_qualifier_value,
                                            claim=extra_prop_data,
                                            qualifier=qualifier_data,
                                        )
                                    acted = True
                    for extra_reference in extra_prop_data.extra_references.copy():
                        compatible = False
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
                                    list(extra_reference.new_reference_props.values()),
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
                                new_claim, *extra_reference.new_reference_props.values()
                            )
                            acted = True
            second_previous_hash = previous_hash
            previous_hash = hash(dumps(item.toJSON()))
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
        with push_scope(), start_transaction(op="act_on_item", name="Process Item"):
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
