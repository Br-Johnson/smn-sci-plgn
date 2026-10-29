# /// script
# requires-python = ">=3.10"
# dependencies = ["metasalmonpy[eml] @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.6.0"]
# ///
"""Fictional local SDK recipe. No arbitrary research inputs or publication."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pandas as pd
import metasalmonpy as ms
from metasalmonpy import sdp_schema
import yaml

HERE = Path(__file__).resolve().parent
BASE = "https://example.org/fictional-sdp/"


def draft(work: Path) -> dict:
    work.mkdir(parents=True)
    shutil.copyfile(HERE / "fictional-counts.csv", work / "original.csv")
    frame = pd.read_csv(work / "original.csv", keep_default_na=False)
    ms.create_sdp({"counts": frame}, work / "draft-sdp", dataset_id="fictional-counts",
                  seed_semantics=False, llm_assess=False, check_updates=False)
    try:
        ms.validate_salmon_datapackage(work / "draft-sdp", require_iris=True)
    except ValueError as exc:
        return {"stage": "draft", "sdk_version": ms.__version__, "strict_draft_refused": True,
                "strict_draft_message": str(exc), "source_sha256": hashlib.sha256((work / "original.csv").read_bytes()).hexdigest(),
                "publication_performed": False}
    raise RuntimeError("The incomplete draft unexpectedly passed strict validation")


def review(work: Path) -> dict:
    if (work / "original.csv").read_bytes() != (HERE / "fictional-counts.csv").read_bytes():
        raise ValueError("This affirmation applies only to the unchanged bundled fictional CSV")
    reviewed = work / "reviewed-sdp"
    shutil.copytree(work / "draft-sdp", reviewed)
    ms.set_sdp_dataset(reviewed, title="Fictional adult count sums",
                       description="An invented two-row exercise; no real salmon observations.",
                       creator="Fictional Recipe Authors", contact_name="Fictional Recipe Authors",
                       contact_email="nobody@example.invalid", license="CC-BY-4.0",
                       source_citation="Fictional SDP recipe. Synthetic fixture; no field observations.",
                       provenance_note="All values and non-unit concepts are invented solely for software testing.", quiet=True)
    ms.set_sdp_table(reviewed, "counts", description="One invented aggregate per fictional site.",
                     observation_unit="Fictional site count observation", observation_unit_iri=BASE + "SiteCount", primary_key="site", quiet=True)
    ms.set_sdp_column(reviewed, "site", table="counts", column_description="A fictional site code, without a real location or stock identity.",
                      required=True, quiet=True)
    ms.set_sdp_column(reviewed, "adult_count_sum", table="counts", column_description="Sum of invented replicate counts restricted to fictional adults.",
                      term_iri=BASE + "AdultCountSum", term_type="skos_concept", property_iri=BASE + "Count", entity_iri=BASE + "Salmon",
                      unit_iri="http://qudt.org/vocab/unit/COUNT", unit_label="Count",
                      constraint_iri=BASE + "Adult", statistical_modifier_iri=BASE + "Sum", quiet=True)
    mapping = yaml.safe_load((HERE / "fictional-eml-mapping.yml").read_text())
    mapping["source_provenance"]["supporting_document"]["sha256"] = hashlib.sha256((work / "original.csv").read_bytes()).hexdigest()
    (reviewed / "metadata/eml-mapping.yml").write_text(yaml.safe_dump(mapping, sort_keys=False))
    evidence = pd.read_csv(HERE / "fictional-evidence.csv", keep_default_na=False)
    evidence["source_artifact_sha256"] = hashlib.sha256((HERE / "fictional-evidence.csv").read_bytes()).hexdigest()
    def no_lookup(*args, **kwargs):
        raise RuntimeError("The complete fictional evidence must not trigger a remote vocabulary lookup")
    ms.write_sdp_semantic_closure(reviewed, evidence=evidence, search_fn=no_lookup, quiet=True)
    ms.validate_salmon_datapackage(reviewed, require_iris=True)
    rewritten = work / "rewritten-sdp"
    shutil.copytree(reviewed, rewritten)
    package = ms.read_salmon_datapackage(rewritten)
    ms.write_salmon_datapackage(resources=package["resources"], dataset_meta=package["dataset"], table_meta=package["tables"],
                                dict_df=package["dictionary"], codes=package["codes"], path=str(rewritten), overwrite=True, prune=False)
    ms.validate_salmon_datapackage(rewritten, require_iris=True)
    exported = ms.write_eml_from_sdp(rewritten)
    return {"stage": "reviewed-fictional-fixture", "sdk_version": ms.__version__, "strict_reviewed": True,
            "strict_rewritten": True, "eml": {"path": str(exported["path"]), "xsd_valid": exported["validation"]},
            "publication_performed": False, "real_research_approval": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("draft", "review"))
    parser.add_argument("work", type=Path)
    parser.add_argument("--confirm-fictional-semantics", action="store_true", help="Human affirmation of the bundled fictional fixture only; not real research or publication approval")
    args = parser.parse_args()
    try:
        if ms.__version__ != "0.6.0":
            raise ValueError("This recipe is pinned to released metasalmonpy v0.6.0")
        sdp_schema.set_sdp_schema_source("vendored")
        if args.stage == "review" and not args.confirm_fictional_semantics:
            raise ValueError("human_confirmation_required: inspect the fictional metadata, qualifiers and evidence, then explicitly affirm this fixture with --confirm-fictional-semantics")
        with contextlib.redirect_stdout(sys.stderr):
            result = draft(args.work) if args.stage == "draft" else review(args.work)
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "publication_performed": False}))
        return 1
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
