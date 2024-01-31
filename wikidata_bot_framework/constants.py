from typing import Union

import pywikibot
from pywikibot.site import DataSite
from requests import Session
from requests.adapters import HTTPAdapter, Retry

session = Session()
_retry = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    respect_retry_after_header=True,
)
session.mount("https://", HTTPAdapter(max_retries=_retry))
session.mount("http://", HTTPAdapter(max_retries=_retry))

url_prop = "P854"
retrieved_prop = "P813"
archive_url_prop = "P1065"
archive_date_prop = "P2960"
deprecated_reason_prop = "P2241"
link_rot_id = "Q1193907"
preferred_rank_reason_prop = "P7452"

site: DataSite = pywikibot.Site("wikidata", "wikidata")  # type: ignore

EntityPage = Union[pywikibot.ItemPage, pywikibot.PropertyPage, pywikibot.LexemePage]
