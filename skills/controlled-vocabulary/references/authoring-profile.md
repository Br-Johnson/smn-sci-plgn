# Local authoring profile

The helper is a small CSV-authoritative SKOS writer. It has no term-search,
ranking, RDF import, mapping approval or general ontology editor. Keep identifiers
and definitions in the authoring files; generated files are disposable outputs,
except immutable release snapshots which must remain in version history.

## Metadata

`vocabulary.json` requires `slug`, `title`, `description`, `version`, `issued`,
`language`, `license`, `publisher`, `github_owner`, `github_repo`, and a nonempty
`maintainers` list. Every maintainer has a `name`, `github` username and `email`.
`example` is an optional boolean. `init --demo` writes a complete fictional
example for inspection; `init --config <json>` creates a real project's blank
CSV and portable tool. It does not create a repository.

- `slug`: one lowercase W3ID namespace candidate, starting with a letter and
  containing letters, digits and hyphens. A local collision check is bounded to
  the supplied checkout; refresh it before submission.
- `version`: three-part semantic version, optionally with a prerelease suffix.
- `issued`: an explicit valid calendar date in `YYYY-MM-DD` form for this
  declared edition, not proof that it has been published. Compact and week-date
  inputs are rejected so the emitted `xsd:date` retains a valid lexical form.
- `language`: a BCP47-shaped language tag, such as `en` or `fr-CA`.
- `license`: the chosen license IRI. The user must have the rights it describes.
- `github_owner` / `github_repo`: the expected repository binding. The starter
  derives `https://<owner>.github.io/<repository>/`; custom domains require an
  explicit adaptation and separate DNS/Pages configuration.

## Concepts

The CSV header is exactly:

```csv
id,label,language,definition,source,alt_labels,broader,status,replaced_by,change_note
```

One row describes one concept with one preferred label and definition in its
declared language. This profile does not author multiple preferred labels per
concept; extend the maintained profile deliberately for multilingual labels.

| Column | Meaning |
|---|---|
| `id` | Stable machine identifier, letters/digits/dot/underscore/hyphen. It must not depend on row position. Case variants collide under this profile. |
| `label` | Preferred label. Labels must be unambiguous within a language under this profile; that is a project constraint, stronger than SKOS itself. |
| `language` | Language of this row's labels and definition. |
| `definition` | Source-backed meaning. A later revision requires a change note; a changed meaning needs a new identifier and human review. |
| `source` | One absolute HTTP(S) provenance IRI, for example a DOI URL. Local validation does not fetch or verify what it says. |
| `alt_labels` | Optional alternative labels separated by `|`. They must differ from the preferred label and each other. |
| `broader` | Optional local concept IDs separated by `|`; targets must exist and the hierarchy must be acyclic. |
| `status` | `draft`, `active`, or `deprecated` lifecycle. This does not assert independent scientific approval. |
| `replaced_by` | Optional successor ID for a deprecated concept. Do not invent a successor when none is known. |
| `change_note` | Provenance note for a definition correction. The tool cannot decide whether a correction changes meaning. |

Generated RDF uses SKOS concepts and a concept scheme, language-tagged labels
and definitions, source/license metadata, and deprecation/replacement annotations.
Lifecycle also remains explicit in the CSV/catalog. No class equivalence,
external mapping or scientific acceptance is inferred.

## Reproducible editions

Run `validate <project>` before `release <project>`. `release` writes
`releases/<version>/`, including authoritative input copies, full/per-concept
RDF and HTML, a catalog with an input digest, and a SHA-256 file manifest.
Calling it again with identical bytes is a no-op. The tool refuses changed
inputs under the same version, older versions, namespace reassignment, missing
historical identifiers, reactivation of deprecated identifiers, and changed
snapshot bytes. Retain a deprecated row and its historical definition/source.

`build <project> --output <new-directory>` prepares the current local release
if needed and creates the latest website plus every verified historical
snapshot. It never overwrites an existing preview directory or writes previews
inside the immutable release history. Only generated
vocabulary outputs go to the site; private notes and authoring tools do not.

The manifest is an integrity check, not an external signature. Preserve reviewed
commits and tags and protect released files in the owning repository. A person
with write access can otherwise rewrite both content and its checksum.
