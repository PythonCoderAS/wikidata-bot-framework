from typing import Union
import pywikibot
from requests import Session

session = Session()

url_prop = "P854"
retrieved_prop = "P813"
site = pywikibot.Site("wikidata", "wikidata")

EntityPage = Union[pywikibot.ItemPage, pywikibot.PropertyPage, pywikibot.LexemePage]
