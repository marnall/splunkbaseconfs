# Third-Party Licenses

`TA-airtable-auditlogs` is licensed under the MIT License (see `LICENSE`).

It bundles the following third-party Python libraries under `lib/`, vendored
so the modular input runs without requiring pip access on the Heavy Forwarder.
Each library retains its own license, reproduced in full inside its
`dist-info` folder at the paths below.

| Library | Version | License | License text |
|---|---|---|---|
| requests | 2.31.0 | Apache License 2.0 | `lib/requests-2.31.0.dist-info/LICENSE` |
| urllib3 | 1.26.20 | MIT License | `lib/urllib3-1.26.20.dist-info/LICENSE.txt` |
| certifi | 2026.7.22 | Mozilla Public License 2.0 | `lib/certifi-2026.7.22.dist-info/licenses/LICENSE` |
| idna | 3.18 | BSD 3-Clause | `lib/idna-3.18.dist-info/licenses/LICENSE.md` |
| charset-normalizer | 3.3.2 | MIT License | `lib/charset_normalizer-3.3.2.dist-info/LICENSE` |
| packaging | 26.2 | Apache-2.0 OR BSD-2-Clause | `lib/packaging-26.2.dist-info/licenses/LICENSE` |
| deprecation | 2.1.0 | Apache License 2.0 | `lib/deprecation-2.1.0.dist-info/LICENSE` |
| splunk-sdk (splunklib) | 2.1.1 | Apache License 2.0 | `lib/splunk_sdk-2.1.1.dist-info/LICENSE` |

None of these libraries have been modified; they are vendored as published by
their respective maintainers, with compiled/platform-specific binaries
stripped for portability across Heavy Forwarder architectures.

If you update any bundled library version, update this table and confirm the
new `dist-info` folder still carries its own license file — some packages
place it under `licenses/` and some directly under `dist-info/`.
