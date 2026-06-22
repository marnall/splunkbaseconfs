# Splunkbase Upload Checklist (PhishIQ TA)

Use this checklist before every Splunkbase submission.

## 1) Version and metadata

- [ ] Update `default/app.conf`:
  - [ ] `version = <new_version>`
  - [ ] `build = <new_build_number>`
- [ ] Preferred update command (from `splunk/`):

```bash
./scripts/bump_version.sh <new_version> <new_build_number>
```
- [ ] Confirm `[package] id = phishiq_ta`
- [ ] Confirm app naming is consistent with the Splunkbase listing

## 2) Package content hygiene

- [ ] Confirm package root folder is exactly `phishiq_ta/`
- [ ] Include required app content:
  - [ ] `default/`
  - [ ] `bin/`
  - [ ] `README/`
  - [ ] `static/` (icons)
  - [ ] `requirements.txt` (if required by runtime)
- [ ] Remove non-release files:
  - [ ] `.DS_Store`
  - [ ] `__pycache__/`
  - [ ] `*.pyc`
  - [ ] local IDE/dev-only files

## 3) Build release artifacts

Preferred (from `splunk/`):

```bash
./scripts/build_release.sh
```

Manual fallback (from `splunk/`):

```bash
rm -rf dist/phishiq_ta
mkdir -p dist/phishiq_ta
cp -R bin default README static dist/phishiq_ta/
cp requirements.txt dist/phishiq_ta/requirements.txt

rm -f dist/phishiq_ta-enterprise.tgz dist/phishiq_ta-enterprise.tgz.sha256 dist/phishiq_ta-enterprise.manifest.txt
tar -czf dist/phishiq_ta-enterprise.tgz -C dist phishiq_ta
shasum -a 256 dist/phishiq_ta-enterprise.tgz > dist/phishiq_ta-enterprise.tgz.sha256
tar -tzf dist/phishiq_ta-enterprise.tgz > dist/phishiq_ta-enterprise.manifest.txt
```

## 4) Validate artifacts

- [ ] Verify hash:

```bash
shasum -a 256 -c dist/phishiq_ta-enterprise.tgz.sha256
```

- [ ] Inspect manifest and confirm no junk files:

```bash
cat dist/phishiq_ta-enterprise.manifest.txt
```

- [ ] Confirm key files are present:
  - [ ] `phishiq_ta/default/app.conf`
  - [ ] `phishiq_ta/default/inputs.conf`
  - [ ] `phishiq_ta/default/props.conf`
  - [ ] `phishiq_ta/default/transforms.conf`
  - [ ] `phishiq_ta/default/commands.conf`
  - [ ] `phishiq_ta/bin/phishiqplus_search.py`
  - [ ] `phishiq_ta/README/RELEASE.md`

## 5) Splunkbase form choices

- [ ] Hosting: `Splunkbase will host my app`
- [ ] Access level: `Restricted` (or `Public` if intentionally open)
- [ ] Content type: `Splunk App`

## 6) Upload package

- [ ] Upload `dist/phishiq_ta-enterprise.tgz`
- [ ] Keep `dist/phishiq_ta-enterprise.tgz.sha256` and `dist/phishiq_ta-enterprise.manifest.txt` for audit/troubleshooting

## 7) Post-upload verification

- [ ] Confirm uploaded version/build match `default/app.conf`
- [ ] Confirm release notes are updated in Splunkbase
- [ ] Store artifacts and checksum in release archive
