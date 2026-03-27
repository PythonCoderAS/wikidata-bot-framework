from wikidata_bot_framework import Output
from wikidata_bot_framework.constants import EntityPage
from . import TestPAB, sandbox_item


class CycleTestBot(TestPAB):
    def get_edit_summary(self, page: EntityPage) -> str:
        return ""

    def run_item(self, item: EntityPage) -> Output:
        return {}

    def processed_hook(self, *_, **__):
        return True


def test_cycle():
    bot = CycleTestBot()
    bot.act_on_item(sandbox_item)
    assert True
