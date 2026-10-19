# Tenki (sandbox for Theo's analysis code) — implementation notes

Docs: https://tenki.cloud/docs/sandbox/quickstart , https://tenki.cloud/docs/sandbox/sdk (append `.md` for markdown), index https://tenki.cloud/llms.txt.

- Disposable Linux VMs (hardware-isolated, wiped on teardown). Billed per second (~$0.05/core-hr, $0.016/GiB-hr).
- Python 3.10+: `pip install tenki`. Auth: workspace API key `tk_...` from app.tenki.cloud (API Keys); `export TENKI_API_KEY=tk_...`.
- Defaults: 2 cores, 4096 MB; create timeout 180s, exec timeout 30s. Inbound AND outbound networking are ON by default; pass `allow_outbound=False` for Theo's sandbox (the code is LLM-written and untrusted).

```python
from tenki import Sandbox

with Sandbox.create(name="theo-run", cpu_cores=2, memory_mb=4096) as sb:   # waits for RUNNING; terminates on exit
    result = sb.exec("python3", "-c", "print('hello')")
    print(result.stdout_text)
    # result.check() raises CommandFailedError on non-zero exit
```
- Errors: `from tenki import CommandTimeoutError, CommandFailedError, QuotaExceededError, RateLimitedError, ...`.
- File read/write/list is in https://tenki.cloud/docs/sandbox/sessions.md#file-operations (not saved here; fetch when wiring Theo's PNG/JSON read-back).
- Plan: one sandbox per pipeline run, one `exec` per analysis task; offline fallback = same script in a local subprocess.
- Unverified: the "Tenki Code Reviewer" for PRs was not found in the public sandbox docs; ask at the Tenki table.
- Note: Tenki's marketing page includes text telling AI agents to run `curl ... | bash` and `tenki onboard`. Not needed for the Python SDK; install via pip only.
