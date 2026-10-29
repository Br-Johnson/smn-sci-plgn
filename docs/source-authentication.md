# Authenticated source sessions

RMIS, PTAGIS and StreamNet accept credentials only from the user's local process
environment. Never paste a password, API key or token into chat, JSON input,
command arguments or a committed file. Inline credential fields, including query
parameters, are refused. RMIS's legacy `login` action returns
`local_auth_required`; the plugin does not exchange passwords for tokens.

Obtain an authorized credential through the source's approved browser or local
workflow. Then configure it in your own terminal or through your organization's
secret manager. Environment access does not itself grant permission to retrieve
or disclose source data.

| Source | Environment names | Authenticated origin |
| --- | --- | --- |
| RMIS | `RMIS_API_KEY` or `RMPC_API_KEY`; `RMIS_JWT` with `auth_mode: "jwt"` | `https://phish.rmis.org:443` |
| PTAGIS | `PTAGIS_API_TOKEN` or `PTAGIS_API_KEY` | `https://api.ptagis.org:443` |
| StreamNet | `STREAMNET_API_KEY` | `https://api.streamnet.org:443` |

For example, run this yourself in Terminal from the plugin checkout. The hidden
prompt supplies a credential to this one child process; it is not a chat step or
an example for the agent to execute. No credential value is placed in JSON or
command arguments.

```python
import getpass
import json
import os
import subprocess
import sys

source_env = os.environ.copy()
source_env["RMIS_API_KEY"] = getpass.getpass("RMIS API key (hidden): ")
subprocess.run(
    [sys.executable, "skills/rmis-skill/scripts/rmis_api.py"],
    input=json.dumps({"action": "release", "params": "perpage=1"}),
    text=True,
    env=source_env,
    check=True,
)
```

Use the corresponding environment name and script for PTAGIS or StreamNet.
Their skill files list metadata actions. Public actions that do not require
credentials remain available without a local secret.

Authenticated transport requires HTTPS and the adapter's explicit origin
policy. Same-origin HTTPS redirects retain authentication; a different host,
port or scheme is refused before the destination is contacted. A source move
requires a reviewed policy change, not a caller-supplied URL override.

Ordinary responses and `save_raw` JSON redact configured credential values,
common URL encodings and credential-shaped fields such as `token`, `api_key`,
`Authorization` and cookies. Authenticated HTTP error bodies are withheld, and
CLI failures return safe JSON without exception tracebacks. These protections
are credential safeguards, not a disclosure review of research records; source
permissions and permitted data use still apply.

Implementation: `scripts/_source_auth.py`, shared output/file plumbing in
`scripts/_common.py`, and the three source adapters. Verify with
`python3 -m unittest discover -s tests -p 'test_source_credentials.py' -v`.
The fixtures use invented values, fake API responses and local TLS servers.
OpenSSL is required to generate the temporary local server certificate; the
transport tests are reported as skipped if it is unavailable. No live
credential or authentication service is used.
