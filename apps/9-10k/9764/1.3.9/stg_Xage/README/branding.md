# Branding

Splunk’s app launcher reads icons from **`static/` at the app root** (not `appserver/static/`). Copies also live in `appserver/static/` for dashboards. All `appIcon*` files are **opaque 24-bit RGB** (navy + Xage cube) so the circular launcher crop has a fill and does not fall back to the generic “App” glyph.

| File | Size | Where Splunk uses it |
|---|---|---|
| `static/appIcon.png` / `_2x` | 36 / 72 | Apps listing (light tile) |
| `static/appIconAlt.png` / `_2x` | 36 / 72 | Dark Splunk nav |
| `static/appLogo.png` / `_2x` | 160×40 / 320×80 | In-app header |

The **app icon** is the Xage cube on navy (readable at 36px). The **app logo** is the partnership lockup:

- **SAIC** — official italic wordmark from saic.com
- **STG** — letter-spaced under SAIC
- **Xage cube** — official isometric mark

Dashboard titles do **not** start with “Xage …” so the in-app letter avatars are unique (O, A, P, D, S, I, E).

Masters live in `appserver/static/branding/`.
