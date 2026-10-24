"""Meaningful offline checks for private bundle handling and scientific limits."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workbench_project", ROOT / "scripts/workbench_project.py")
wp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wp)


def bundle():
    return {"format": wp.FORMAT, "exportedAt": "2026-10-24T12:00:00Z", "limitations": ["Private export"],
            "sources": [{"id": "catalog-a", "title": "Public source", "organization": "Agency", "kind": "Salmon",
                         "phase": "Offshore", "years": "2022", "region": "Pacific", "description": "Source metadata",
                         "variables": ["group"], "url": "https://example.org/source", "license": "unconfirmed",
                         "access": "public metadata", "limitations": "No age", "sourceVersion": "v1"}],
            "project": {"id": "private-project-id", "title": "Private project", "description": "Confidential description",
                        "question": "Which encounters can we describe?", "hypothesis": "A proposal", "region": "Pacific",
                        "spatialScale": "station", "temporalStart": "2022-01-01", "temporalEnd": "2022-04-30",
                        "temporalScale": "event", "ownerName": "Local owner", "revision": 1,
                        "createdAt": "2026-10-24T10:00:00Z", "updatedAt": "2026-10-24T12:00:00Z",
                        "contribution": {"committed": True, "outputs": ["workflow"], "rawAccess": "private",
                                         "embargoUntil": "2026-11-30", "reason": "Review safe method description"},
                        "datasets": [{"id": "native-source", "title": "Private upload", "citation": "Local source",
                                      "url": "", "status": "included", "reason": "Scope", "limitations": "Unknown marine age",
                                      "evidence": "PRIVATE SOURCE EVIDENCE", "sourceType": "upload",
                                      "sourceSha256": "a" * 64, "originalFileName": "private.csv", "columns": ["secret_code"], "rowCount": 3}],
                        "identities": [{"id": "candidate", "authority": "Agency A", "nativeId": "private-native-id",
                                        "label": "Shared name", "entityType": "source unit", "species": "Sockeye",
                                        "sourceUrl": "https://example.org/source", "sourceVersion": "v1", "targetAuthority": "Agency B",
                                        "targetId": "different-unit", "relationship": "candidate_match", "evidence": "Name only",
                                        "status": "pending", "reviewNote": "No accepted identity"}],
                        "notes": [{"id": "note", "text": "PRIVATE NOTE VALUE", "createdAt": "2026-10-24T12:00:00Z", "author": "Local owner"}]}}


class WorkbenchProjectTests(unittest.TestCase):
    def test_actual_export_shape_inspects_without_source_mutation(self):
        b = bundle(); original = deepcopy(b)
        out = wp.inspect_bundle(b)
        self.assertEqual(out["sourceDecisions"]["included"], 1)
        self.assertEqual(out["pendingIdentityCount"], 1)
        self.assertFalse(out["publicationAuthorized"])
        self.assertEqual(b, original)
        self.assertNotIn("PRIVATE NOTE VALUE", json.dumps(out))

    def test_expiry_and_explicit_asof_never_publish(self):
        b = bundle()
        before = wp.inspect_bundle(b, "2026-11-29")
        after = wp.inspect_bundle(b, "2026-11-30")
        self.assertEqual(before["embargoState"], "private_until_review")
        self.assertEqual(after["embargoState"], "review_due")
        self.assertFalse(after["publicationAuthorized"])
        self.assertEqual(b["project"]["contribution"]["rawAccess"], "private")

    def test_draft_inspection_allowed_but_contribution_preflight_refuses(self):
        b = bundle(); c = b["project"]["contribution"]
        c.update(committed=False, outputs=[], reason="", embargoUntil="")
        self.assertEqual(wp.inspect_bundle(b)["embargoState"], "not_committed")
        self.assertFalse(wp.inspect_bundle(b)["commitmentComplete"])
        with self.assertRaises(wp.ContractError): wp.contribution_preview(b, {"title": "Safe title"})

    def test_commitment_needs_outputs_reason_and_real_date(self):
        for field, value in [("outputs", []), ("reason", ""), ("embargoUntil", "forever"), ("embargoUntil", "2026-02-30")]:
            with self.subTest(field=field, value=value):
                b = bundle(); b["project"]["contribution"][field] = value
                with self.assertRaises(wp.ContractError): wp.validate_bundle(b)

    def test_raw_public_and_accepted_identity_refused(self):
        b = bundle(); b["project"]["contribution"]["rawAccess"] = "public"
        with self.assertRaises(wp.ContractError): wp.validate_bundle(b)
        b = bundle(); b["project"]["identities"][0]["status"] = "accepted"
        with self.assertRaises(wp.ContractError): wp.validate_bundle(b)

    def test_alias_and_published_relation_are_source_records_not_acceptance(self):
        for relation in ("lexical_alias", "published_relationship", "candidate_match"):
            b = bundle(); b["project"]["identities"][0]["relationship"] = relation
            out = wp.inspect_bundle(b)
            self.assertEqual(out["pendingIdentityCount"], 1)
            self.assertFalse(out["scientificAcceptance"])

    def test_malformed_types_ids_ranges_and_hashes_refused(self):
        cases = []
        for kind in range(7):
            b = bundle()
            if kind == 0: b["sources"].append(deepcopy(b["sources"][0]))
            if kind == 1: b["project"]["revision"] = True
            if kind == 2: b["project"]["datasets"][0]["sourceSha256"] = "not-a-hash"
            if kind == 3: b["project"]["temporalEnd"] = "2020-01-01"
            if kind == 4: b["exportedAt"] = "2026-10-24T12:00:00"
            if kind == 5: b["project"]["contribution"]["committed"] = "yes"
            if kind == 6: b["sources"][0]["variables"] = "wrong type"
            cases.append(b)
        for b in cases:
            with self.subTest(bundle=b):
                with self.assertRaises(wp.ContractError): wp.validate_bundle(b)

    def test_preview_copies_only_explicit_text_and_keeps_review_gate(self):
        b = bundle(); original = deepcopy(b)
        out = wp.contribution_preview(b, {"title": "Shareable method"})
        self.assertEqual(out["selectedFields"], {"title": "Shareable method"})
        for private in ("private-project-id", "PRIVATE NOTE VALUE", "private-native-id", "secret_code", "PRIVATE SOURCE EVIDENCE"):
            self.assertNotIn(private, json.dumps(out))
        self.assertEqual(out["status"], "disclosure_review_required")
        self.assertFalse(out["publicationAuthorized"])
        self.assertEqual(b, original)

    def test_preview_refuses_private_or_implicit_fields(self):
        for supplied in ({}, {"notes": "private"}, {"examples": ["private"]}, {"title": ""}):
            with self.subTest(supplied=supplied):
                with self.assertRaises(wp.ContractError): wp.contribution_preview(bundle(), supplied)

    def test_first_winter_requires_age_and_cohort_not_size_or_date(self):
        f = wp.framework_template(bundle()); f.update(lifeStage="first_winter", evidenceType="encounter")
        f["limitations"] = ["Winter date, juvenile life stage, length and weight are available"]
        with self.assertRaisesRegex(wp.ContractError, "marineAgeEvidence"): wp.validate_framework(f)
        f["marineAgeEvidence"] = ["source scale-age record"]
        with self.assertRaisesRegex(wp.ContractError, "cohortEvidence"): wp.validate_framework(f)
        f["cohortEvidence"] = ["source entry-cohort record"]
        self.assertEqual(wp.validate_framework(f)["status"], "awaiting_review")

    def test_mixed_age_hard_call_encounters_are_valid_proposals(self):
        f = wp.framework_template(bundle()); f.update(lifeStage="winter_mixed", evidenceType="encounter", assignmentKind="hard_call")
        out = wp.validate_framework(f)
        self.assertFalse(out["scientificAcceptance"])
        f["usesAssignmentProbabilities"] = True
        with self.assertRaises(wp.ContractError): wp.validate_framework(f)

    def test_direct_survival_needs_separate_source_evidence(self):
        f = wp.framework_template(bundle()); f.update(evidenceType="direct_survival")
        with self.assertRaises(wp.ContractError): wp.validate_framework(f)
        f["survivalEvidence"] = ["unknown"]
        with self.assertRaises(wp.ContractError): wp.validate_framework(f)
        f["survivalEvidence"] = ["Release and detection histories with model assumptions for review"]
        self.assertFalse(wp.validate_framework(f)["scientificAcceptance"])

    def test_core_actions_do_not_access_network(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network")), patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS")):
            wp.inspect_bundle(bundle())
            wp.validate_framework(wp.framework_template(bundle()))
            wp.contribution_preview(bundle(), {"title": "Safe method"})

    def test_both_installed_skill_entrypoints_and_refusal_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "project.json"; p.write_text(json.dumps(bundle()))
            for skill, name, action in [("salmon-workbench-skill", "workbench_bundle.py", "inspect"), ("salmon-research-framework-skill", "research_framework.py", "framework-template")]:
                script = ROOT / "skills" / skill / "scripts" / name
                result = subprocess.run([sys.executable, "-B", str(script), action, "--bundle", str(p)], capture_output=True, text=True, cwd=tmp)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)["ok"])
            b = bundle(); b["project"]["identities"][0]["status"] = "accepted"; p.write_text(json.dumps(b))
            result = subprocess.run([sys.executable, "-B", str(script), action, "--bundle", str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["ok"])

    def test_json_duplicate_nonfinite_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.json"
            for text in ('{"x":1,"x":2}', '{"x":NaN}'):
                p.write_text(text)
                with self.assertRaises(wp.ContractError): wp.read_json(p)
            p.write_text('{}'); link = p.with_name("link.json"); link.symlink_to(p)
            with self.assertRaises(wp.ContractError): wp.read_json(link)

    def test_cli_framework_and_preview_roundtrip_and_repeat_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); project = root / "project.json"; selected = root / "selected.json"
            project.write_text(json.dumps(bundle())); selected.write_text(json.dumps({"title": "Reusable method"}))
            helper = ROOT / "scripts/workbench_project.py"
            args = [sys.executable, "-B", str(helper)]
            before = project.read_bytes()
            template = subprocess.run(args + ["framework-template", "--bundle", str(project)], capture_output=True, check=True)
            frame = root / "frame.json"; frame.write_bytes(template.stdout)
            result = subprocess.run(args + ["framework-check", "--framework", str(frame)], capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)["status"], "awaiting_review")
            call = args + ["contribution-preview", "--bundle", str(project), "--sanitized", str(selected)]
            a = subprocess.run(call, capture_output=True, check=True).stdout
            b = subprocess.run(call, capture_output=True, check=True).stdout
            self.assertEqual(a, b)
            self.assertEqual(project.read_bytes(), before)
            self.assertFalse(json.loads(a)["publicationAuthorized"])


if __name__ == "__main__": unittest.main()
