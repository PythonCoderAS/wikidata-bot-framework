import datetime
import re

import pywikibot

from .constants import (
    archive_date_prop,
    archive_url_prop,
    deprecated_reason_prop,
    link_rot_id,
    site,
)
from .dataclasses import ExtraProperty, ExtraQualifier


def de_archivify_url_property(prop: ExtraProperty, deprecate: bool = True):
    """Converts a :class:`.ExtraProperty` with an archive.org URL to a :class:`.ExtraProperty` with the original URL and some qualifiers."""
    full_url = str(prop.claim.getTarget())
    if match := re.search(r"web.archive.org/web/(\d{14})/", full_url):
        prop.claim.setTarget(full_url.replace(match.group(0), ""))
        if deprecate:
            prop.claim.setRank("deprecated")
        timestamp = datetime.datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        archive_url = pywikibot.Claim(site, archive_url_prop)
        archive_url.setTarget(full_url)
        prop.qualifiers[archive_url_prop].append(
            ExtraQualifier(archive_url, skip_if_conflicting_exists=True)
        )
        archive_date = pywikibot.Claim(site, archive_date_prop)
        archive_date.setTarget(
            pywikibot.WbTime(
                year=timestamp.year, month=timestamp.month, day=timestamp.day
            )
        )
        prop.qualifiers[archive_date_prop].append(
            ExtraQualifier(archive_date, skip_if_conflicting_exists=True)
        )
        deprecated_reason = pywikibot.Claim(site, deprecated_reason_prop)
        deprecated_reason.setTarget(pywikibot.ItemPage(site, link_rot_id))
        prop.qualifiers[deprecated_reason_prop].append(
            ExtraQualifier(deprecated_reason, skip_if_conflicting_exists=True)
        )
