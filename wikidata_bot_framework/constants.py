from typing import Union

import pywikibot
from requests import Session

session = Session()

url_prop = "P854"
retrieved_prop = "P813"
archive_url_prop = "P1065"
archive_date_prop = "P2960"
deprecated_reason_prop = "P2241"
link_rot_id = "Q1193907"
site = pywikibot.Site("wikidata", "wikidata")

EntityPage = Union[pywikibot.ItemPage, pywikibot.PropertyPage, pywikibot.LexemePage]
