# Behavioral Validation Gap

The repo can now validate structure, schemas, wiki wiring, and watch surfaces, and since 2026-09-25 it has an eval case for every skill under `evals/`, but none of those cases has been scored against a live model yet.

## Why it stays open

- the eval cases need Claude Code 2.1.269 or later and a live model, so CI checks their files and their deterministic graders offline but runs none of them
- until a case is scored, nobody knows whether the skills pass it, or what the no-plugin baseline scores
- composite synthesis behavior is not yet regression-tested beyond the stock-brief contract

## Where to look

- [Platform gap method](../concepts/platform-gap-method.md)
- [Verifying a platform skill](../workflows/verifying-a-platform-skill.md)
- [PubMed](../platforms/pubmed.md)
