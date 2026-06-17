# Lawhook SDK Parity Review

This review compares the Python SDK in `lawhook/` and the TypeScript SDK in `lawhook-typescript/` for purpose, tone, public API shape, and functionality.

No builds, tests, or code changes were performed during this review.

## Review Findings

### High Severity

- Python subscriptions are broken because `Subscription` is not decorated with `@dataclass`, but `Subscription.from_dict()` instantiates it with keyword args. Any Python call returning a subscription will fail with `TypeError: Subscription() takes no arguments`; TypeScript works here. See `lawhook/models.py:63` and `lawhook/client.py:237`.

- TypeScript exposes tested SDK behavior, but Python has no equivalent SDK tests in the repo. This means parity is not enforceable across `create_key`, subscription CRUD, change listing/search, error mapping, date parsing, and rate-limit handling. See `lawhook-typescript/tests/client.test.ts:89`.

### Medium Severity

- Python package metadata uses the root app README, which describes the whole platform and still says Python/TypeScript SDKs are Phase 2, while the SDKs already exist. This makes Python package purpose/tone inconsistent with the TypeScript package description. See `pyproject.toml:18`, `README.md:70`, and `README.md:299`.

- TypeScript package has no SDK README, while Python points to the root README. Consumers of the npm SDK will get less onboarding/context than PyPI consumers, so the tone and docs are not identical. See `lawhook-typescript/package.json:14`.

- Package metadata is not aligned: Python URLs point to GitHub for homepage/docs/repo/issues, while TypeScript uses GitHub for repo but `https://lawhook.dev` for homepage. See `pyproject.toml:57` and `lawhook-typescript/package.json:35`.

### Low Severity

- The SDK APIs are functionally similar but not literally identical in naming style. Python uses `api_key`, `base_url`, `create_key`, `list_keys`, `webhook_url`; TypeScript uses idiomatic `apiKey`, `baseUrl`, `createKey`, `listKeys`, `webhookUrl`. That is normal for each language, but not literally identical. See `lawhook/client.py:67` and `lawhook-typescript/src/client.ts:55`.

## Parity Summary

- Both SDKs target the same purpose: official Lawhook SDKs for the Regulatory & Compliance Change Monitoring API.

- Both expose the same major namespaces: `auth`, `subscriptions`, and `changes`.

- Both cover the same core methods: create/list/revoke API keys, create/list/get/update/delete/pause/resume subscriptions, list/get/search changes.

- Both map the same error hierarchy: auth, not found, validation, rate limit, server, connection.

- The biggest blocker to parity is the broken Python `Subscription` model plus missing Python test coverage.

## Recommended Next Steps

1. Fix `Subscription` in `lawhook/models.py` by making it a dataclass or otherwise adding a matching constructor.

2. Add Python SDK tests mirroring `lawhook-typescript/tests/client.test.ts`.

3. Create SDK-specific README files for both packages or update the root README so package consumers get accurate SDK-focused documentation.

4. Align package metadata URLs and descriptions across `pyproject.toml` and `lawhook-typescript/package.json`.
