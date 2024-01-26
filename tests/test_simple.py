import pywikibot
from wikidata_bot_framework import Output, PropertyAdderBot
from wikidata_bot_framework.constants import EntityPage, retrieved_prop, site
from wikidata_bot_framework.dataclasses import ExtraProperty


class SimpleTestBot(PropertyAdderBot):
    def get_edit_summary(self, page: EntityPage) -> str:
        return "Testing wikidata-bot-framework"

    def run_item(self, item: EntityPage) -> Output:
        claim = pywikibot.Claim(site, retrieved_prop)
        claim.setTarget(pywikibot.WbTime(year=2021, month=1, day=1))
        return {retrieved_prop: [ExtraProperty(claim)]}

    def post_edit_process_hook(self, output: Output, item: EntityPage) -> None:
        item.removeClaims(
            output[retrieved_prop][0].claim,
            summary=super().get_full_summary("Removing test claim"),
            bot=True,
        )


def test_simple_test_bot():
    bot = SimpleTestBot()
    bot.act_on_item(pywikibot.ItemPage(site, "Q4115189"))
