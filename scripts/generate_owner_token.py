#!/usr/bin/env python3
"""Generate (or rotate) the MiAI Admin Owner Token + PIN.

This is how you get the payload that the MiAI Admin Android app asks for on
its "Vincular MiAI Admin" screen. Run this ON the machine/server where MiAI
Core runs (it writes directly to the Core's admin database).

Usage:
    python scripts/generate_owner_token.py --url https://mi-core.ejemplo.com
    python scripts/generate_owner_token.py --url http://192.168.1.50:8000 --rotate

The token is only ever stored hashed — if you lose it, rotate it, you cannot
recover the original value.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.admin.auth import generate_credentials, has_credentials, set_credentials  # noqa: E402
from python.admin.store import AdminStore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--url",
        required=True,
        help="URL donde la app Android alcanzará este Core, ej: https://192.168.1.50:8000",
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Genera un token/pin nuevos aunque ya exista uno (invalida el anterior).",
    )
    args = parser.parse_args()

    store = AdminStore()
    if has_credentials(store) and not args.rotate:
        print(
            "Ya existe un Owner Token configurado para este Core.\n"
            "Usa --rotate si quieres generar uno nuevo (esto invalida el anterior "
            "y tendrás que volver a vincular la app).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    token, pin = generate_credentials()
    set_credentials(store, token, pin)
    store.log_audit("admin:token_rotated" if args.rotate else "admin:token_generated", level="security")

    payload = {"url": args.url.strip().rstrip("/"), "token": token, "pin": pin}
    print(json.dumps(payload, separators=(",", ":")))
    print(
        "\n⚠️  Guarda este token en un lugar seguro — no se puede recuperar, solo rotar.\n"
        "Pega el JSON de arriba (la línea de una sola línea) en la app MiAI Admin, "
        "pantalla 'Vincular MiAI Admin'.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
