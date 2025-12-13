# Internationalization Strategy – DCP v2

Key-based JSON bundles stored alongside the service. Supported locales: `en` (default), `pt-BR`, `es`.

## Server negotiation
- Inspect `Accept-Language` header; pick the best-supported locale; fallback to `en`.
- Persist `language` on `decision` to keep rendering consistent across inbox and notifications.
- Admin UI exposes a language switch that sets a user preference (cookie/local storage) but server still guards fallback logic.

## Bundle storage
- Files under `/i18n/<locale>.json`.
- Namespaced keys: `decision.*`, `action.*`, `status.*`, `common.*`, `messages.*`.
- Backend responses avoid embedding translated strings except where user-facing (e.g., notifications); otherwise send keys and let the UI translate.

## Example
Key `decision.approve`:
- en: "Approve"
- pt-BR: "Aprovar"
- es: "Aprobar"

## Operational notes
- Use strict key linting during CI to ensure all locales are in sync.
- Keep messages short; avoid model-generated translations in runtime paths—pre-translate and review.
