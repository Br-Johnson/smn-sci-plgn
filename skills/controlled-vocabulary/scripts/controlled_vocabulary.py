#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Brett Johnson and contributors
"""Local CSV-to-SKOS authoring. Never registers, uploads, deploys or calls a network."""

from __future__ import annotations

import argparse
import csv
from graphlib import TopologicalSorter, CycleError
import hashlib
import html
import io
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


COLUMNS = ("id", "label", "language", "definition", "source", "alt_labels", "broader", "status", "replaced_by", "change_note")
VERSION_RE = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*))?")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
LANG_RE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*")
DEMO = {
    "slug": "example-salmon-vocabulary", "title": "Fictional salmon vocabulary",
    "description": "Fictional concepts for a local authoring demonstration.",
    "version": "0.1.0", "issued": "2026-01-01", "language": "en",
    "license": "https://creativecommons.org/licenses/by/4.0/", "publisher": "Example organisation",
    "github_owner": "example-org", "github_repo": "example-salmon-vocabulary",
    "maintainers": [{"name": "Example maintainer", "github": "example-maintainer", "email": "maintainer@example.org"}],
    "example": True,
}
TOOL_LICENSE = """MIT License

Copyright (c) 2026 Brett Johnson and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def url(value, label):
    require(isinstance(value, str) and not re.search(r'[\s<>"{}|\\^`\x00-\x1f]', value), f"{label} must be an absolute safe HTTP(S) IRI")
    require(not re.search(r"%(?![0-9A-Fa-f]{2})", value), f"{label} contains malformed percent encoding")
    parsed = urlsplit(value)
    require(parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password, f"{label} must be an absolute HTTP(S) IRI without credentials")
    try:
        parsed.port  # urlsplit checks the port only when this property is read.
    except ValueError:
        raise ValueError(f"{label} contains an invalid HTTP(S) port") from None


def config_check(meta):
    require(isinstance(meta, dict), "vocabulary.json must contain an object")
    require(set(DEMO) - {"example"} <= meta.keys(), "vocabulary.json is missing required metadata; use the documented profile")
    require(not (meta.keys() - DEMO.keys()), "vocabulary.json contains an unknown field")
    for key in ("title", "description", "publisher"):
        require(isinstance(meta[key], str) and meta[key].strip() and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", meta[key]), f"{key} is required and must contain printable text")
    require(isinstance(meta["slug"], str) and re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", meta["slug"]) and len(meta["slug"]) <= 64, "slug must be lowercase letters/digits/hyphens, starting with a letter")
    require(isinstance(meta["version"], str) and VERSION_RE.fullmatch(meta["version"]), "version must be a three-part semantic version, optionally with a prerelease suffix")
    version_key(meta["version"])
    require(isinstance(meta["issued"], str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", meta["issued"]), "issued must be a calendar date in YYYY-MM-DD form")
    try:
        date.fromisoformat(meta["issued"])
    except ValueError:
        raise ValueError("issued must be a valid calendar date in YYYY-MM-DD form") from None
    require(LANG_RE.fullmatch(meta["language"]), "language must use the profile's BCP47-shaped tag")
    url(meta["license"], "license")
    require(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", meta["github_owner"]), "github_owner must be a GitHub owner name")
    require(ID_RE.fullmatch(meta["github_repo"]) and meta["github_repo"] not in {".", ".."}, "github_repo must be a simple repository name")
    require(isinstance(meta["maintainers"], list) and meta["maintainers"], "at least one maintainer is required")
    for owner in meta["maintainers"]:
        require(isinstance(owner, dict) and set(owner) == {"name", "github", "email"}, "each maintainer requires name, github and email")
        require(all(isinstance(v, str) and v.strip() and not re.search(r"[\r\n]", v) for v in owner.values()), "maintainer values must be non-empty single lines")
        require(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner["github"]), "maintainer github must be a username")
        require(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", owner["email"]), "maintainer email must be an address")
    require(isinstance(meta.get("example", False), bool), "example must be boolean")


def namespace(meta):
    return f"https://w3id.org/{meta['slug']}/"


def load_project(project):
    for name in ("vocabulary.json", "concepts.csv"):
        require(not (project / name).is_symlink(), f"{name} must not be a symbolic link")
    meta = json.loads((project / "vocabulary.json").read_text(encoding="utf-8"))
    config_check(meta)
    with (project / "concepts.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == list(COLUMNS), f"concepts.csv columns must be {','.join(COLUMNS)}")
        rows = list(reader)
    require(rows, "concepts.csv requires at least one concept")
    seen = set()
    for row in rows:
        require(None not in row and all(isinstance(v, str) for v in row.values()), "concepts.csv contains a malformed row")
        row.update({k: v.strip() for k, v in row.items()})
        require(ID_RE.fullmatch(row["id"]) and row["id"] not in {".", ".."}, "concept id must be a simple stable identifier")
        require(row["id"].casefold() not in seen, "concept identifiers collide, including a case variant")
        seen.add(row["id"].casefold())
        require(row["label"] and row["definition"], f"{row['id']}: label and definition are required")
        require(LANG_RE.fullmatch(row["language"]), f"{row['id']}: language is required")
        url(row["source"], f"{row['id']}: source")
        require(row["status"] in {"draft", "active", "deprecated"}, f"{row['id']}: status must be draft, active or deprecated")
    by_id = {r["id"]: r for r in rows}
    labels = set()
    for row in rows:
        label_key = (row["language"].casefold(), row["label"].casefold())
        require(label_key not in labels, "preferred labels collide in the same language under this authoring profile")
        labels.add(label_key)
        alternatives = row["alt_labels"].split("|") if row["alt_labels"] else []
        require(all(v and v.casefold() != row["label"].casefold() for v in alternatives) and len(set(v.casefold() for v in alternatives)) == len(alternatives), f"{row['id']}: alternative labels must be distinct from each other and the preferred label")
        for broader in row["broader"].split("|") if row["broader"] else []:
            require(broader in by_id and broader != row["id"], f"{row['id']}: broader must name another concept in this vocabulary")
        replacement = row["replaced_by"]
        if replacement:
            require(row["status"] == "deprecated" and replacement in by_id and replacement != row["id"] and by_id[replacement]["status"] != "deprecated", f"{row['id']}: replaced_by requires a deprecated source and an existing non-deprecated successor")
    try:
        tuple(TopologicalSorter({r["id"]: r["broader"].split("|") if r["broader"] else [] for r in rows}).static_order())
    except CycleError:
        raise ValueError("broader hierarchy contains a cycle") from None
    check_history(project, meta, by_id)
    return meta, sorted(rows, key=lambda row: row["id"])


def empty_destination(path):
    require(not path.exists() and not path.is_symlink(), f"destination already exists: {path}; choose a new directory")
    path.mkdir(parents=True)


def version_key(version):
    match = VERSION_RE.fullmatch(version)
    require(match, "release version is malformed")
    pre = match[4]
    require(not pre or all(not v.isdigit() or v == "0" or not v.startswith("0") for v in pre.split(".")), "numeric prerelease identifiers must not have leading zeros")
    return tuple(map(int, match.group(1, 2, 3))), int(pre is None), tuple((0, int(v)) if v.isdigit() else (1, v) for v in pre.split(".")) if pre else ()


def check_history(project, meta, by_id):
    releases = project / "releases"
    require(not releases.is_symlink(), "releases must not be a symbolic link")
    if not releases.exists():
        return
    for snapshot in sorted(releases.iterdir()):
        require(snapshot.is_dir() and not snapshot.is_symlink(), "releases may contain only real version directories")
        require(not any(p.is_symlink() for p in snapshot.rglob("*")), "release files must not be symbolic links")
        manifest = json.loads((snapshot / "manifest.json").read_text())
        require(manifest.get("schema_version") == "controlled-vocabulary.release/v1" and manifest.get("version") == snapshot.name, "release manifest/version mismatch")
        require(manifest.get("namespace") == namespace(meta), "a release cannot reassign the namespace")
        expected = manifest["files"]
        actual = {p.relative_to(snapshot).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.rglob("*") if p.is_file() and p.relative_to(snapshot).as_posix() != "manifest.json"}
        require(actual == expected, "immutable release content or manifest hashes differ")
        require(version_key(meta["version"]) >= version_key(snapshot.name), "new version must not precede an existing release")
        catalog = json.loads((snapshot / "catalog.json").read_text())
        for old in catalog["concepts"]:
            require(old["id"] in by_id, f"cannot withdraw released identifier {old['id']}; retain and deprecate it")
            current = by_id[old["id"]]
            require(old["status"] != "deprecated" or current["status"] == "deprecated", f"cannot silently reactivate deprecated identifier {old['id']}")
            if current["definition"] != old["definition"]:
                require(current["change_note"], f"{old['id']}: a definition revision needs a change_note and human meaning review; mint a new id for changed meaning")
        if snapshot.name == meta["version"]:
            current_digest = hashlib.sha256(canonical([meta, sorted(by_id.values(), key=lambda r: r["id"])] )).hexdigest()
            require(current_digest == catalog["input_sha256"], "this release version already exists with different authoring inputs; use a new version")


def initialize(project, config, demo):
    meta = dict(DEMO) if demo else json.loads(config.read_text(encoding="utf-8"))
    config_check(meta)
    empty_destination(project)
    (project / "vocabulary.json").write_bytes(canonical(meta))
    with (project / "concepts.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, COLUMNS, lineterminator="\n")
        writer.writeheader()
        if demo:
            for identity, label, status, replacement in (("demo-observation", "Demo observation category", "draft", ""), ("demo-retired", "Retired demo category", "deprecated", "demo-observation")):
                writer.writerow(dict.fromkeys(COLUMNS, "") | {"id": identity, "label": label, "language": "en", "definition": "A fictional category used only for a local authoring demonstration.", "source": "https://example.org/fictional-specification", "status": status, "replaced_by": replacement})
    (project / "tools").mkdir()
    (project / "tools" / "controlled_vocabulary.py").write_bytes(Path(__file__).read_bytes())
    (project / "tools" / "LICENSE").write_text(TOOL_LICENSE)
    (project / "README.md").write_text("# Controlled vocabulary authoring\n\nEdit vocabulary.json and concepts.csv, then run the copied tools/controlled_vocabulary.py with validate, release, build and prepare-publication. Generated releases are immutable; the site is generated. Review sources, meaning, public scope, license and ownership before any publication. The helper never registers or deploys. Its software license is tools/LICENSE; the vocabulary's data license is the metadata license IRI.\n")
    return {"ok": True, "project": str(project), "namespace": namespace(meta), "publication_performed": False}


PREFIXES = {"skos": "http://www.w3.org/2004/02/skos/core#", "dcterms": "http://purl.org/dc/terms/", "owl": "http://www.w3.org/2002/07/owl#", "xsd": "http://www.w3.org/2001/XMLSchema#"}


def literal(value, language):
    return {"@value": value, "@language": language}


def graph_for(meta, rows):
    base = namespace(meta)
    scheme = {"@id": base + "scheme", "@type": "skos:ConceptScheme", "dcterms:title": literal(meta["title"], meta["language"]), "dcterms:description": literal(meta["description"], meta["language"]), "dcterms:publisher": meta["publisher"], "dcterms:license": {"@id": meta["license"]}, "dcterms:issued": {"@value": meta["issued"], "@type": "xsd:date"}, "owl:versionInfo": meta["version"]}
    graph = [scheme]
    for row in rows:
        term = {"@id": base + "concept/" + row["id"], "@type": "skos:Concept", "skos:inScheme": {"@id": scheme["@id"]}, "skos:prefLabel": literal(row["label"], row["language"]), "skos:definition": literal(row["definition"], row["language"]), "dcterms:source": {"@id": row["source"]}, "skos:notation": row["id"], "skos:editorialNote": "Lifecycle status: " + row["status"], "owl:deprecated": row["status"] == "deprecated"}
        for field, prop in (("alt_labels", "skos:altLabel"), ("broader", "skos:broader")):
            if row[field]:
                term[prop] = [literal(v, row["language"]) if field == "alt_labels" else {"@id": base + "concept/" + v} for v in row[field].split("|")]
        if row["replaced_by"]:
            term["dcterms:isReplacedBy"] = {"@id": base + "concept/" + row["replaced_by"]}
        if row["change_note"]:
            term["skos:changeNote"] = literal(row["change_note"], row["language"])
        graph.append(term)
    return graph


def turtle(graph):
    def value(item):
        if isinstance(item, bool):
            return "true" if item else "false"
        if isinstance(item, dict):
            if "@id" in item:
                return "<" + item["@id"] + ">"
            rendered = json.dumps(item["@value"], ensure_ascii=False)
            return rendered + ("@" + item["@language"] if "@language" in item else "^^" + item["@type"])
        return json.dumps(item, ensure_ascii=False)
    lines = [f"@prefix {key}: <{iri}> ." for key, iri in PREFIXES.items()]
    for node in graph:
        statements = ["a " + node["@type"]]
        for prop in sorted(set(node) - {"@id", "@type"}):
            objects = node[prop] if isinstance(node[prop], list) else [node[prop]]
            statements.append(prop + " " + ", ".join(value(v) for v in objects))
        lines.append("\n<" + node["@id"] + "> " + " ;\n    ".join(statements) + " .")
    return ("\n".join(lines) + "\n").encode()


def page(meta, title, body):
    css = "body{font:17px/1.6 system-ui,sans-serif;color:#163d38;max-width:960px;margin:48px auto;padding:0 22px}a{color:#185c90;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{text-align:left;vertical-align:top;border-bottom:1px solid #d6e2dc;padding:10px}code{overflow-wrap:anywhere}h1{line-height:1.2}small{color:#52645f}"
    return (f'<!doctype html><html lang="{meta["language"]}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{css}</style><body><h1>{html.escape(title)}</h1>{body}</body></html>\n').encode()


def artifact_files(meta, rows):
    graph = graph_for(meta, rows)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, COLUMNS, lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    catalog = {"schema_version": "controlled-vocabulary/v1", "namespace": namespace(meta), "version": meta["version"], "concepts": rows, "input_sha256": hashlib.sha256(canonical([meta, rows])).hexdigest()}
    result = {"vocabulary.json": canonical(meta), "concepts.csv": text.getvalue().encode(), "catalog.json": canonical(catalog), "vocabulary.ttl": turtle(graph), "vocabulary.jsonld": canonical({"@context": PREFIXES, "@graph": graph}), ".nojekyll": b""}
    e = html.escape
    terms = "".join(f'<tr><td><a href="concept/{r["id"]}/">{e(r["label"])}</a></td><td>{e(r["definition"])}</td><td>{r["status"]}</td></tr>' for r in rows)
    note = "<p><strong>Fictional demonstration; no namespace registration or publication is established.</strong></p>" if meta.get("example") else ""
    result["index.html"] = page(meta, meta["title"], note + f'<p>{e(meta["description"])}</p><p>Version {e(meta["version"])} · {meta["issued"]} · <a href="{e(meta["license"])}">License</a></p><p><a href="vocabulary.ttl">Turtle</a> · <a href="vocabulary.jsonld">JSON-LD</a> · <a href="catalog.json">Catalog and provenance</a></p><table><thead><tr><th>Concept</th><th>Definition</th><th>Lifecycle</th></tr></thead><tbody>{terms}</tbody></table><p><small>Publisher: {e(meta["publisher"])}. Lifecycle is not an assertion of independent scientific approval.</small></p>')
    for row, term in zip(rows, graph[1:]):
        stem = "concept/" + row["id"] + "/index"
        result[stem + ".ttl"] = turtle([graph[0], term])
        result[stem + ".jsonld"] = canonical({"@context": PREFIXES, "@graph": [graph[0], term]})
        replacement = f'<p>Replaced by <a href="../{row["replaced_by"]}/">{e(row["replaced_by"])}</a>.</p>' if row["replaced_by"] else ""
        result[stem + ".html"] = page(meta, row["label"], f'<p><a href="../../index.html">Vocabulary</a> · <a href="index.ttl">Turtle</a> · <a href="index.jsonld">JSON-LD</a></p><p><code>{e(term["@id"])}</code></p><p>{e(row["definition"])}</p><p>Definition source: <a href="{e(row["source"])}">{e(row["source"])}</a></p><p>Lifecycle: {row["status"]} · Language: {e(row["language"])}</p>{replacement}')
    result["manifest.json"] = canonical({"schema_version": "controlled-vocabulary.release/v1", "namespace": namespace(meta), "version": meta["version"], "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(result.items())}})
    return result


def write_files(target, files):
    for name, data in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def release(project, meta, rows):
    files = artifact_files(meta, rows)
    target = project / "releases" / meta["version"]
    if target.exists():
        require(not target.is_symlink(), "release must not be a symbolic link")
        actual = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob("*") if p.is_file()}
        require(actual == files, "this release version already exists with different bytes; use a new version, never overwrite a release")
        return {"ok": True, "release": str(target), "unchanged": True, "publication_performed": False}
    target.mkdir(parents=True)
    write_files(target, files)
    return {"ok": True, "release": str(target), "unchanged": False, "publication_performed": False}


def build(project, output, meta, rows):
    preview_destination(project, output)
    release(project, meta, rows)
    empty_destination(output)
    write_files(output, artifact_files(meta, rows))
    shutil.copytree(project / "releases", output / "releases")
    return {"ok": True, "site": str(output), "version": meta["version"], "publication_performed": False}


PAGES_WORKFLOW = """# Review, then copy to .github/workflows/vocabulary-pages.yml in the vocabulary repository.
name: Publish vocabulary website
'on':
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: github-pages
  cancel-in-progress: false
