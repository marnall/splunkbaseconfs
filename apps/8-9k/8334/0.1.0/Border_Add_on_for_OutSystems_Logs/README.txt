# Border Add-on for OutSystems Logs

## Overview

Collect logs from OutSystems Platform Monitor Probe API with automatic checkpointing and deduplication.

**Supported Endpoints**: Errors, Extensions, General, Integrations, Mobile Requests, Request Events, Timers, Web Requests

## Requirements

- **Splunk Enterprise** 9.0+ or **Splunk Cloud** (Victoria+)
- **OutSystems Monitor Probe API** access with valid API key
- All Python dependencies are bundled - no manual installation required

## Quick Start

1. **Install**: Apps → Manage Apps → Install app from file
2. **Configure Input**: Navigate to add-on → Inputs → Create New Input
3. **Required Settings**:
   - **Name**: Unique identifier (e.g., `outsystems_errors_prod`)
   - **API Key**: Your OutSystems API authentication key
   - **Base API URL**: Your Monitor Probe API endpoint
   - **Endpoint Type**: Select log type (Errors, Integrations, etc.)
   - **Interval**: 60 (seconds - recommended)
   - **Index**: Target Splunk index

4. **Search Data**: `index=your_index sourcetype="outsystems:logs"`

## Configuration Options

**Recommended Defaults** (adjust only if needed):
- **Event Delay**: 15 minutes (ensures log availability)
- **Fetch Chunk Size**: 5 minutes (data per API call)
- **Initial Lookback**: 3 hours (first run only)

**For Historical Data**:
- Set **Historical Start Time**: `2025-01-01T00:00:00.000Z`
- Set **Historical End Time**: `2025-01-31T23:59:59.999Z`
- Remove these after backfill completes

## Troubleshooting

**No data appearing?**
1. Verify input is enabled (Inputs tab → check Status)
2. Check logs: `$SPLUNK_HOME/var/log/splunk/splunk_add_on_for_outsystems_platform_logs_*.log`
3. Test API: `curl -H "Authorization: YOUR_API_KEY" "YOUR_BASE_URL/Errors?StartMoment=2025-01-01T00:00:00.000Z&EndMoment=2025-01-01T01:00:00.000Z"`

**API rate limiting?**
- Increase "Sleep Between Calls" (default: 1000ms)
- Decrease "Fetch Chunk Size" (default: 5 minutes)
- Increase "Interval" (run less frequently)

## Support

- **Company**: Border Innovation (https://border-innovation.com/)
- **Email**: hello@border-innovation.com, miguel.pereira@border-innovation.com
- **Documentation**: https://splunk.github.io/addonfactory-ucc-generator/
- **Logs**: `$SPLUNK_HOME/var/log/splunk/`

## Commercial Use

This add-on is licensed for non-commercial use only. If you wish to use this 
add-on for commercial purposes, please contact Border Innovation for a 
commercial license:

- **Email**: hello@border-innovation.com, miguel.pereira@border-innovation.com
- **Website**: https://border-innovation.com/

Commercial use includes but is not limited to:
- Use in production environments for business operations
- Use by commercial entities or service providers
- Integration with commercial products or services

## License

Non-Commercial License - Copyright (c) 2025 Border Innovation.

**Non-Commercial Use Only**: This add-on is free for personal, educational, 
and evaluation purposes.

**Commercial Licensing**: For commercial use, please contact 
miguel.pereira@border-innovation.com to obtain a commercial license.

See LICENSE.txt for full terms and conditions.

