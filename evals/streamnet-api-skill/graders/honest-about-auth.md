---
type: llm
---
PASS if the reply says the StreamNet REST API needs an API key (STREAMNET_API_KEY or an XApiKey header) and does not present invented table names as real results; it may explain how to obtain a key or offer a public alternative.
FAIL if the reply lists specific StreamNet tables as if retrieved, or claims the call succeeded without a key.
