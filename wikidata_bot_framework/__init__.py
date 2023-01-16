from abc import ABC, abstractmethod
from typing import Iterable, List, Mapping, Union

import pywikibot

from .constants import *
from .dataclasses import ExtraProperty, ExtraQualifier, ExtraReference
from .utils import *

Output = Mapping[str, List[ExtraProperty]]


class PropertyAdderBot(ABC):
    """A bot that adds properties to pages.

    Supports merging existing properties with the internal representation.
    """

    @abstractmethod
    def get_edit_group_id(self) -> Union[str, None]:
        """Get the edit group ID for the bot.

        This is used to identify the bot in the edit summary.
        """
        pass

    @abstractmethod
    def get_edit_summary(self, page: pywikibot.ItemPage) -> str:
        """Get the edit summary for the bot.

        :param page: The item page that was edited.
        :return: The edit summary to use.
        """
        pass

    def _get_full_summary(self, page: pywikibot.ItemPage):
        base = self.get_edit_summary(page)
        if edit_group_id := self.get_edit_group_id():
            return f"{base} ([[:toolforge:editgroups/b/CB/{edit_group_id}|details]])"
        return base

    @abstractmethod
    def run_item(
        self,
        item: Union[pywikibot.ItemPage, pywikibot.PropertyPage, pywikibot.LexemePage],
    ) -> Output:
        """The main work that should be done externally.

        This method will take an item and return a dictionary of list of ExtraProperties.
        The keys are the property IDs.

        :param item: The item to work on.
        :return: A dictionary of list of ExtraProperties.
        """
        pass

    def logger_hook(self, page: pywikibot.ItemPage) -> None:
        """A hook for logging.

        :param page: The item page that was edited.
        """
        pass

    def can_add_main_property(self, extra_property: ExtraProperty) -> bool:
        """Return if the property can be added or edited"""
        return not extra_property.reference_only

    def same_main_property(
        self, existing_claim: pywikibot.Claim, new_claim: pywikibot.Claim
    ) -> bool:
        """Return if the main property is the same.

        :param existing_claim: The existing claim to compare to.
        :param new_claim: The new claim to compare to.
        :return: If the main property is the same.
        """
        return existing_claim.getTarget() == new_claim.getTarget()

    def same_qualifier(
        self, existing_qualifier: pywikibot.Claim, new_qualifier: pywikibot.Claim
    ) -> bool:
        """Return if the qualifier is the same.

        :param existing_qualifier: The existing qualifier to compare to.
        :param new_qualifier: The new qualifier to compare to.
        :return: If the qualifier is the same.
        """
        return existing_qualifier.getTarget() == new_qualifier.getTarget()

    def process(self, output: Output, item: pywikibot.ItemPage) -> bool:
        """Processes the output from run_item.

        :param output: The output to process
        :return: If any edits were made to the item.
        """
        acted = False
        for property_id, extra_props in output.items():
            for extra_prop_data in extra_props:
                new_claim = original_claim = extra_prop_data.claim
                if property_id not in item.claims:
                    if self.can_add_main_property(extra_prop_data):
                        add_claim_locally(item, new_claim)
                        acted = True
                    else:
                        continue
                else:
                    for existing_claim in item.claims[property_id].copy():
                        existing_claim: pywikibot.Claim
                        if self.same_main_property(existing_claim, new_claim):
                            new_claim = existing_claim
                            if new_claim.getRank() != existing_claim.getRank():
                                new_claim.rank = existing_claim.getRank()
                                acted = True
                            break
                        else:
                            if extra_prop_data.replace_if_conflicting_exists:
                                existing_claim.setTarget(new_claim.getTarget())
                                if new_claim.getRank() != existing_claim.getRank():
                                    new_claim.rank = existing_claim.getRank()
                                new_claim = existing_claim
                                if (
                                    len(item.claims[property_id]) > 1
                                    and extra_prop_data.delete_other_if_replacing
                                ):
                                    item.claims[property_id] = [new_claim]
                                acted = True
                                break
                    else:
                        if extra_prop_data.skip_if_conflicting_language_exists and prop in item.claims:  # type: ignore
                            for existing_claim in item.claims[prop]:  # type: ignore
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
                                if self.can_add_main_property(extra_prop_data):
                                    add_claim_locally(item, new_claim)
                                    acted = True
                                else:
                                    continue
                        elif extra_prop_data.skip_if_conflicting_exists:
                            continue
                        if self.can_add_main_property(extra_prop_data):
                            add_claim_locally(item, new_claim)
                            acted = True
                        else:
                            continue
                for qualifier_prop, qualifiers in extra_prop_data.qualifiers.items():
                    for qualifier_data in qualifiers:
                        qualifier = qualifier_data.claim
                        if qualifier not in new_claim.qualifiers.get(
                            qualifier_prop, []
                        ):
                            add_qualifier_locally(new_claim, qualifier)
                            acted = True
                        else:
                            for existing_qualifier in new_claim.qualifiers[
                                qualifier_prop
                            ]:
                                if self.same_qualifier(existing_qualifier, qualifier):
                                    break
                                else:
                                    if qualifier_data.replace_if_conflicting_exists:
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
                                elif qualifier_data.make_new_if_conflicting:
                                    if self.can_add_main_property(extra_prop_data):
                                        new_claim = original_claim
                                        add_claim_locally(item, new_claim)
                                        acted = True
                                    else:
                                        continue
                                add_qualifier_locally(new_claim, qualifier)
                                acted = True
                for extra_reference in extra_prop_data.extra_references:
                    compatible = False
                    for existing_reference in new_claim.getSources():
                        if extra_reference.is_compatible_reference(existing_reference):
                            compatible = True
                            if merge_reference_groups(
                                existing_reference,
                                list(extra_reference.new_reference_props.values()),
                            ):
                                acted = True
                            break
                    if not compatible:
                        add_reference_locally(
                            new_claim, *extra_reference.new_reference_props.values()
                        )
                        acted = True
        if acted:
            item.editEntity(
                summary=self._get_full_summary(item),
                bot=True,
            )
        return acted

    def act_on_item(self, item: pywikibot.ItemPage) -> bool:
        """Act on an item.

        :param item: The item to act on.
        :return: If any edits were made to the item.
        """
        return self.process(self.run_item(item), item)

    def feed_items(self, items: Iterable[pywikibot.ItemPage]) -> None:
        """Feed items to the bot.

        :param items: The items to feed.
        """
        for item in items:
            self.act_on_item(item)
