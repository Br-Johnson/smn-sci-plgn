# Handing the Review to the User

After the last ingest, the verdicts are recorded in
`review/semantic-llm-assessments.csv` and sit on the package's suggestions.
Nothing is in the metadata yet. The user confirms each term, and that is the
step that writes it.

## What to tell the user

Lead with what needs them:

- the terms you accepted, each with its label, IRI and the reason it fits;
- the slots you left for review, with what evidence would settle each;
- the new terms you asked for, including rejected shortlists the package
  escalated, with the label you proposed and the namespace, if you named one;
- any accept the package turned into `review`, with the finding it named; and
- any slot recorded as an error, and why.

Then give them the calls below. The review console prints, under each
candidate, the exact `accept_suggestion()` call that decides it, so the user
pastes calls rather than writing them.

## Python

```python
from metasalmonpy import (
    accept_suggestion, apply_sdp_semantics, reject_suggestion,
    review_metadata, review_semantics, validate_salmon_datapackage,
)

review = review_semantics("path/to/sdp")
print(review)  # each slot, its candidates, your verdict, and the call that decides it
review = accept_suggestion(review, "CATCH_COUNT", "variable", rank=1)  # pasted from the console
review = reject_suggestion(review, "CATCH_COUNT", "constraint", reason="No qualifier applies.")
apply_sdp_semantics("path/to/sdp", review)
print(review_metadata("path/to/sdp"))  # whatever still blocks strict validation
validate_salmon_datapackage("path/to/sdp", require_iris=True)
```

## R

```r
library(metasalmon)
review <- review_semantics("path/to/sdp")
review
review <- accept_suggestion(review, "CATCH_COUNT", "variable", rank = 1)
review <- reject_suggestion(review, "CATCH_COUNT", "constraint", reason = "No qualifier applies.")
apply_sdp_semantics("path/to/sdp", review)
review_metadata("path/to/sdp")
validate_salmon_datapackage("path/to/sdp", require_iris = TRUE)
```

A clean `validate_salmon_datapackage(require_iris = TRUE)` is the bar for
calling the package ready to publish.

## New terms

The `request_new_term` outcomes are ontology gaps. The package drafts the term
requests; filing them opens GitHub issues in an ontology repository, so leave
that to the user, after they have read the drafts.

```python
from metasalmonpy import (
    detect_semantic_term_gaps, render_ontology_term_request,
    semantic_suggestions, submit_term_request_issues,
)

gaps = detect_semantic_term_gaps(suggestions=semantic_suggestions("path/to/sdp"))
requests = render_ontology_term_request(gaps, ask=False)
submit_term_request_issues(requests, dry_run=True)  # a preview; nothing is filed
```

In R, the same three functions take the same arguments:
`detect_semantic_term_gaps(suggestions = semantic_suggestions("path/to/sdp"))`.
