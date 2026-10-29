"""Recorded owner-discovery behavior through source JSON CLIs, without network."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
import io,json,runpy,socket,sys
from urllib.error import HTTPError,URLError
from unittest.mock import patch
class Response(io.BytesIO):
    status=200
    headers={'Content-Type':'text/html; charset=utf-8'}
    def geturl(self): return sys.argv[3]
def transport(opener,request,*args,**kwargs):
    if sys.argv[2]=='dns': raise URLError(socket.gaierror('FICTIONAL DNS DETAIL'))
    if sys.argv[2]=='404': raise HTTPError(request.full_url,404,'FICTIONAL HTTP DETAIL',{},io.BytesIO(b'FICTIONAL ERROR BODY'))
    return Response(b'<html><title>Fictional owner documentation</title><p>Source context only.</p></html>')
with patch('urllib.request.OpenerDirector.open',transport):
    runpy.run_path(sys.argv[1],run_name='__main__')
'''

def run(skill, script, request, mode='ok', final='https://www.fisheries.noaa.gov/inport/item/17904'):
    proc = subprocess.run([sys.executable,'-B','-c',HARNESS,
                           str(ROOT/'skills'/skill/'scripts'/script),mode,final],
                          input=json.dumps(request),text=True,capture_output=True,check=True)
    return json.loads(proc.stdout)

class SourceAvailabilityTests(unittest.TestCase):
    def test_noaa_owner_metadata_is_an_explicit_discovery_action(self):
        out=run('noaa-sps-skill','noaa_sps.py',{'action':'metadata'})
        self.assertTrue(out['ok'])
        self.assertEqual(out['url'],'https://www.fisheries.noaa.gov/inport/item/17904')
        self.assertEqual(out['discovery_scope'],'owner_metadata_only')
        self.assertEqual(out['records']['title'],'Fictional owner documentation')

    def test_noaa_home_preserves_same_origin_apex_page_provenance(self):
        final='https://www.webapps.nwfsc.noaa.gov/apex/f?p=261:1::::::'
        out=run('noaa-sps-skill','noaa_sps.py',{'action':'home'},final=final)
        self.assertTrue(out['ok'])
        self.assertEqual(out['url'],final)
        self.assertEqual(out['retrieval'][0]['requested_url'],'https://www.webapps.nwfsc.noaa.gov/sps')
        self.assertEqual(out['retrieval'][0]['final_origin'],'https://www.webapps.nwfsc.noaa.gov')

    def test_unavailable_sources_retain_typed_failure_and_owner_discovery(self):
        for skill,script,action,mode,code,owner in (
            ('noaa-sps-skill','noaa_sps.py','home','404','not_found','https://www.fisheries.noaa.gov/inport/item/17904'),
            ('critfc-crosswalk-skill','critfc_crosswalk.py','rest_root','dns','dns_error',
             'https://critfc.org/fish-and-watersheds/fishery-science/data-resources/columbia-basin-salmon-and-steelhead-crosswalk-project/'),
        ):
            with self.subTest(source=skill):
                out=run(skill,script,{'action':action},mode=mode)
                self.assertFalse(out['ok'])
                self.assertEqual(out['error']['code'],code)
                self.assertEqual(out['outcome'],'unavailable')
                self.assertEqual(out['availability']['owner_documentation'],owner)
                self.assertEqual(out['availability']['fallback_scope'],'owner_documentation_only')
                self.assertFalse(out['availability']['records_returned'])
                self.assertNotIn('FICTIONAL',json.dumps(out))

if __name__=='__main__':unittest.main()
