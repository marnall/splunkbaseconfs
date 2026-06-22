# App Icon Instructions

## Location
Place the Nucleus Security logo in this directory (`static/`) with the filename `appIcon.png`

## Requirements

### For Splunk Apps (Splunk Web UI):
- **Filename**: `appIcon.png`
- **Size**: 36x36 pixels
- **Format**: PNG with transparency recommended
- **Location**: `splunk/TA-nucleus-logs/static/appIcon.png`

### For Splunk Cloud (Optional - larger icon):
- **Filename**: `appIcon_2x.png` 
- **Size**: 72x72 pixels (2x resolution for retina displays)
- **Format**: PNG with transparency recommended
- **Location**: `splunk/TA-nucleus-logs/static/appIcon_2x.png`

### For Splunkbase Listing:
Splunkbase requires separate icon uploads through the web interface:
- **Small icon**: 96x96 pixels (PNG)
- **Large icon**: 660x420 pixels (PNG)

## Steps to Add Your Logo

1. **Prepare the Nucleus Security logo**:
   - Create a 36x36 pixel PNG version
   - Optionally create a 72x72 pixel PNG version for high-DPI displays
   - Ensure the logo is clear and recognizable at small sizes

2. **Save as `appIcon.png`**:
   ```bash
   cp /path/to/nucleus-logo.png splunk/TA-nucleus-logs/static/appIcon.png
   ```

3. **Optional - Add retina version**:
   ```bash
   cp /path/to/nucleus-logo-2x.png splunk/TA-nucleus-logs/static/appIcon_2x.png
   ```

4. **Verify the icon appears**:
   - Restart Splunk
   - Navigate to Apps menu
   - The Nucleus logo should appear next to "Nucleus User Logs Technology Add-on"

## Icon Design Tips

- Use a simple, recognizable version of the Nucleus logo
- Avoid text in the 36x36 icon (too small to read)
- Ensure good contrast against both light and dark backgrounds
- Use transparency for non-rectangular logos
- Test the icon in both Splunk Light and Dark themes

## After Adding the Icon

Remember to rebuild the app package:
```bash
cd splunk/
tar -czf TA-nucleus-logs.tar.gz TA-nucleus-logs/ --exclude='*.tar.gz'
```

