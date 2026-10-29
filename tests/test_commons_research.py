"""Public JSON CLI controls over fictional compiler-shaped local artifacts."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / 'skills/commons-card/scripts/commons_card.py'
COMMIT = '1' * 40


def write_distribution(root, *, concepts=None, claims=None, mode='full'):
    stamp = {'commons_commit': COMMIT, 'commons_commit_source': 'git',
             'worktree_dirty': False, 'okf_version': '0.2',
             'schema_sha256': '2' * 64, 'compiler_version': '0.1.0'}
    if concepts is None:
        concepts = [{'id': 'concepts/fictional-winter', 'iri': 'urn:commons:card:concepts/fictional-winter',
                     'type': 'Concept', 'title': 'Fictional winter habitat',
                     'description': 'A fictional example about winter habitat.', 'status': 'draft',
                     'generated': {'by': 'process:fictional', 'at': '2026-01-01T00:00:00Z'},
                     'verified': [], 'stale_after': '2026-02-01T00:00:00Z',
                     'sources': [{'id': 'fictional-source', 'resource': 'https://example.org/fictional',
                                  'title': 'Invented fixture; no scientific evidence'}],
                     'relationships': [{'to': 'concepts/fictional-counterexample', 'type': 'contradicts',
                                        'note': 'Fictional disagreement retained, with no resolution implied.'}],
                     'gaps': [{'conflicts': ['Fictional unresolved interpretation.']}]}]
    if claims is None:
        claims = [{'card': 'concepts/fictional-winter', 'n': 1,
                   'claim_id': 'concepts/fictional-winter#1', 'section': 'Fictional example',
                   'text': 'The fictional example asserts winter habitat is relevant.',
                   'footnotes': ['fictional-source'], 'sources': ['fictional-source'],
                   'source_dates': [{'id': 'fictional-source', 'published': '2025', 'last_modified': None}]}]
    artifacts = []
    for name, rows in [('concepts.jsonl', concepts), ('claims.jsonl', claims)]:
        raw = ''.join(json.dumps({**r, 'build': {k:stamp[k] for k in ['commons_commit','okf_version','schema_sha256','compiler_version']}})+'\n' for r in rows).encode()
        (root/name).write_bytes(raw)
        artifacts.append({'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'rows':len(rows)})
    catalog = {'build': stamp, 'mode':mode, 'artifacts':artifacts,
               'counts':{'cards_compiled':len(concepts), 'claims':len(claims)}, 'identifiers_placeholder':'Fixture placeholder IDs'}
    raw = (json.dumps(catalog)+'\n').encode()
    (root/'catalog.json').write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    (root/'MANIFEST.sha256').write_text(''.join(f"{a['sha256']}  {a['path']}\n" for a in artifacts)+f'{digest}  catalog.json\n')
    return digest


class CommonsResearchCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dist = Path(self.tmp.name)
        self.digest = write_distribution(self.dist)

    def call(self, **fields):
        req = {'action':'search', 'distribution_dir': str(self.dist),
               'authorized_local_read':True, 'expected_commit':COMMIT,
               'expected_catalog_sha256':self.digest, 'query':'winter'}
        req.update(fields)
        proc = subprocess.run([sys.executable,str(ADAPTER)],input=json.dumps(req),text=True,capture_output=True,cwd=ROOT,check=True)
        self.assertEqual(proc.stderr, '')
        return json.loads(proc.stdout)

    def test_research_search_returns_recorded_review_and_provenance(self):
        result = self.call()
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['count'],1)
        card = result['results'][0]
        self.assertEqual(card['id'],'concepts/fictional-winter')
        self.assertEqual(card['recorded_status'],'draft')
        self.assertEqual(card['verified'],[])
        self.assertTrue(card['stale'])
        self.assertEqual(card['conflicts'][0]['type'],'contradicts')
        self.assertEqual(result['distribution']['commons_commit'],COMMIT)
        self.assertFalse(result['disclosure_authorized'])
        self.assertEqual(card['citation']['card_path'],'concepts/fictional-winter.md')


    def test_read_preserves_claim_and_source_locators(self):
        result = self.call(action='read',card_id='concepts/fictional-winter')
        self.assertTrue(result['ok'],result)
        card = result['results'][0]
        self.assertEqual(card['claims'][0]['claim_id'],'concepts/fictional-winter#1')
        self.assertEqual(card['claims'][0]['section'],'Fictional example')
        self.assertEqual(card['claims'][0]['sources'],['fictional-source'])
        self.assertEqual(card['sources'][0]['resource'],'https://example.org/fictional')
        self.assertEqual(card['generated']['by'],'process:fictional')
        self.assertEqual(card['review_status'],'not_derived_by_reader')

    def test_absent_and_denied_distribution_never_returns_content(self):
        for change in ({'authorized_local_read':False}, {'distribution_dir':None},
                       {'distribution_dir':str(self.dist/'absent')}):
            with self.subTest(change=change):
                result=self.call(**change)
                self.assertEqual(result['error']['code'],'unavailable')
                self.assertNotIn('fictional-winter',json.dumps(result))

    def test_wrong_commit_and_artifact_tampering_fail_closed(self):
        self.assertEqual(self.call(expected_commit='3'*40)['error']['code'],'commit_mismatch')
        (self.dist/'claims.jsonl').write_text('private-looking sentinel must stay local')
        result = self.call()
        self.assertEqual(result['error']['code'],'integrity_mismatch')
        self.assertNotIn('private-looking',json.dumps(result))

    def test_hash_admission_and_symlink_escape_are_refused(self):
        self.assertEqual(self.call(expected_catalog_sha256=None)['error']['code'],'invalid_input')
        target=self.dist/'outside.jsonl'; target.write_text('EXTERNAL_CONTENT_SENTINEL')
        (self.dist/'claims.jsonl').unlink()
        (self.dist/'claims.jsonl').symlink_to(target)
        result=self.call()
        self.assertEqual(result['error']['code'],'invalid_distribution')
        self.assertNotIn('EXTERNAL_CONTENT',json.dumps(result))

    def test_successful_empty_and_missing_card_remain_distinct(self):
        result=self.call(query='no matching phrase')
        self.assertTrue(result['ok'])
        self.assertEqual(result['count'],0)
        self.assertEqual(result['results'],[])
        self.assertEqual(self.call(action='read',card_id='concepts/absent')['error']['code'],'not_found')

    def test_incoming_conflict_and_draft_are_preserved_without_resolution(self):
        root=json.loads((self.dist/'concepts.jsonl').read_text())
        root.pop('build')
        counter={**root,'id':'concepts/fictional-counterexample','title':'Opposite fictional reading',
                 'relationships':[], 'stale_after':'2099-01-01T00:00:00Z'}
        self.digest=write_distribution(self.dist,concepts=[root,counter])
        result=self.call(action='read',card_id='concepts/fictional-counterexample')
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['results'][0]['conflicts'][0]['direction'],'incoming')
        self.assertFalse(result['results'][0]['stale'])
        self.assertEqual(result['results'][0]['recorded_status'],'draft')

    def test_dirty_or_argument_only_build_and_unreviewed_compiler_are_refused(self):
        for field,value,code in [('worktree_dirty',True,'unverified_build'),
                                 ('commons_commit_source','argument','unverified_build'),
                                 ('compiler_version','99.0','unsupported_distribution')]:
            with self.subTest(field=field):
                self.digest=write_distribution(self.dist)
                catalog=json.loads((self.dist/'catalog.json').read_text())
                catalog['build'][field]=value
                raw=json.dumps(catalog).encode(); (self.dist/'catalog.json').write_bytes(raw)
                self.digest=hashlib.sha256(raw).hexdigest()
                self.assertEqual(self.call()['error']['code'],code)

    def test_search_has_bounded_literal_results_and_no_semantic_equivalence(self):
        card=json.loads((self.dist/'concepts.jsonl').read_text()); card.pop('build')
        cards=[{**card,'id':f'concepts/fictional-{n:02d}'} for n in range(25)]
        self.digest=write_distribution(self.dist,concepts=cards,claims=[])
        result=self.call(limit=2)
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['count'],25)
        self.assertEqual(len(result['results']),2)
        self.assertTrue(result['truncated'])
        self.assertEqual(self.call(query='WINTER')['count'],25)
        self.assertEqual(self.call(query='winter|habitat')['count'],0)

    def test_large_read_refuses_unbounded_output(self):
        claims=[{'card':'concepts/fictional-winter','claim_id':'concepts/fictional-winter#1',
                 'text':'fictional '*100000,'sources':[],'section':'Fixture'}]
        self.digest=write_distribution(self.dist,claims=claims)
        result=self.call(action='read',card_id='concepts/fictional-winter')
        self.assertEqual(result['error']['code'],'output_limit')
        self.assertLess(len(json.dumps(result).encode()),2048)


if __name__ == '__main__':
    unittest.main()