jobs:
  build:
    if: github.ref_name == github.event.repository.default_branch
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - name: Validate and prepare site
        run: |
          python tools/controlled_vocabulary.py validate . --for-publication --repository '${{ github.repository }}'
          python tools/controlled_vocabulary.py release .
          python tools/controlled_vocabulary.py build . --output _site
      - uses: actions/upload-pages-artifact@v4
        with:
          path: _site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/configure-pages@v5
      - uses: actions/deploy-pages@v4
        id: deployment
"""


def namespace_collision(meta, checkout):
    if checkout is None:
        return "not_performed"
    ids = checkout / "ids"
    require(ids.is_dir(), "current w3id.org checkout requires ids/; refresh an older checkout before checking")
    require(not any(p.name.casefold() == meta["slug"].casefold() for p in ids.iterdir()), "namespace collision in this local W3ID snapshot; choose another namespace or use its maintenance process")
    return "checked_local_snapshot"


def publication_plan(project, output, meta, rows, collision):
    require((project / "releases" / meta["version"]).is_dir(), "prepare the local release before preparing publication")
    preview_destination(project, output)
    empty_destination(output)
    site = f"https://{meta['github_owner'].lower()}.github.io/{meta['github_repo']}/"
    contacts = "\n".join(f"# {m['name']} <{m['email']}>; GitHub username: {m['github']}" for m in meta["maintainers"])
    rules = f"# /{meta['slug']}/\n# Maintainers\n{contacts}\n\nRewriteEngine On\n"
    rules += f"RewriteRule ^$ {site} [R=303,L]\nRewriteRule ^scheme/?$ {site} [R=303,L]\n"
    rules += f"RewriteRule ^(vocabulary\\.(?:ttl|jsonld)|catalog\\.json|manifest\\.json)$ {site}$1 [R=303,L]\n"
    rules += f"RewriteRule ^concept/([A-Za-z0-9][A-Za-z0-9._-]*)/index\\.(ttl|jsonld)$ {site}concept/$1/index.$2 [R=303,L]\n"
    rules += f"RewriteRule ^concept/([A-Za-z0-9][A-Za-z0-9._-]*)/?$ {site}concept/$1/ [R=303,L]\n"
    version = r"([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?)"
    rules += f"RewriteRule ^release/{version}/?$ {site}releases/$1/ [R=303,L]\n"
    rules += f"RewriteRule ^release/{version}/(vocabulary\\.(?:ttl|jsonld)|catalog\\.json|manifest\\.json)$ {site}releases/$1/$2 [R=303,L]\n"
    target = output / "w3id" / "ids" / meta["slug"]
    target.mkdir(parents=True)
    (target / ".htaccess").write_text(rules)
    owners = "\n".join(f"- {m['name']} — {m['email']} — GitHub: [{m['github']}](https://github.com/{m['github']})" for m in meta["maintainers"])
    (target / "README.md").write_text(f"# /{meta['slug']}/\n\nPersistent identifiers for {meta['title']}.\n\nNamespace: {namespace(meta)}\n\nTarget: {site}\n\n## Maintainers\n\n{owners}\n")
    (output / "vocabulary-pages.yml").write_text(PAGES_WORKFLOW)
    checks = [{"path": "", "status": 303, "location": site}, {"path": "vocabulary.ttl", "status": 303, "location": site + "vocabulary.ttl"}, {"path": "vocabulary.jsonld", "status": 303, "location": site + "vocabulary.jsonld"}]
    for row in rows:
        checks.append({"path": "concept/" + row["id"], "status": 303, "location": site + "concept/" + row["id"] + "/"})
        checks.append({"path": "concept/" + row["id"] + "/index.ttl", "status": 303, "location": site + "concept/" + row["id"] + "/index.ttl"})
    checks.append({"path": "release/" + meta["version"], "status": 303, "location": site + "releases/" + meta["version"] + "/"})
    (output / "http-checks.json").write_bytes(canonical({"execution_status": "not_run", "accept_policy": "Canonical identifiers always redirect to HTML, regardless of Accept. Use explicit representation paths; no quality-value negotiation is implemented.", "checks": checks, "also_check": ["no Accept", "text/html", "text/turtle", "application/ld+json", "*/*", "text/turtle;q=0,text/html;q=1", "unknown path and unknown concept (must not claim a successful term lookup)", "final target status and MIME type", "existing paths after each maintenance change"]}))
    (output / "REVIEW-BEFORE-PUBLISHING.md").write_text(f"# Publication plan — not executed\n\n1. Review vocabulary meaning, sources, license, public output and maintenance ownership. This tool cannot approve them.\n2. Commit the authoritative inputs, portable tool and immutable releases in the intended repository. Review and copy vocabulary-pages.yml into .github/workflows/.\n3. An authorized maintainer enables GitHub Pages with GitHub Actions, configures environment/branch protections, then explicitly dispatches the workflow. Confirm the public target and MIME types before W3ID submission.\n4. Refresh perma-id/w3id.org, recheck namespace collisions and its current contribution rules. Copy only w3id/ids/{meta['slug']}/ into its ids/ directory. No vocabulary/site files belong there. Run its checker and actual local Apache tests from the primary documentation. http-checks.json is an expected plan, not a passed HTTP test.\n5. Review one namespace PR with maintainer contacts and actual tested URLs/results, then submit only when authorized; do not repeat authorization already supplied for this scope. A local folder or prepared PR is not an allocated namespace.\n6. After the reviewed W3ID PR merges and deployment is observed, independently verify root, concept, version and representation URLs and final MIME types. Record the real evidence.\n\nNo namespace availability, registration, website publication or content negotiation has been verified by this preparation. Bare directory requests may incur Apache's normal slash redirect before these rules. Keep old identifiers resolving; deprecate rather than delete them.\n")
    return {"ok": True, "proposal": str(output), "namespace_collision_check": collision, "registration_verified": False, "publication_performed": False}


def preview_destination(project, output):
    history = (project / "releases").resolve()
    require(not output.resolve().is_relative_to(history), "preview destination must be outside immutable release history")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create local authoring inputs and a portable tool; does not register a namespace")
    init.add_argument("project", type=Path)
    mode = init.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--config", type=Path)
    validate = commands.add_parser("validate", help="Check the local authoring profile")
    validate.add_argument("project", type=Path)
    validate.add_argument("--w3id-checkout", type=Path)
    validate.add_argument("--repository", help="Check the expected GitHub owner/repository binding")
    validate.add_argument("--for-publication", action="store_true", help="Refuse an explicitly fictional demonstration; does not establish permission to publish")
    prepare = commands.add_parser("release", help="Prepare an immutable local release; does not publish")
    prepare.add_argument("project", type=Path)
    website = commands.add_parser("build", help="Build a static website in a new local directory; does not deploy")
    website.add_argument("project", type=Path)
    website.add_argument("--output", type=Path, required=True)
    publish = commands.add_parser("prepare-publication", help="Prepare Pages workflow and reviewed W3ID contribution files; never submit or deploy")
    publish.add_argument("project", type=Path)
    publish.add_argument("--output", type=Path, required=True)
    publish.add_argument("--w3id-checkout", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args.project, args.config, args.demo)
        else:
            meta, rows = load_project(args.project)
            collision = namespace_collision(meta, getattr(args, "w3id_checkout", None))
            if getattr(args, "repository", None):
                require(args.repository.casefold() == f"{meta['github_owner']}/{meta['github_repo']}".casefold(), "GitHub repository binding differs from the vocabulary metadata")
            if getattr(args, "for_publication", False):
                require(not meta.get("example", False), "fictional example cannot pass the publication-specific gate; replace it with reviewed real inputs")
            if args.command == "release":
                result = release(args.project, meta, rows)
            elif args.command == "build":
                result = build(args.project, args.output, meta, rows)
            elif args.command == "prepare-publication":
                result = publication_plan(args.project, args.output, meta, rows, collision)
            else:
                result = {"ok": True, "concept_count": len(rows), "namespace": namespace(meta), "namespace_collision_check": collision, "publication_performed": False}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "publication_performed": False}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
