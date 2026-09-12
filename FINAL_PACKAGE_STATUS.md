# MiAI — Final Package Status

'
    'Runtime: **0.12.0-b4**
'
    'Release channel: **stable-candidate**
'
    'Update policy: **manual-owner-approval**
'
    'Automatic update: **disabled**

'
    '## CI/API validation hardening
'
    '- API version is sourced from `python/core/version.py`.
'
    '- CI compares the API, version source and `release.json` instead of hard-coding an old version.
'
    '- `/system/version` exposes the release contract for future Android clients.
'
    '- Release-control regression tests are included.

'
    '## Validation performed on this package
'
    '- Python tests: 46 passed.
'
    '- Python compileall: passed.
'
    '- API import/version: passed.
'
    '- C++ Release build: passed.
'
    '- API smoke tests: 12 passed.
'
    