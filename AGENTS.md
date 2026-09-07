# Cortex public documentation

This is the Mintlify site for `docs.cortex.foundation`. Edit the site at the
repository root, not in `apps/docs`. Preview and validation commands are in
`README.md`.

- Keep product copy in English and use the Cortex product names and domains.
- Do not publish authentication/session internals, credentials, private API
  routes, farm details, or backend operator runbooks.
- Preserve the Home + Documentation navbar and ink-on-cream CTAs.
- Keep every navigation slug backed by a page and every problem page's
  `type` URL on `https://docs.cortex.foundation/problems/{code}`.
- Run `node scripts/check-docs-site.mjs` and
  `bash scripts/tests/check-docs-site.test.sh`, then
  `npm exec --yes --package=mint@4.2.876 -- mint validate` before committing.
- For error-code or endpoint changes, also run the checker with a backend
  checkout as its first argument. Coordinate the two PRs; the backend owns
  the API contract and checks this repository in its CI.
- Do not change the Mintlify integration, custom domain, or DNS without an
  explicit request.
