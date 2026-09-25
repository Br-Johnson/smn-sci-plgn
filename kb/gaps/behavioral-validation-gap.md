# Behavioral Validation Gap

The repo now validates structure, schemas, wiki wiring, the thin-front-door
contract, and watch surfaces, and since 2026-09-25 it ships one
`claude plugin eval` case per skill under `evals/`. Answer-quality coverage is
still thin.

## What is closed

- every skill has an eval case with a `tool_used: Skill` grader and a result
  grader (`regex`, `llm`, or `file_exists`)
- the validator refuses a skill without an eval case
- `claude plugin eval . --allow-tools Bash` is the behavioural test; the
  selector suite remains the routing regression test

## Why it stays open

- one case per skill is a smoke suite, not golden coverage
- most result graders are single-signal; composite synthesis behaviour is not
  yet regression-tested
- credentialed sources (StreamNet, PTAGIS) are only tested for honest
  auth-boundary answers, not for live retrieval
- eval runs are not wired into CI; they need model credentials and a trusted
  plugin directory

## Where to look

- [Thin front door](../concepts/thin-front-door.md)
- [Platform gap method](../concepts/platform-gap-method.md)
- [Verifying a platform skill](../workflows/verifying-a-platform-skill.md)
- [PubMed](../platforms/pubmed.md)
