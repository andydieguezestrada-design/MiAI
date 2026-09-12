"""Owner-only administration surface for MiAI Core.

This package implements the Owner Token pairing, audit/system logging,
cost-policy enforcement, provider/model switching and signed-release
lifecycle consumed by the MiAI Admin Android app. None of this existed in
V0.12-B4 — the Core exposed only the `/ai/*` inference API. `release.json`
already declared this as the future contract for Android clients; this
package is that contract, implemented.
"""
