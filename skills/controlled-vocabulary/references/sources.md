# Primary guidance reviewed 2026-10-29

Recheck the live documents when performing external publication. Local
scaffolding cannot establish current name availability, service deployment or
repository permissions.

| Source | What it informs |
|---|---|
| [W3ID: creating an identifier](https://github.com/perma-id/w3id.org/blob/master/docs/guides/create-an-id.md) | Current `ids/` layout, name/case collision checks, a live HTTPS target before submission, maintainer GitHub contacts and reviewed namespace contribution. |
| [W3ID: rewrite rules](https://github.com/perma-id/w3id.org/blob/master/docs/guides/htaccess.md) | Directory-relative patterns, rule flags, ordering and avoiding copied unnecessary directives. |
| [W3ID: content negotiation](https://github.com/perma-id/w3id.org/blob/master/docs/guides/content-negotiation.md) | Redirecting to representation URLs; explicit representation paths are this starter's chosen simpler profile, not universal negotiation support. |
| [W3ID: testing](https://github.com/perma-id/w3id.org/blob/master/docs/guides/testing.md) | Upstream checker, actual local Apache behavior, root/bare/path/header requests and final MIME/status checks. |
| [W3ID: identifier maintenance](https://github.com/perma-id/w3id.org/blob/master/docs/guides/maintain-an-id.md) | Preserve existing paths, review target changes, refresh contacts and state actual tested URLs. |
| [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/) | Concepts, concept schemes, labels, definitions and semantic relations; S13 disjoint label properties and S14 at most one preferred label per language. |
| [W3C Cool URIs](https://www.w3.org/TR/cooluris/) | Distinguish identifiers for concepts from describing documents; keep established hash/slash contracts and use appropriate redirects. |
| [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) | Official build/artifact/deploy actions, required permissions and `github-pages` environment. |
| [GitHub Pages publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) | Explicit settings choice and actual publication/access boundary. |

Existing salmon vocabulary projects supplied generic architectural checks:
CSV/JSON authority inputs, generated outputs, immutable manifests, source
provenance and separate vocabulary versus identifier-hosting repositories. No
private vocabulary records, mappings or source-card text are embedded here.
