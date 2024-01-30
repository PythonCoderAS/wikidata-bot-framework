from collections import defaultdict
import sys

mylang = "wikidata"
family = "wikidata"
usernames: defaultdict[str, defaultdict[str, str]] = defaultdict(defaultdict)

usernames[family][mylang] = "RPI2026F1Bot"

simulate = "--simulate" in sys.argv

password_file = "user-password.py"

put_throttle = 1

del defaultdict
