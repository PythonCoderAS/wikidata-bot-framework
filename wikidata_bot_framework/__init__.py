from typing import Dict, Iterable, List, Literal, Mapping, Union

import pywikibot

from .dataclasses import ExtraProperty, ExtraQualifier, ExtraReference
from abc import ABC, abstractmethod

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
    def get_edit_summary(self, op: Literal["add", "edit"], main_property: pywikibot.Claim, secondary: Union[ExtraQualifier,
    ExtraReference,None] = None, rank: Literal["normal", "preferred", "deprecated", None] = None) -> str:
        """Get the edit summary for the bot.

        :param op: The operation being performed. One of "add", "edit".
        :param main_property: The main property being edited.
        :param secondary: The secondary property being edited.
        :param rank: The rank of the property being edited, if it's changing.
        :return: The edit summary to use.
        """
        pass

    def _get_full_summary(self, op: Literal["add", "edit"], main_property: pywikibot.Claim, secondary: Union[ExtraQualifier,
    ExtraReference,None] = None, rank: Literal["normal", "preferred", "deprecated", None] = None):
        base = self.get_edit_summary(op, main_property, secondary, rank)
        if edit_group_id := self.get_edit_group_id():
            return f"{base} ([[:toolforge:editgroups/b/CB/{edit_group_id}|details]])"
        return base

    @abstractmethod
    def run_item(self, item: Union[pywikibot.ItemPage, pywikibot.PropertyPage, pywikibot.LexemePage]) -> Output:
        """The main work that should be done externally.

        This method will take an item and return a dictionary of list of ExtraProperties.
        The keys are the property IDs.

        :param item: The item to work on.
        :return: A dictionary of list of ExtraProperties.
        """
        pass

    def logger_hook(self, op: Literal["add", "edit"], main_property: pywikibot.Claim, secondary: Union[ExtraQualifier,
    ExtraReference,None] = None, rank: Literal["normal", "preferred", "deprecated", None] = None) -> None:
        """A hook for logging.

        :param op: The operation being performed. One of "add", "edit".
        :param main_property: The main property being edited.
        :param secondary: The secondary property being edited.
        :param rank: The rank of the property being edited, if it's changing.
        """
        pass

    def can_add_main_property(self, extra_property: ExtraProperty) -> bool:
        """Return if the property can be added or edited"""
        return not extra_property.reference_only

    def process(self, output: Output, item: pywikibot.ItemPage) -> bool:
        """Processes the output from run_item.

        :param output: The output to process
        :return: If any edits were made to the item.
        """
        acted = False
        for property_id, extra_props in output.items():
            for extra_prop_data in extra_props:
                new_claim = extra_prop_data.claim
                if property_id not in item.claims:
                    if self.can_add_main_property(extra_prop_data):
                        item.addClaim(new_claim, summary=self._get_full_summary("add", extra_prop_data.claim))
                        self.logger_hook("add", new_claim)
                        acted = True
                    else:
                        continue
                else:
                    for existing_claim in item.claims[property_id]:
                        existing_claim: pywikibot.Claim
                        if existing_claim.getTarget() == new_claim.getTarget():
                            new_claim = existing_claim
                            if new_claim.getRank() != existing_claim.getRank():
                                existing_claim.changeRank(new_claim.getRank(),
                                summary=self._get_full_summary("edit", existing_claim, rank=new_claim.getRank()),

                                                          bot=True)

        return acted
