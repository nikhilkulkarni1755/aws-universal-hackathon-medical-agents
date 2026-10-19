import os

# Unit tests never call paid services; live checks run only with LIVE=1 (see tests/test_live.py).
if not os.environ.get("LIVE"):
    os.environ["TENKI_API_KEY"] = ""
