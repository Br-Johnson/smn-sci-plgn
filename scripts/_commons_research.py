"""Read an explicitly admitted, hash-pinned upstream compiler distribution.

No source acquisition, compilation, status derivation or contribution occurs.
The reader consumes the compiler's JSON artifacts and preserves their evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_RESULTS = 20
MAX_OUTPUT_BYTES = 64 * 1024
COMPILER_VERSION = '0.1.0'


class DistributionError(Exception):
    """A bounded refusal without source content or filesystem diagnostics."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def refuse(code: str, message: str) -> None:
    raise DistributionError(code, message)


def read_bytes(root: Path, name: str) -> bytes:
    path = root / name
    if path.is_symlink() or path.resolve().parent != root:
        refuse('invalid_distribution', 'Distribution artifacts must be regular files inside the admitted directory.')
    if not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        refuse('unavailable', 'Required artifact is absent or exceeds the local reader limit.')
    return path.read_bytes()


def load_distribution(request: dict) -> tuple[dict, list[dict], list[dict]]:
    """Verify only the catalog and the two research artifacts this reader consumes."""
    if request.get('authorized_local_read') is not True:
        refuse('unavailable', 'Authorize local reading for this research task before opening the distribution.')
    value = request.get('distribution_dir')
    if not isinstance(value, str) or not value.strip():
        refuse('unavailable', 'An explicitly admitted local distribution_dir is required; no source is acquired automatically.')
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        refuse('unavailable', 'The admitted local distribution is unavailable.')
    expected_commit = request.get('expected_commit')
    expected_hash = request.get('expected_catalog_sha256')
    if not isinstance(expected_commit, str) or not re.fullmatch('[0-9a-f]{40}', expected_commit):
        refuse('invalid_input', 'expected_commit must be an exact 40-character lowercase Git commit.')
    if not isinstance(expected_hash, str) or not re.fullmatch('[0-9a-f]{64}', expected_hash):
        refuse('invalid_input', 'expected_catalog_sha256 must be a trusted 64-character lowercase SHA-256.')
    catalog_raw = read_bytes(root, 'catalog.json')
    if hashlib.sha256(catalog_raw).hexdigest() != expected_hash:
        refuse('integrity_mismatch', 'The catalog does not match the admitted SHA-256; no content was returned.')
    catalog = json.loads(catalog_raw)
    stamp = catalog['build']
    if stamp.get('commons_commit') != expected_commit:
        refuse('commit_mismatch', 'The distribution does not name the requested immutable Commons commit.')
    if stamp.get('compiler_version') != COMPILER_VERSION:
        refuse('unsupported_distribution', 'This reader supports the reviewed upstream compiler version 0.1.0 only.')
    if stamp.get('commons_commit_source') != 'git' or stamp.get('worktree_dirty') is not False:
        refuse('unverified_build', 'A clean Git-derived build is required; argument-only or dirty provenance is not accepted.')
    if catalog.get('mode') not in ('full', 'promote'):
        refuse('unsupported_distribution', 'Unknown distribution mode; no disclosure decision can be inferred.')
    manifest = {}
    for line in read_bytes(root, 'MANIFEST.sha256').decode('utf-8').splitlines():
        if not line:
            continue
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)', line)
        if not match or match[2] in manifest:
            refuse('invalid_distribution', 'The manifest has an invalid or duplicate entry.')
        manifest[match[2]] = match[1]
    if manifest.get('catalog.json') != expected_hash:
        refuse('integrity_mismatch', 'The manifest does not cover the pinned catalog.')
    records = {}
    artifacts = {a['path']: a for a in catalog['artifacts']}
    slim = {k:stamp[k] for k in ('commons_commit','okf_version','schema_sha256','compiler_version')}
    for name in ('concepts.jsonl','claims.jsonl'):
        artifact = artifacts[name]
        raw = read_bytes(root, name)
        digest = hashlib.sha256(raw).hexdigest()
        if artifact['sha256'] != digest or manifest.get(name) != digest or artifact['bytes'] != len(raw):
            refuse('integrity_mismatch', 'A research artifact does not match the pinned catalog and manifest.')
        rows = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
        if len(rows) != artifact['rows'] or any(row.get('build') != slim for row in rows):
            refuse('integrity_mismatch', 'Research row counts or build stamps differ from the pinned catalog.')
        records[name] = rows
    concepts = records['concepts.jsonl']
    if len({row['id'] for row in concepts}) != len(concepts):
        refuse('invalid_distribution', 'Duplicate card identifiers are not accepted.')
    if catalog['counts']['cards_compiled'] != len(concepts) or catalog['counts']['claims'] != len(records['claims.jsonl']):
        refuse('integrity_mismatch', 'Catalog counts differ from the research artifacts.')
    return {**stamp, 'mode':catalog['mode'], 'catalog_sha256':expected_hash,
            'integrity':'catalog_and_research_artifacts_verified',
            'authenticity':'caller_admitted_hash_not_a_signature',
            'identifiers_placeholder':catalog.get('identifiers_placeholder')}, concepts, records['claims.jsonl']


