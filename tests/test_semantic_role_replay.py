"""Role-boundary controls: authored expectations versus actual package events.

These fixtures test plumbing and handoff rules, not a model's scientific skill.
"""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'evals/sdp-semantic-review/replay_role_boundaries.py'


def load_replay():
    spec=importlib.util.spec_from_file_location('role_replay',SCRIPT)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RoleReplayOracles(unittest.TestCase):
    def test_wrong_raw_count_event_fails_the_adjusted_efs_oracle(self):
        replay=load_replay()
        case=next(c for c in replay.load_fixture()['cases'] if c['case_id']=='efs_preserves_adjusted_variable')
        observed=[{'type':'assessment','role':'variable','decision':'accept'},
                  {'type':'selection','role':'variable','decision':'accept','iri':'https://example.org/fixture/RawFemaleCount'}]
        result=replay.evaluate([case],{case['case_id']:observed})
        self.assertEqual(result['status'],'fail')
        self.assertTrue(any(f['bucket']=='forbidden' for f in result['failures']))


@unittest.skipUnless(importlib.util.find_spec('metasalmonpy'), 'Requires actual pinned metasalmonpy package profile; no fake package replay')
class ReleasedRoleReplay(unittest.TestCase):
    def test_authored_answers_pass_real_packet_ingestion_and_wrong_efs_fails_oracle(self):
        result=load_replay().controls()
        self.assertEqual(result['status'],'pass',result)
        self.assertEqual(len(result['correct_answers']['cases']),10)
        self.assertEqual(result['wrong_answers']['efs_preserves_adjusted_variable']['oracle_status'],'fail')
        self.assertTrue(result['proposal_off_shortlist_refused'])
        self.assertTrue(result['proposal_names_absent_from_shortlists'])
        self.assertIn({'type':'selection','role':'variable','decision':'accept',
                       'iri':'https://example.org/fixture/RawFemaleCount'},
                      result['wrong_answers']['efs_preserves_adjusted_variable']['events'])

    def test_changed_packet_input_fails_the_recorded_fingerprint(self):
        replay=load_replay()
        case=copy.deepcopy(replay.load_fixture()['cases'][0])
        case['description']='A changed synthetic field that was not reviewed in the pinned fixture.'
        with self.assertRaisesRegex(AssertionError,'packet fingerprint changed'):
            replay.replay(case)

    def test_packet_preserves_source_scope_review_status_and_unapplied_metadata(self):
        replay=load_replay()
        fixture=replay.load_fixture()
        by_id={c['case_id']:c for c in fixture['cases']}
        efs=replay.replay(by_id['efs_preserves_adjusted_variable'])
        candidate=next(c for c in efs['packet_candidates'] if c['iri']=='https://w3id.org/psc/vocab/concept/PSC-CV-000035')
        self.assertEqual(candidate['extra']['source_release'],'v0.1.0-alpha.6')
        self.assertEqual(candidate['extra']['review_status'],'provisional; domain-review-pending')
        self.assertEqual(efs['metadata_values']['term_iri'],[None])
        female=replay.replay(by_id['sample_female_value_needs_application_review'])
        extra=female['packet_candidates'][0]['extra']
        self.assertEqual(extra['source_version'],'http://vocab.nerc.ac.uk/collection/S10/current/S102/2/')
        self.assertEqual(extra['source_sha256'],'b0e884a4593d9791df61f8f1c7dacbe650c90a30637f9e3dbfc1fac6087d35ff')
        self.assertIn('Sample-based',extra['application_scope'])
        self.assertEqual(female['events'],[{'type':'assessment','role':'constraint','decision':'review'}])
        mapping=replay.replay(by_id['close_mapping_is_not_equivalence'])
        evidence=mapping['packet_candidates'][0]['extra']
        self.assertEqual(evidence['mapping_predicate'],'skos:broadMatch')
        self.assertEqual(evidence['mapping_source'],'https://w3id.org/smn/Abundance')
        self.assertEqual(mapping['metadata_values']['property_iri'],[None])



if __name__ == '__main__':
    unittest.main()
