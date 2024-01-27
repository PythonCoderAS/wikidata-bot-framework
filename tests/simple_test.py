import pytest
import pywikibot
from wikidata_bot_framework import Output
from wikidata_bot_framework.constants import EntityPage, retrieved_prop, site
from wikidata_bot_framework.dataclasses import ExtraProperty
from . import TestPAB, sandbox_item


class SimpleTestBot(TestPAB):
    def get_edit_summary(self, page: EntityPage) -> str:
        return "Testing wikidata-bot-framework"

    def run_item(self, item: EntityPage) -> Output:
        claim = pywikibot.Claim(site, retrieved_prop)
        claim.setTarget(pywikibot.WbTime(year=2021, month=1, day=1))
        return {retrieved_prop: [ExtraProperty(claim)]}

    def post_edit_process_hook(self, output: Output, item: EntityPage) -> None:
        if not self.simulate:
            item.removeClaims(
                output[retrieved_prop][0].claim,
                summary=super().get_full_summary("Removing test claim"),
                bot=True,
            )


def test_simple_test_bot(pytestconfig: pytest.Config):
    bot = SimpleTestBot(simulate=pytestconfig.getoption("--simulate"))
    bot.act_on_item(sandbox_item)
    assert True  # If we get here, it worked
