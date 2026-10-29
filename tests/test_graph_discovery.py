"""JSON CLI boundary over a real installed wheel and fictional local stores."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/graph-discovery/scripts/graph_discovery.py"
HAS_GRAPH = importlib.util.find_spec("salmongraph") is not None
B = "https://example.test/fictional-plugin-discovery/"


def cli(value, library_path=None):
    # A socket attempt is a failed test. The real graph library remains unmocked.
    launcher = """import runpy,socket,sys
def denied(*a,**k): raise AssertionError('network forbidden in graph tests')
socket.create_connection=socket.getaddrinfo=denied
socket.socket.connect=denied
if len(sys.argv)>2: sys.path.insert(0,sys.argv[2])
runpy.run_path(sys.argv[1],run_name='__main__')
"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SALMONGRAPH_") and k != "SALMON_GRAPH_BINDING"}
    command = [sys.executable, "-I", "-c", launcher, str(SCRIPT)]
    if library_path is not None:
        command.append(str(library_path))
    proc = subprocess.run(command,
        input=json.dumps(value), capture_output=True, text=True, timeout=60, env=env)
    if proc.returncode or proc.stderr:
        raise AssertionError((proc.returncode, proc.stderr, proc.stdout))
    return json.loads(proc.stdout)


class InputBoundary(unittest.TestCase):
    def test_no_binding_is_unavailable_without_opening_or_acquiring_a_store(self):
        answer = cli({"action": "discover"})
        self.assertFalse(answer["ok"])
        self.assertEqual(answer["error"]["code"], "binding_required")

    def test_unknown_fields_and_write_actions_are_refused(self):
        for value in ({"action": "contribute"}, {"action": "discover", "project_datasets": [B + "outside"]},
                {"action": "discover", "endpoint": "https://example.test/graph"}):
            with self.subTest(value=value):
                answer = cli(value)
                self.assertFalse(answer["ok"])
                self.assertIn(answer["error"]["code"], ("unsupported_action", "invalid_input"))

    def test_absent_binding_and_permission_denial_do_not_read_or_create_stores(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "binding.json"
            for updates, code in [({"admitted": False}, "access_unavailable"),
                    ({"read_authorized": False}, "access_unavailable"), ({}, "store_unavailable")]:
                path.write_text(json.dumps({"store_dir": "missing-store", "project_datasets": [B + "project/dataset"],
                    "admitted": True, "read_authorized": True, **updates}))
                answer = cli({"action": "discover", "binding_file": str(path)})
                self.assertFalse(answer["ok"])
                self.assertEqual(answer["error"]["code"], code)
                self.assertFalse((Path(temp) / "missing-store").exists())
            path.unlink()
            self.assertEqual(cli({"binding_file": str(path)})["error"]["code"], "binding_unavailable")


@unittest.skipUnless(HAS_GRAPH, "needs the pinned installed graph wheel (Python 3.13+)")
class InstalledWheelBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def binding(self, store, datasets=None, **updates):
        path = self.directory / "binding.json"
        value = {"store_dir": str(store), "project_datasets": datasets or [B + "project/dataset"],
            "admitted": True, "read_authorized": True, **updates}
        path.write_text(json.dumps(value))
        return str(path)

    def measurement_store(self):
        import gc
        import pyoxigraph as ox
        from salmongraph.graph import GraphBuilder, L
        builder = GraphBuilder()
        for slug in ("project", "other", "same-label"):
            dataset, table, schema, column, graph = (B + slug + "/" + part
                for part in ("dataset", "table", "schema", "column", "graph"))
            builder.type(dataset, "dcat:Dataset", graph)
            builder.add(dataset, "pav:version", L("fictional-v1"), graph)
            builder.add(dataset, "dcterms:source", B + slug + "/source", graph)
            builder.add(dataset, "dcterms:hasPart", table, graph)
            builder.add(table, "csvw:tableSchema", schema, graph)
            builder.add(schema, "csvw:column", column, graph)
            builder.type(column, "csvw:Column", graph)
            meaning = B + ("meaning/different" if slug == "same-label" else "meaning/temperature")
            builder.add(meaning, "rdfs:label", L("Fictional temperature"), graph)
            record = B + slug + "/record"
            builder.reify(record, column, "qb:concept", meaning, graph, assert_triple=True)
            builder.add(record, "dcterms:source", B + slug + "/source", graph)
        store = self.directory / "admitted"
        engine = ox.Store(store)
        engine.extend(builder.quads)
        engine.flush()
        del engine
        gc.collect()
        return store

    def save(self, builder):
        import gc
        import pyoxigraph as ox
        store = self.directory / "admitted"
        engine = ox.Store(store)
        engine.extend(builder.quads)
        engine.flush()
        del engine
        gc.collect()
        return store

    @staticmethod
    def topology(builder, slug):
        from salmongraph.graph import L
        dataset, table, schema, column, graph = (B + slug + "/" + part
            for part in ("dataset", "table", "schema", "column", "graph"))
        builder.type(dataset, "dcat:Dataset", graph)
        builder.add(dataset, "pav:version", L("fictional-v1"), graph)
        builder.add(dataset, "dcterms:source", B + slug + "/source", graph)
        builder.add(dataset, "dcterms:hasPart", table, graph)
        builder.add(table, "csvw:tableSchema", schema, graph)
        builder.add(schema, "csvw:column", column, graph)
        builder.type(column, "csvw:Column", graph)
        builder.add(column, "csvw:number", L(1), graph)
        return dataset, table, column, graph

    @staticmethod
    def native(builder, slug, parent, graph, iri, context):
        from salmongraph import provenance
        from salmongraph.graph import L
        from salmongraph.native_references import CONTEXT_TYPE
        node, record = B + slug + "/native-" + context["family"], B + slug + "/record-" + context["family"]
        builder.add(node, "dcterms:isPartOf", parent, graph)
        provenance.mark_statement(builder, record, node, "dcterms:references", iri, graph=graph,
            agent=B + "fictional-agent", activity=B + "fictional-run", evidence="Fictional metadata reference only",
            confidence="high", criticality="critical", assert_triple=False)
        builder.add(record, "dcterms:type", L(CONTEXT_TYPE), graph)
        builder.add(record, "prov:value", L(json.dumps(context)), graph)

    def native_store(self):
        from salmongraph.graph import GraphBuilder
        from salmongraph.native_references import CONTEXT_TYPE
        builder = GraphBuilder()
        for slug in ("project", "other", "old-authority", "observed"):
            dataset, table, column, graph = self.topology(builder, slug)
            if slug == "observed":
                builder.add(B + slug + "/observation", "qb:dataSet", dataset, graph)
                builder.add(B + slug + "/observation", "sosa:usedProcedure", B + "procedure", graph)
                builder.add(B + slug + "/observation", "sosa:hasFeatureOfInterest", B + "identity", graph)
                builder.type(B + "identity", "smn:Population", graph)
                continue
            population = {"schema": CONTEXT_TYPE, "family": "population", "field": "codes.term_iri",
                "scope": "code-reference", "columnOrdinal": 0, "nativeKey": "F-7",
                "authorityName": "Fictional Authority", "authorityVersion": "old" if slug == "old-authority" else "v1",
                "vocabularyIri": B + "authority/v1", "termType": "owl_named_individual"}
            self.native(builder, slug, column, graph, B + "identity", population)
            if slug != "old-authority":
                self.native(builder, slug, table, graph, B + "procedure", {"schema": CONTEXT_TYPE,
                    "family": "procedure", "field": "tables.method_iri", "scope": "table", "protocolCitation": "Fictional method citation"})
        return self.save(builder)

    def mapping_store(self, decision="reviewed-scoped", incomplete=False):
        from salmongraph import provenance
        from salmongraph.graph import GraphBuilder, L
        from salmongraph.native_references import CONTEXT_TYPE, PENDING_TYPE
        builder = GraphBuilder()
        _owner, _table, column, graph = self.topology(builder, "project")
        _other, _table, other_column, other_graph = self.topology(builder, "other")
        def side(slug, key):
            return {"nativeKey": key, "termIri": B + slug + "/identity", "termType": "owl_named_individual",
                "authorityName": "Fictional " + slug, "authorityVersion": "v1", "vocabularyIri": B + slug + "/vocabulary",
                "evidence": {"citation": "Fictional authority source", "sha256": None}}
        row = {"index": 0, "columnOrdinal": 0, "columnName": "fictional_identity", "source": side("north", "N-1"),
            "target": side("south", "S-7"), "predicateIri": B + "scoped-relation",
            "evidence": {"citation": "Fictional scope evidence", "sha256": "a" * 64},
            "uncertainty": "Fictional sampling frame only", "scope": {"kind": "dataset-identifier", "note": "Fictional selected dataset period"},
            "sourceDecision": decision, "origin": "current-saved-source-mapping"}
        record = B + "project/saved-relationship"
        provenance.mark_statement(builder, record, row["source"]["termIri"], row["predicateIri"], row["target"]["termIri"],
            graph=graph, agent=B + "fictional-agent", activity=B + "fictional-run", evidence="Fictional mapping evidence",
            confidence="high", criticality="critical", assert_triple=False)
        builder.add(record, "dcterms:isPartOf", column, graph)
        builder.add(record, "dcterms:source", B + "project/source", graph)
        builder.add(record, "dcterms:type", L(PENDING_TYPE), graph)
        if not incomplete:
            builder.add(record, "prov:value", L(json.dumps({"schema": PENDING_TYPE, "row": row})), graph)
        context = {"schema": CONTEXT_TYPE, "family": "population", "field": "codes.term_iri", "scope": "code-reference", "columnOrdinal": 0,
            **{key: row["target"][key] for key in ("nativeKey", "authorityName", "authorityVersion", "vocabularyIri", "termType")}}
        self.native(builder, "other", other_column, other_graph, row["target"]["termIri"], context)
        return self.save(builder), row

    def test_exact_iri_evidence_and_runtime_are_preserved_from_installed_wheel(self):
        from salmongraph import discovery
        store = self.measurement_store()
        answer = cli({"action": "discover", "binding_file": self.binding(store), "families": ["measurement"]})
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(answer["result"], discovery.discover(store,
            project_datasets=[B + "project/dataset"], families=["measurement"]))
        found, = answer["result"]["paths"]
        self.assertEqual(found["dataset"], B + "other/dataset")
        self.assertEqual(found["shared_iri"], B + "meaning/temperature")
        self.assertEqual(found["candidate_source"]["versions"], ["fictional-v1"])
        self.assertEqual(found["candidate"]["authority"], "source_stated")
        self.assertTrue(answer["runtime"]["matches_pin"])
        self.assertEqual(answer["runtime"]["source_commit"], "4036bad502ac0319e1207f233386ac7f766de2f6")

    def test_saved_relationship_mode_needs_explicit_pending_opt_in(self):
        answer = cli({"action": "discover", "binding_file": self.binding(self.measurement_store()),
            "families": ["population"], "relationship_kinds": ["scoped_mapping"]})
        self.assertFalse(answer["ok"])
        self.assertEqual(answer["error"]["code"], "pending_opt_in_required")

    def test_native_metadata_pending_and_authority_context_never_become_observations(self):
        from salmongraph import discovery
        store = self.native_store()
        request = {"binding_file": self.binding(store)}
        self.assertEqual(cli(request)["result"]["paths"], [])
        answer = cli({**request, "include_pending": True})
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(answer["result"], discovery.discover(store, project_datasets=[B + "project/dataset"], include_pending=True))
        self.assertEqual(len(answer["result"]["paths"]), 2)
        for path in answer["result"]["paths"]:
            self.assertEqual(path["dataset"], B + "other/dataset")
            self.assertEqual(path["match_basis"], "native_metadata_reference")
            self.assertEqual(path["path_state"], "awaiting_review")
            self.assertFalse(path["candidate"]["asserted"])
            self.assertEqual(path["candidate"]["authority"], "awaiting_review")
            self.assertIn(path["candidate"]["native_reference"]["field"], ("tables.method_iri", "codes.term_iri"))

    def check_mapping(self, decision, kind):
        from salmongraph import discovery
        store, row = self.mapping_store(decision)
        request = {"binding_file": self.binding(store), "include_pending": True,
            "families": ["population"], "relationship_kinds": [kind]}
        answer = cli(request)
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(answer["result"], discovery.discover(store, project_datasets=[B + "project/dataset"],
            include_pending=True, families=["population"], relationship_kinds=[kind]))
        found, = answer["result"]["paths"]
        self.assertEqual(found["match"], kind)
        self.assertNotIn("shared_iri", found)
        self.assertEqual(found["path_state"], "awaiting_review")
        self.assertEqual(found["relationship"]["context"], row)
        self.assertEqual(found["relationship"]["sharedReview"], "awaiting_review")
        reverse = cli({**request, "binding_file": self.binding(store, [B + "other/dataset"])})
        self.assertEqual(reverse["result"]["paths"][0]["relationship"], found["relationship"])

    def test_scoped_mapping_is_direct_pending_and_retains_original_direction(self):
        self.check_mapping("reviewed-scoped", "scoped_mapping")

    def test_suggestion_is_unresolved_and_retains_original_direction(self):
        self.check_mapping("unresolved", "suggestion")

    def test_incomplete_saved_proof_remains_refusal_with_no_paths(self):
        from salmongraph import discovery
        store, _row = self.mapping_store(incomplete=True)
        answer = cli({"binding_file": self.binding(store), "include_pending": True,
            "families": ["population"], "relationship_kinds": ["scoped_mapping"]})
        self.assertFalse(answer["ok"])
        self.assertEqual(answer["error"]["code"], "incomplete_evidence")
        self.assertEqual(answer["result"]["query_status"], "partial_evidence_refused")
        self.assertEqual(answer["result"]["partial_reason"], "incomplete_saved_mapping_evidence")
        self.assertEqual(answer["result"]["paths"], [])
        self.assertEqual(answer["result"], discovery.discover(store, project_datasets=[B + "project/dataset"],
            include_pending=True, families=["population"], relationship_kinds=["scoped_mapping"]))

    def test_discovery_never_changes_bound_store_files(self):
        store = self.measurement_store()
        def inventory():
            return {p.relative_to(store).as_posix(): (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
                for p in store.rglob("*") if p.is_file()}
        before = inventory()
        self.assertTrue(cli({"binding_file": self.binding(store)})["ok"])
        self.assertEqual(inventory(), before)

    def test_empty_result_and_invalid_query_are_distinct(self):
        store = self.measurement_store()
        empty = cli({"binding_file": self.binding(store, [B + "absent/dataset"])})
        self.assertTrue(empty["ok"])
        self.assertEqual(empty["result"]["paths"], [])
        bad = cli({"binding_file": self.binding(store), "families": ["unknown"]})
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["error"]["code"], "invalid_query_or_store")

    def test_same_version_with_changed_installed_source_is_refused(self):
        import salmongraph
        shadow = self.directory / "different-wheel"
        copied = shadow / "salmongraph"
        shutil.copytree(Path(salmongraph.__file__).parent, copied)
        with (copied / "discovery.py").open("a") as handle:
            handle.write("\n# Fictional changed installed package with unchanged version.\n")
        answer = cli({"action": "runtime"}, library_path=shadow)
        self.assertFalse(answer["ok"])
        self.assertEqual(answer["error"]["code"], "runtime_mismatch")
        self.assertNotIn("result", answer)


if __name__ == "__main__":
    unittest.main()
