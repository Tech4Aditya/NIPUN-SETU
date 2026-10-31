"""Authenticated smoke test for NIPUNSetu analytics APIs.
Run: python scripts/smoke-test.py [BASE_URL]
Default BASE_URL: http://127.0.0.1:8000
"""
import sys
import urllib.request
import urllib.error
import json

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8000'

def request(path, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(BASE + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode())

login = request('/api/auth/login', {'email': 'block@demo.in', 'password': 'block123'})
token = login['access_token']
paths = [
    '/api/analytics/predictions',
    '/api/analytics/impact',
    '/api/analytics/cohorts',
    '/api/analytics/ml-validation',
    '/api/analytics/competency-outcomes',
    '/api/analytics/intervention-effectiveness',
    '/api/validation/readiness',
    '/api/import/template',
    '/api/public-data/overview',
    '/api/comparison/overview?grade=3&domain=reading',
]
for path in paths:
    result = request(path, token=token)
    assert isinstance(result, dict), f'{path} did not return an object'
    print(f'PASS {path}')
public = request('/api/public-data/overview', token=token)
assert public['total_benchmarks'] >= 35
assert public['source_counts']['ASER2024'] >= 10
assert public['source_counts']['PARAKH2024'] >= 10
comparison_req = urllib.request.Request(BASE + '/api/comparison/template', headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(comparison_req, timeout=10) as response:
    assert response.status == 200 and b'observation_id,school_id' in response.read()
reference_req = urllib.request.Request(BASE + '/api/comparison/reference-template', headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(reference_req, timeout=10) as response:
    assert response.status == 200 and b'assessment_instrument' in response.read()
print('PASS comparison CSV templates')
template_req = urllib.request.Request(BASE + '/api/public-data/template', headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(template_req, timeout=10) as response:
    assert response.status == 200 and b'source_id,geography_name' in response.read()
print('Public evidence registry verified:', public['total_benchmarks'], 'benchmarks across', len(public['sources']), 'sources')
print('PASS /api/public-data/template (CSV)')
print('All NIPUNSetu API smoke tests passed.')
