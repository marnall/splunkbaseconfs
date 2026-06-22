# Airia Platform Analytics - Splunk App

A complete Splunk app for monitoring and analyzing Airia Platform AI operations.

## Features

### Dedicated Index
- **Index Name:** `airia`
- **Retention:** 30 days
- **Max Size:** 5GB
- **Optimized for:** AI cost tracking, performance monitoring, usage analytics

### Sourcetype
- **airia:syslog** - Optimized for Airia Platform JSON logs via syslog

### Automatic Field Extraction
Pre-configured field extractions for:
- `model_name` - AI model identifier
- `model_display` - Friendly model name
- `tokens_cost` - Cost per API call
- `total_tokens`, `input_tokens`, `output_tokens` - Token usage
- `prompt_name` - Prompt template name
- `success` - Execution status
- `provider` - Model provider (Anthropic, Google, etc.)

### Pre-built Dashboards
1. **AI Cost Monitoring** - Track spending, tokens, cost trends
2. **Performance Metrics** - Success rates, execution stats
3. **Usage Analytics** - Prompt usage, user activity patterns

## Installation

### Option 1: Deploy via Docker (Recommended)

1. **Stop Splunk container:**
   ```bash
   docker stop splunk-server
   ```

2. **Copy app to Splunk:**
   ```bash
   docker cp splunk-app-airia splunk-server:/opt/splunk/etc/apps/airia_platform
   ```

3. **Fix permissions:**
   ```bash
   docker exec -u root splunk-server chown -R splunk:splunk /opt/splunk/etc/apps/airia_platform
   ```

4. **Start Splunk:**
   ```bash
   docker start splunk-server
   ```

5. **Wait 30 seconds for Splunk to start, then access:**
   - Go to http://localhost:8000
   - Login: `admin` / `changeme123`
   - Click **Apps** → You should see **Airia Platform Analytics**

### Option 2: Install from Archive

1. **Create tar archive:**
   ```bash
   cd splunk-app-airia
   tar -czf airia_platform.tar.gz *
   ```

2. **Install via Splunk Web:**
   - Go to http://localhost:8000
   - Click **Apps** → **Manage Apps**
   - Click **Install app from file**
   - Upload `airia_platform.tar.gz`
   - Click **Install**

## Configuration

### **IMPORTANT: Data Model Acceleration**

This app includes a data model (`Airia_Platform`) for accelerated analytics. To enable acceleration:

1. Go to **Settings** → **Data models**
2. Find **Airia_Platform** data model
3. Click **Edit** → **Edit Acceleration**
4. Enable acceleration with these recommended settings:
   - **Enable acceleration:** Yes
   - **Acceleration time range:** Last 7 days (`-7d`)
   - **Summary schedule:** Every 5 minutes (`*/5 * * * *`)
   - **Max concurrent jobs:** 2
   - **Backfill time:** Last 7 days (`-7d`)
   - **Max summary time:** 3600 seconds (1 hour)
5. Click **Save**

**Why manual setup?** Splunk best practices require data model acceleration to be enabled manually through the GUI to prevent unintended disk usage and performance impact.

### **IMPORTANT: Enable Syslog Inputs**

After installing the app, you **MUST manually enable** the syslog inputs in Splunk:

#### Enable TCP Input (Port 514):
1. Go to **Settings** → **Data Inputs** → **TCP**
2. Click **New Local TCP**
3. Port: `514`
4. Click **Next**
5. Source type: Select **Manual** → Enter `airia:syslog`
6. App Context: `airia_platform`
7. Index: `airia`
8. Click **Review** → **Submit**

#### Enable UDP Input (Port 514) - Optional:
1. Go to **Settings** → **Data Inputs** → **UDP**
2. Click **New Local UDP**
3. Port: `514`
4. Click **Next**
5. Source type: Select **Manual** → Enter `airia:syslog`
6. App Context: `airia_platform`
7. Index: `airia`
8. Click **Review** → **Submit**

**Why manual setup?** Splunk security policy prevents apps from automatically enabling network inputs. The inputs.conf in this app defines the configuration, but you must enable them manually via the UI or CLI.

### Verify Installation

1. **Check index is created:**
   ```spl
   | eventcount summarize=false index=airia
   ```

2. **Search for events:**
   ```spl
   index=airia
   ```

3. **Test field extractions:**
   ```spl
   index=airia model_name=* | stats count by model_name
   ```

## Using the App

### Access Dashboards

1. Go to http://localhost:8000
2. Click **Apps** → **Airia Platform Analytics**
3. You'll see all 3 dashboards on the home page

### Create Alerts

**Example: High Cost Alert**
```spl
index=airia tokens_cost=*
| stats sum(cost_numeric) as daily_cost
| where daily_cost > 10
```

**Example: Failure Alert**
```spl
index=airia success=false
| stats count as failures
| where failures > 5
```

### Common Searches

**Total Cost Today:**
```spl
index=airia earliest=@d
| stats sum(cost_numeric) as cost
| eval cost="$".round(cost, 2)
```

**Most Expensive Prompts:**
```spl
index=airia prompt_name=* tokens_cost=*
| stats sum(cost_numeric) as cost by prompt_name
| sort -cost
```

**Model Performance:**
```spl
index=airia model_display=*
| stats count avg(tokens_numeric) as avg_tokens by model_display
```

## Advantages of This App

### vs. Using Main Index:
✅ **Dedicated storage** - Won't mix with other Splunk data
✅ **Custom retention** - 30 days for AI logs (configurable)
✅ **Optimized fields** - Pre-extracted at index time for speed
✅ **Better organization** - All Airia data in one place
✅ **Faster searches** - Smaller index = faster queries

### Built-in Features:
✅ **Automatic field extraction** - No manual rex commands needed
✅ **Pre-built dashboards** - Instant visibility
✅ **Proper sourcetype** - `airia:syslog` instead of generic `syslog`
✅ **Professional packaging** - Easy to share/deploy

## Customization

### Modify Field Extractions
Edit: `default/props.conf`

### Change Index Settings
Edit: `default/indexes.conf`

### Update Dashboards
1. Go to dashboard in Splunk Web
2. Click **Edit**
3. Modify as needed
4. Click **Save**

Or edit XML files in: `default/data/ui/views/`

### Add More Dashboards
1. Create dashboard in Splunk Web
2. Export as XML
3. Copy to `default/data/ui/views/`
4. Restart Splunk

## Migrating Existing Data

If you have data already in `main` index:

```spl
index=main host=airia.platform sourcetype=syslog
| collect index=airia sourcetype=airia:syslog
```

## Troubleshooting

### App doesn't appear
- Check permissions: `docker exec splunk-server ls -la /opt/splunk/etc/apps/airia_platform`
- Restart Splunk: `docker restart splunk-server`
- Check logs: `docker logs splunk-server | grep airia`

### No data in index
- Verify syslog is sending to correct host
- Check input status: Settings → Data Inputs → TCP/UDP
- Test manually: `echo "<14>test" | nc localhost 514`
- Search: `index=airia` (with time range: All time)

### Fields not extracting
- Check props.conf is correct
- Restart Splunk
- Test with: `index=airia | head 1 | fieldsummary`

## Support

- App Version: 1.0.0
- Compatible with: Splunk 8.x, 9.x, 10.x
- Documentation: See parent README.md files

## License

Please see [LICENSE](../LICENSE) for the license governing use of this Software provided by Airia
