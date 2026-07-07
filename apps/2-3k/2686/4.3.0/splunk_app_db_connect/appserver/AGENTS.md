## Overview

Frontend UI for Splunk DB Connect. Built with React 16, MobX 2 for state management, Webpack 4, and
Splunk UI libraries (`@splunk/react-ui`, `@splunk/themes`). Styles use PostCSS with `.pcssm`
modules.

## Structure

```
appserver/
  templates/          # Splunk HTML templates that load the JS pages
    configuration.html
    data_lab.html
    ftr.html
  static/
    src/              # Source code
      bootstrap.jsx   # App entry point: polyfills, FTR redirect check
      components/     # Reusable React components
      pages/          # Route-level page containers
      stores/         # MobX observable stores
      utils/          # Shared utilities
      constants/      # Enums and constants
      schemas/        # Validation schemas
      shim/           # Compatibility shims (ACE editor, VisualizationLoader)
      config.test.js  # Test configuration (injected by Karma)
      setupTests.js   # Test setup
    styles.pcss       # Global styles
    monitoring.css    # Monitoring page styles
    monitoring.js     # Monitoring page script
    swc-dbx/          # Symlink to swc-dbx/dist (Splunk Web Components)
```

## Pages

Each page has `Index.jsx` (entry), `components/`, `layout(s)/`, and `views/`:

| Page                       | URL             | Purpose                                                          |
|----------------------------|-----------------|------------------------------------------------------------------|
| `pages/data_lab/`          | `data_lab`      | Inputs, Outputs, Lookups management                              |
| `pages/database_settings/` | `configuration` | Identities, Connections, Drivers, Keystore, Settings, HA Cluster |
| `pages/ftr/`               | `ftr`           | First Time Run setup wizard                                      |

Pages are loaded by Splunk via XML views (`default/data/ui/views/*.xml`) which reference the HTML
templates.

## MobX Stores (`stores/`)

Each store is a singleton MobX observable that manages a domain entity's state and API calls:

`Identities`, `Connections`, `ConnectionTypes`, `Inputs`, `Outputs`, `Lookups`, `Settings`,
`Drivers`, `Keystore`, `Templates`, `LogConfigs`, `Apps`, `Messages`, `Roles`, `SavedSearches`,
`ServerStatus`, `TimezoneInfo`, `HttpEventCollector`, `Cluster`, `OAuth2`, `EmbeddingServices`

All stores are re-exported from `stores/index.jsx`.

## Components (`components/`)

38 reusable component directories. Key patterns:

- Each component directory contains: `ComponentName.jsx`, `ComponentName.pcssm` (PostCSS module),
  optionally `ComponentName.test.jsx`
- Components use React class components with `propTypes` (not functional/hooks - this is a known
  tech debt)
- Styling via PostCSS modules (`.pcssm` files) with variables, nesting, mixins
- Splunk UI components from `@splunk/react-ui` are used alongside custom components

## Utilities (`utils/`)

- `APIRequest.jsx` - HTTP requests to DBX Java API (via Python proxy)
- `SplunkAPIRequest.jsx` - HTTP requests to Splunk REST API
- `DbxUtil.jsx` - App info, navigation, URL helpers
- `Authorization.js` - Role/capability checks
- `Search.jsx` - Splunk search helpers
- `ValidationHelper.jsx` - Form validation
- `SQLUtils.jsx` / `SPLModeHelper.jsx` - SQL/SPL editing helpers
- `CheckpointValidator.js` - Checkpoint validation logic
- `StringUtils.jsx` - String manipulation helpers
- `CollectionStorage.jsx` / `SplunkResourceStorage.jsx` / `BrowserStorage.jsx` /
  `InMemoryStorage.jsx` - Storage abstractions

## Testing

UI unit tests use Karma + Mocha + Chai + Sinon + Enzyme:

```sh
yarn ui-unit-tests  # from repo root
# Runs: ./node_modules/karma/bin/karma start --no-colors --single-run --reporters dots,junit
```

Test files are colocated: `ComponentName.test.jsx` next to `ComponentName.jsx`. Tests focus on
component rendering using Enzyme.

Karma config is at the repo root (`karma.conf.js`). It uses:

- ChromeHeadless (via Puppeteer)
- babel-polyfill for ES6 features
- Source maps for debugging
- JUnit XML reporter for CI

E2E UI tests (WebdriverIO + Chai) are in `wdio-test/` at the repo root, not here.

## Code Style

ESLint with `@splunk/eslint-config/browser`, `plugin:react/recommended`. Parser:
`@babel/eslint-parser`.

```sh
./node_modules/.bin/eslint <files>        # Check
./node_modules/.bin/eslint <files> --fix  # Apply
```

Key rules: semicolons required, no-console (warn), no-unused-vars (warn), react prop-types (warn),
JSX double quotes, eqeqeq (allow-null).

## Build

Webpack 4 bundles the frontend. The build is triggered as part of the Grunt pipeline:

1. `swc-dbx` deps installed and built (provides `splcore-ui` components)
2. Webpack build combines `static/src/` with Splunk Web Components
3. PostCSS processes styles (`style.config.js` at repo root)

Webpack resolves modules from `static/` and `swc-dbx/dist/`. Import paths use `src/` prefix (e.g.,
`import stores from 'src/stores/Apps'`).

## Page Loading Flow

1. Splunk loads an XML view from `default/data/ui/views/*.xml` (e.g., `data_lab.xml`)
2. The XML view references an HTML template from `templates/` (e.g., `data_lab.html`)
3. The HTML template loads the corresponding page's `Index.jsx`
4. `Index.jsx` imports `bootstrap.jsx` at the top, which:
    - Loads babel-polyfill and ES6 promise polyfill
    - Checks if the app is configured via the Apps store
    - Redirects to FTR (First Time Run) page if not configured
