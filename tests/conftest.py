import os

# Unit tests never call external or paid services (server.py loads .env with setdefault, so blanks here win).
# Live checks run only with LIVE=1 (see tests/test_live.py).
if not os.environ.get("LIVE"):
    for key in ("TENKI_API_KEY", "FLATKEY_API_KEY", "ANTHROPIC_API_KEY", "MASKY_API_KEY"):
        os.environ[key] = ""
    os.environ["NO_LIVE"] = "1"
