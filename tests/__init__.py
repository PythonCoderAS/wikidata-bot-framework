from abc import ABC

import pywikibot
from wikidata_bot_framework import PropertyAdderBot, site


class TestPAB(PropertyAdderBot, ABC):
    def __init__(self, *, simulate: bool):
        super().__init__()
        self.simulate = simulate


sandbox_item = pywikibot.ItemPage(site, "Q4115189")
