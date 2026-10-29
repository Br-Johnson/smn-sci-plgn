"""Behavioral regressions at the normalizer's public JSON CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / "skills/salmon-entity-normalizer-skill/scripts/normalize_entities.py"


class SpeciesNormalizationTests(unittest.TestCase):
    def normalize(self, text: str) -> dict:
        response = subprocess.run(
            [sys.executable, str(NORMALIZER)],
            input=json.dumps({"text": text}),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(response.returncode, 0, response.stderr)
        result = json.loads(response.stdout)
        self.assertTrue(result["ok"], result)
        return result

    def test_cohort_question_does_not_introduce_coho(self) -> None:
        result = self.normalize("Compare cohort survival among years.")
        self.assertEqual(result["species"], [])

    def test_alias_substrings_do_not_introduce_species(self) -> None:
        for text in ("A chummy cohort.", "Compare silver salmonella strains."):
            with self.subTest(text=text):
                self.assertEqual(self.normalize(text)["species"], [])

    def test_explicit_species_match_next_to_punctuation_and_preserve_input(self) -> None:
        text = "Assess (COHO), then coho's cohort survival."
        result = self.normalize(text)
        self.assertEqual([s["canonical_name"] for s in result["species"]], ["Coho salmon"])
        self.assertEqual(result["input"]["text"], text)

    def test_explicit_multi_species_question_keeps_both_species(self) -> None:
        result = self.normalize("Compare Chinook and sockeye escapement.")
        self.assertEqual(
            [s["canonical_name"] for s in result["species"]],
            ["Chinook salmon", "Sockeye salmon"],
        )

    def test_scientific_abbreviation_and_multiword_alias_remain_supported(self) -> None:
        for text in ("Assess O. kisutch.", "Assess silver salmon."):
            with self.subTest(text=text):
                self.assertEqual(
                    [s["canonical_name"] for s in self.normalize(text)["species"]],
                    ["Coho salmon"],
                )

    def test_unknown_species_remains_unresolved_and_identity_slice_stays_a_hint(self) -> None:
        result = self.normalize("Compare Arctic grayling survival.")
        self.assertEqual(result["species"], [])
        self.assertEqual(result["identity_hints"], [])
        self.assertEqual(result["identity_slice"]["authority"], "non-authoritative")


if __name__ == "__main__":
    unittest.main()
