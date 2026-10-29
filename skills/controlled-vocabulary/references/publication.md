# Publish and maintain the vocabulary

The helper prepares files locally. Repository creation, commits/pushes, GitHub
Pages settings, workflow dispatch, public releases and W3ID pull requests are
separate external actions. Carry out only the actions the user has authorized.
Do not repeat an approval already supplied for the same scope.

## GitHub Pages

1. Review the public output and license. A private source repository does not
   make its Pages output private by default; confirm the actual site's access
   model before transferring anything restricted.
2. Keep `vocabulary.json`, `concepts.csv`, the portable `tools/` helper and
   immutable `releases/` under version control. Run local validation and the
   release/site build. Commit reviewed inputs and snapshots before deployment.
3. Review the prepared `vocabulary-pages.yml`; copy it into the vocabulary
   repository's `.github/workflows/` only as authorized. Its trigger is manual
   `workflow_dispatch`, restricted to the repository's default branch. It checks
   the repository binding and rejects an explicitly fictional example before
   building.
4. An authorized maintainer selects **Settings → Pages → Build and deployment →
   Source: GitHub Actions** and sets the `github-pages` environment protections.
   The deploy job needs `pages: write` and `id-token: write`; the build artifact
   must exist before deployment. The supplied workflow uses the official Pages
   actions and does not enable Pages itself.
5. Dispatch explicitly. Verify the actual deployment URL, representative concept
   pages and immutable edition files. Check final HTTP status, MIME type and
   that the served manifest matches the reviewed local release. A successful
   local build is not this verification.

The provided target is a normal project Pages URL. Adapt explicitly for an
organization/user root site, custom domain, Enterprise deployment or another
existing authority-site contract; preserve its identifiers and access rules.

## W3ID contribution

Read current upstream guidance before each contribution. As reviewed on
2026-10-29, new identifiers belong under `ids/<namespace>/` in
`perma-id/w3id.org`. Older companion clones may show the previous layout.

```bash
python tools/controlled_vocabulary.py prepare-publication . --output ../publication-review --w3id-checkout /path/to/current/w3id.org
```

Only the prepared namespace's `.htaccess` and maintainer README belong in the
W3ID contribution. Do not add the vocabulary, website, helper, workflow or test
plan to that namespace directory. Check the candidate and case variants against
a fresh upstream checkout. Existing names require that namespace's maintainer
process, not another claim. A clean local check does not reserve a name.

Publish and verify the HTTPS target first. Review the generated rewrite rules,
run upstream's `tools/check` checker, then exercise them with the current
supported local Apache setup. The generated `http-checks.json` gives expected
requests/locations and explicitly starts at `execution_status: not_run`. It is
not an Apache emulator or a passed HTTP receipt.

This starter's canonical namespace, scheme and concept IRIs always 303-redirect
to HTML. Machine representations have explicit stable paths, such as
`concept/<id>/index.ttl` and `vocabulary.jsonld`. Responses do not vary with
`Accept`, so the rules do not implement quality-value negotiation or need an
`Accept`-dependent cache claim. Unknown concept paths may redirect to a final
404; a redirect alone never proves a concept exists. If actual header
negotiation is required, adapt from current primary guidance and test all
supported types, wildcards, absent headers, `q=0`, relative preferences and caches
with Apache; a substring `RewriteCond` is not a complete negotiation algorithm.

Submit one reviewed namespace contribution with current maintainer contacts,
descriptive commit/PR text and actual test evidence. Do not change other
namespaces or W3ID's root configuration. After maintainer merge and observed
deployment, test real W3ID identifiers, redirects and final representations.
Record registration/publication only when those external results are confirmed.

## Maintenance

Use new edition versions and retain old snapshots and concept IRIs. Deprecate
and link a known successor rather than deleting/reassigning identifiers. Keep
source and decision provenance with definition changes. When hosting moves,
update only authorized redirect targets and test old paths as well as new ones.
Keep at least one reachable maintainer with a GitHub username, and plan a
successor who can maintain both the website and the redirect contribution.
