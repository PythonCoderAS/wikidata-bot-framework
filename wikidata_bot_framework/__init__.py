from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Union

import pywikibot

from .constants import *
from .dataclasses import *
from .sentry import *
from .transformers import *
from .utils import *

Output = Mapping[str, List[ExtraProperty]]


@dataclass(frozen=True, kw_only=True)
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


class PropertyAdderBot(ABC):
    """A bot that adds properties to pages.

    Supports merging existing properties with the internal representation.
    """

    def __init__(self):
        load_sentry()
        self.config = Config()

    def set_config(self, config: Config):
        self.config = config

    @abstractmethod
    def get_edit_group_id(self) -> Union[str, None]:
        """Get the edit group ID for the bot.

        This is used to identify the bot in the edit summary.
        """
        pass

    @abstractmethod
    def get_edit_summary(self, page: EntityPage) -> str:
        """Get the edit summary for the bot.

        :param page: The item page that was edited.
        :return: The edit summary to use.
        """
        pass

    def _get_full_summary(self, page: EntityPage):
        base = self.get_edit_summary(page)
        if edit_group_id := self.get_edit_group_id():
            return f"{base} ([[:toolforge:editgroups/b/CB/{edit_group_id}|details]])"
        return base

    @abstractmethod
    def run_item(
        self,
        item: EntityPage,
    ) -> Output:
        """The main work that should be done externally.

        This method will take an item and return a dictionary of list of ExtraProperties.
        The keys are the property IDs.

        :param item: The item to work on.
        :return: A dictionary of list of ExtraProperties.
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
            if (
                reference.claim.getID()
                in self.config.create_or_edit_references_for_main_property_whitelist
            ):
                return True
            return False
        return True

    def process(self, output: Output, item: EntityPage) -> bool:
        """Processes the output from run_item.

        :param output: The output to process
        :param item: The item to process
        :return: If any edits were made to the item.
        """
        acted = False
        for property_id, extra_props in output.items():
            for extra_prop_data in extra_props:
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
                        add_claim_locally(item, new_claim)
                        acted = True
                    else:
                        continue
                else:
                    for existing_claim in item.claims[property_id].copy():
                        existing_claim: pywikibot.Claim
                        if self.same_main_property(existing_claim, new_claim, item):
                            if new_claim.getRank() != existing_claim.getRank():
                                if (
                                    self.whitelisted_claim(extra_prop_data)
                                    or self.config.copy_ranks_for_nonwhitelisted_main_properties
                                ):
                                    existing_claim.rank = new_claim.getRank()
                                    acted = True
                            new_claim = extra_prop_data.claim = existing_claim
                            break
                        else:
                            if (
                                extra_prop_data.replace_if_conflicting_exists
                                and self.whitelisted_claim(extra_prop_data)
                            ):
                                existing_claim.setTarget(new_claim.getTarget())
                                if new_claim.getRank() != existing_claim.getRank():
                                    new_claim.rank = existing_claim.getRank()
                                new_claim = extra_prop_data.claim = existing_claim
                                if (
                                    len(item.claims[property_id]) > 1
                                    and extra_prop_data.delete_other_if_replacing
                                ):
                                    item.claims[property_id] = [new_claim]
                                acted = True
                                break
                    else:
                        if extra_prop_data.skip_if_conflicting_language_exists and property_id in item.claims:  # type: ignore
                            for existing_claim in item.claims[property_id]:  # type: ignore
                                existing_claim: pywikibot.Claim
                                if isinstance(
                                    existing_claim.getTarget(),
                                    pywikibot.WbMonolingualText,
                                ):
                                    lang_target: pywikibot.WbMonolingualText = existing_claim.getTarget()  # type: ignore
                                    if lang_target.language == new_claim.getTarget().language:  # type: ignore
                                        break
                                else:
                                    continue
                            else:
                                if self.can_add_main_property(
                                    extra_prop_data
                                ) and self.whitelisted_claim(extra_prop_data):
                                    add_claim_locally(item, new_claim)
                                    acted = True
                                else:
                                    continue
                        elif extra_prop_data.skip_if_conflicting_exists:
                            continue
                        if self.can_add_main_property(
                            extra_prop_data
                        ) and self.whitelisted_claim(extra_prop_data):
                            add_claim_locally(item, new_claim)
                            acted = True
                        else:
                            continue
                for qualifier_prop, qualifiers in extra_prop_data.qualifiers.items():
                    for qualifier_data in qualifiers:
                        qualifier = qualifier_data.claim
                        if qualifier not in new_claim.qualifiers.get(
                            qualifier_prop, []
                        ) and (
                            self.whitelisted_claim(extra_prop_data)
                            or self.whitelisted_qualifier(extra_prop_data, qualifier)
                        ):
                            add_qualifier_locally(new_claim, qualifier)
                            acted = True
                        else:
                            for existing_qualifier in new_claim.qualifiers[
                                qualifier_prop
                            ]:
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
                                                extra_prop_data, qualifier
                                            )
                                        )
                                    ):
                                        existing_qualifier.setTarget(
                                            qualifier.getTarget()
                                        )
                                        qualifier = existing_qualifier
                                        if (
                                            len(new_claim.qualifiers[qualifier_prop])
                                            > 1
                                            and qualifier_data.delete_other_if_replacing
                                        ):
                                            new_claim.qualifiers[qualifier_prop] = [
                                                qualifier
                                            ]
                                        acted = True
                                        break
                            else:
                                if qualifier_data.skip_if_conflicting_exists:
                                    continue
                                elif (
                                    qualifier_data.make_new_if_conflicting
                                    and self.whitelisted_claim(extra_prop_data)
                                ):
                                    if self.can_add_main_property(extra_prop_data):
                                        new_claim = (
                                            extra_prop_data.claim
                                        ) = original_claim
                                        add_claim_locally(item, new_claim)
                                        acted = True
                                    else:
                                        continue
                                add_qualifier_locally(new_claim, qualifier)
                                acted = True
                for extra_reference in extra_prop_data.extra_references:
                    compatible = False
                    for existing_reference in new_claim.getSources():
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
                                acted = True
                            break
                    if not compatible and (
                        self.whitelisted_claim(extra_prop_data)
                        or self.whitelisted_reference(extra_prop_data, extra_reference)
                    ):
                        add_reference_locally(
                            new_claim, *extra_reference.new_reference_props.values()
                        )
                        acted = True
        with start_span(
            op="post_output_process", description="Post Output Process Hook"
        ):
            if self.post_output_process_hook(output, item) and not acted:
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
                                summary=self._get_full_summary(item),
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
        with start_transaction(op="act_on_item", name="Process Item"):
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
