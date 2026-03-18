from collections import defaultdict
import sys

mylang = "wikidata"
family = "wikidata"
usernames: defaultdict[str, defaultdict[str, str]] = defaultdict(defaultdict)

simulate = "--simulate" in sys.argv

put_throttle = 1

del defaultdict
