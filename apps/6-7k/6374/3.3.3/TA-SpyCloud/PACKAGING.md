# TA-SpyCloud Packaging Guide

This document explains how to package the TA-SpyCloud Splunk Technical Add-on for deployment to Splunk Enterprise.

## Quick Start

### Option 1: Using the Bash Script (Recommended)

The `package.sh` script provides the most comprehensive packaging solution with validation and cleanup.

```bash
# Create package with auto-detected version
./package.sh

# Create package with specific version
./package.sh -v 3.0.3

# Preview what would be packaged (dry run)
./package.sh --dry-run

# Skip cleanup or verification
./package.sh --no-cleanup --no-verify

# Show help
./package.sh --help
```

### Option 2: Using Make

For simple packaging, you can use the Makefile:

```bash
# Create the package
make package

# Show package info
make info

# Verify existing package
make verify

# Clean up development files
make clean

# Show help
make help
```

## Package Details

### What Gets Packaged

The packaging process includes:
- **bin/**: Python scripts and dependencies
- **default/**: Configuration files (app.conf, inputs.conf, etc.)
- **appserver/**: Web UI components and static assets
- **static/**: App icons and logos
- **metadata/**: Permissions and metadata files
- **README/**: Documentation
- **CHANGELOG.md**: Version history
- **app.manifest**: Splunk app manifest

### What Gets Excluded

The following development files are automatically excluded:
- `.claude/` directory (Claude Code artifacts)
- `.git/` directory and `.gitignore`
- `__pycache__/` directories
- `*.pyc` files (Python bytecode)
- `.DS_Store` files (macOS)
- `package.sh` and `Makefile` (packaging scripts)
- `*.patch` files and `PATCH_SUMMARY.md`

### Version Detection

Both packaging methods automatically detect the version from `default/app.conf`:
```ini
[launcher]
version = 3.0.2
```

## Packaging Script Features

The `package.sh` script provides advanced features:

### Command Line Options

- `-h, --help`: Show help message
- `-v, --version VER`: Override version (default: auto-detect)
- `-o, --output DIR`: Output directory (default: parent directory)
- `--no-cleanup`: Skip cleanup of development files
- `--no-verify`: Skip package verification
- `--dry-run`: Preview without creating package

### Validation Features

- **Structure Validation**: Ensures required directories and files exist
- **Version Detection**: Automatically reads version from app.conf
- **Package Verification**: Validates package contents and structure
- **File Count Statistics**: Shows files and directories in package
- **Exclusion Verification**: Confirms no development files are included

### Example Outputs

```bash
$ ./package.sh
[INFO] Starting TA-SpyCloud packaging process...
[INFO] App directory: /path/to/TA-SpyCloud
[INFO] Version: 3.0.2
[INFO] Output directory: /path/to/splunk
[INFO] Validating app structure...
[SUCCESS] App structure validated
[INFO] Cleaning up development files...
[SUCCESS] Development files cleaned up
[INFO] Creating package: TA-SpyCloud-3.0.2.spl
[SUCCESS] Package created: /path/to/splunk/TA-SpyCloud-3.0.2.spl
[INFO] Verifying package contents...
[INFO] Package size: 5.8M
[SUCCESS] Package structure verified
[INFO] Files: 1006, Directories: 148
[SUCCESS] No excluded files found in package
[SUCCESS] Packaging completed successfully!
[INFO] Package location: /path/to/splunk/TA-SpyCloud-3.0.2.spl
```

## Deployment

Once packaged, you can deploy the `.spl` file to Splunk Enterprise:

### Via Splunk Web (Recommended)
1. Go to **Apps** → **Manage Apps**
2. Click **Install app from file**
3. Upload the `.spl` file
4. Follow the installation wizard

### Via Command Line
```bash
$SPLUNK_HOME/bin/splunk install app TA-SpyCloud-3.0.2.spl
$SPLUNK_HOME/bin/splunk restart
```

### Manual Installation
```bash
cd $SPLUNK_HOME/etc/apps/
tar -xzf /path/to/TA-SpyCloud-3.0.2.spl
$SPLUNK_HOME/bin/splunk restart
```

## Post-Installation Configuration

After installation, configure the add-on:

1. **API Credentials**: Set up SpyCloud API credentials in the app settings
2. **Data Inputs**: Configure the 4 available data sources:
   - spycloud_watchlist
   - spycloud_watchlist_identifiers
   - spycloud_compass
   - spycloud_breach_catalog
3. **Ingestion Schedules**: Set up data collection intervals
4. **Index Configuration**: Ensure proper index mapping

## Troubleshooting

### Common Issues

**Package verification fails**
- Ensure you're in the TA-SpyCloud directory when running the script
- Check that required files (app.conf, app.manifest) exist

**Version detection fails**
- Verify `default/app.conf` exists and contains a valid version line
- Use `-v` option to override version detection

**Package too large**
- Check for accidentally included files (logs, temp files)
- Ensure cleanup ran properly with `--no-cleanup` flag

**Permission denied errors**
- Make sure `package.sh` is executable: `chmod +x package.sh`
- Check write permissions in the output directory

### Support

For issues with packaging or deployment:
1. Check the Splunk Enterprise documentation
2. Review the app logs in `$SPLUNK_HOME/var/log/splunk/`
3. Use the `--dry-run` option to preview packaging without creating files

## File Structure Reference

```
TA-SpyCloud/
├── bin/                          # Python scripts and dependencies
│   ├── api.py                   # SpyCloud API integration
│   ├── ingestion.py             # Data ingestion logic
│   └── ta_spycloud/             # Python dependencies
├── default/                      # Configuration files
│   ├── app.conf                 # Main app configuration
│   ├── inputs.conf              # Input definitions
│   └── ...                      # Other configs
├── appserver/                    # Web UI components
│   ├── static/                  # JavaScript and assets
│   └── templates/               # HTML templates
├── static/                       # App icons and logos
├── metadata/                     # Permissions and metadata
├── README/                       # Documentation
├── app.manifest                  # Splunk app manifest
├── CHANGELOG.md                  # Version history
├── package.sh                   # Packaging script
└── Makefile                     # Make targets
```