def card_view(card: dict, all_cards: list[dict], commit: str) -> dict:
    """Carry recorded evidence without deriving scientific acceptance."""
    value = card.get('stale_after')
    stale = None
    if isinstance(value, str):
        try:
            instant = datetime.fromisoformat(value.replace('Z','+00:00'))
            if instant.tzinfo:
                stale = datetime.now(timezone.utc) >= instant
        except ValueError:
            pass
    conflicts = [r for r in card.get('relationships') or [] if r.get('type') == 'contradicts']
    conflicts += [{'from':other['id'], **r, 'direction':'incoming'} for other in all_cards
                  for r in other.get('relationships') or [] if r.get('type') == 'contradicts' and r.get('to') == card['id']]
    return {key:card.get(key) for key in ('id','iri','title','description','generated','verified','sources','relationships','gaps')} | {
        'recorded_status':card.get('status'), 'review_status':'not_derived_by_reader',
        'stale_after':value, 'stale':stale, 'conflicts':conflicts,
        'verification_limitations':['Recorded verification is preserved, not independently attested.',
                                    'The compiled concept view does not expose a claim-level review verdict.'],
        'citation':{'card_path':card['id']+'.md', 'commons_commit':commit,
                    'compiled_locator':'concepts.jsonl:'+card['id']}}


def research(request: dict) -> dict:
    """Answer a local search/read request; refusals contain no evidence payload."""
    try:
        distribution, cards, claims = load_distribution(request)
        action = request['action']
        limit = request.get('limit', 10)
        if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
            refuse('invalid_input', 'limit must be an integer from 1 to 20.')
        if action == 'search':
            query = request.get('query')
            if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
                refuse('invalid_input', 'query must be a nonempty literal phrase of at most 200 characters.')
            # Literal case-insensitive discovery, not semantic ranking or equivalence.
            phrase = query.strip().casefold()
            found = [c for c in cards if phrase in ' '.join(str(c.get(k) or '') for k in ('id','title','description','tags')).casefold()
                     or any(claim.get('card') == c['id'] and phrase in str(claim.get('text','')).casefold() for claim in claims)]
        else:
            card_id = request.get('card_id')
            if not isinstance(card_id, str) or not card_id:
                refuse('invalid_input', 'read requires an exact card_id from search.')
            found = [c for c in cards if c['id'] == card_id]
            if not found:
                refuse('not_found', 'The requested card is absent from the admitted distribution.')
        results = [card_view(c,cards,distribution['commons_commit']) for c in sorted(found,key=lambda c:c['id'])[:limit]]
        if action == 'read':
            selected = [c for c in claims if c.get('card') == found[0]['id']]
            results[0]['claims'] = selected[:MAX_RESULTS]
            results[0]['claim_count'] = len(selected)
            results[0]['claims_truncated'] = len(selected) > MAX_RESULTS
        result = {'ok':True, 'action':action, 'distribution':distribution, 'count':len(found),
                'truncated':len(found)>limit, 'results':results,
                'disclosure_authorized':False, 'contribution_performed':False,
                'limitations':['Local evidence retrieval does not approve scientific claims, mappings or publication.',
                               'Only catalog and consumed research artifacts are verified; no source URLs are fetched.']}
        if len(json.dumps(result, indent=2, sort_keys=True).encode('utf-8')) > MAX_OUTPUT_BYTES:
            refuse('output_limit', 'The selected evidence exceeds 64 KiB. Narrow the search or inspect the admitted artifacts locally; no bulk content was emitted.')
        return result
    except DistributionError as exc:
        return {'ok':False, 'error':{'code':exc.code,'message':str(exc)}}
    except PermissionError:
        return {'ok':False, 'error':{'code':'unavailable','message':'The admitted local distribution cannot be read with current permissions.'}}
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return {'ok':False, 'error':{'code':'invalid_distribution','message':'The admitted distribution is malformed or incomplete; no content was returned.'}}
