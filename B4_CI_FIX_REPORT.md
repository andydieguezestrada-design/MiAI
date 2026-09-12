# B4 CI Fix Report

## Root cause
The GitHub Actions API validation step in the failing commit still asserted the old stable version `0.11.1` while `api/main.py` had already been advanced to `0.12.0-b4`.

This caused:

`AssertionError: 0.12.0-b4`

## Fix
The API validation workflow now validates the current B4 version:

`0.12.0-b4`

## Local validation
- Python compileall: PASS
- Full pytest: 44 passed
- C++ CMake Release build: PASS
- API import/version validation: PASS (`MiAI Core 0.12.0-b4`)
- API smoke tests: 10 passed
