# NetBox Connector - Installation Guide

## Prerequisites

1. **Splunk Enterprise** 8.0 or higher
2. **NetBox** v2.8 or higher
3. **NetBox API Token** with read permissions
4. **Python 3** (included with Splunk 8.0+)

## Installation Steps

### 1. Install the Add-on

#### Option A: Via Splunk Web (Recommended)

1. Login to Splunk Web as admin
2. Navigate to **Apps** > **Manage Apps**
3. Click **Install app from file**
4. Upload the `TA-netbox-connector` package
5. Restart Splunk

#### Option B: Manual Installation

1. Copy the add-on to your Splunk apps directory:
   ```bash
   cd $SPLUNK_HOME/etc/apps/
   tar -xzf TA-netbox-connector.tar.gz
   # or
   cp -r TA-netbox-connector $SPLUNK_HOME/etc/apps/
   ```

2. Set correct permissions:
   ```bash
   chown -R splunk:splunk $SPLUNK_HOME/etc/apps/TA-netbox-connector
   chmod +x $SPLUNK_HOME/etc/apps/TA-netbox-connector/bin/*.py
   ```

3. Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

### 2. Install Python Dependencies

The add-on requires the `requests` library. Install it using one of these methods:

#### Option A: Using Splunk's Python

```bash
cd $SPLUNK_HOME/bin
./splunk cmd python3 -m pip install requests
```

#### Option B: System Python (if Splunk uses system Python)

```bash
pip3 install -r $SPLUNK_HOME/etc/apps/TA-netbox-connector/requirements.txt
```

### 3. Configure NetBox Connection

#### Option A: Via Splunk Web UI

1. Go to **Settings** > **Data inputs**
2. Click **NetBox Connector**
3. Click **New Input**
4. Fill in the configuration:
   - **Name**: Unique name for this input (e.g., `netbox_devices_prod`)
   - **NetBox URL**: Your NetBox URL (e.g., `https://netbox.example.com`)
   - **NetBox API Token**: Your API token
   - **Data Type**: Choose what to collect (`devices`, `virtual_machines`, `ip_addresses`, `sites`, or `all`)
   - **Output Mode**: Choose output format (`events`, `lookup`, or `kvstore`)
   - **Verify SSL**: Enable/disable SSL verification
   - **Interval**: Collection interval in seconds (default: 3600)
5. Click **Save**

#### Option B: Via Configuration File

Edit `$SPLUNK_HOME/etc/apps/TA-netbox-connector/local/inputs.conf`:

```ini
[netbox_connector://netbox_devices_prod]
netbox_url = https://netbox.example.com
netbox_token = your_api_token_here
data_type = devices
output_mode = lookup
verify_ssl = 1
interval = 3600
disabled = 0
```

### 4. Verify Installation

#### Check Add-on Status

```spl
index=_internal source="*ta_netbox_connector*" earliest=-15m
| stats count by log_level
```

#### Test Data Collection

After the first collection interval:

```spl
index=netbox earliest=-1h
| stats count by sourcetype
```

Or check lookups:

```spl
| inputlookup netbox_devices
| head 10
```

#### Test Enrichment Command

```spl
| makeresults
| eval hostname="test-device"
| netboxenrich field=hostname netbox_url="https://netbox.example.com" netbox_token="your_token"
```

## Configuration Examples

### Example 1: Collect All Data to Lookups

```ini
[netbox_connector://netbox_all_lookups]
netbox_url = https://netbox.company.com
netbox_token = abc123def456ghi789
data_type = all
output_mode = lookup
verify_ssl = 1
interval = 7200
disabled = 0
```

### Example 2: Collect Devices to KV Store

```ini
[netbox_connector://netbox_devices_kvstore]
netbox_url = https://netbox.company.com
netbox_token = abc123def456ghi789
data_type = devices
output_mode = kvstore
verify_ssl = 1
interval = 3600
disabled = 0
```

### Example 3: Stream All Data as Events

```ini
[netbox_connector://netbox_events]
netbox_url = https://netbox.company.com
netbox_token = abc123def456ghi789
data_type = all
output_mode = events
verify_ssl = 1
interval = 1800
disabled = 0
index = netbox
```

## NetBox API Token Setup

1. Login to NetBox as admin
2. Navigate to **Admin** > **Users** > **Tokens**
3. Click **Add Token**
4. Fill in:
   - **User**: Select service account user
   - **Key**: Auto-generated or custom
   - **Write enabled**: Unchecked (read-only is sufficient)
   - **Description**: "Splunk Integration"
5. Click **Save**
6. Copy the token and use it in Splunk configuration

## Security Best Practices

1. **Use dedicated service account**: Create a dedicated NetBox user for Splunk
2. **Read-only permissions**: The token only needs read access
3. **Restrict object permissions**: Limit access to only necessary objects
4. **Enable SSL**: Always use HTTPS and verify certificates
5. **Rotate tokens**: Regularly rotate API tokens
6. **Encrypt storage**: Splunk stores tokens encrypted by default

## Troubleshooting

### Common Issues

#### 1. "Import error: No module named 'requests'"

**Solution**: Install the requests library:
```bash
$SPLUNK_HOME/bin/splunk cmd python3 -m pip install requests
```

#### 2. "NetBox API request failed: SSL verification failed"

**Solution**: Either:
- Add NetBox certificate to trusted certificates, or
- Set `verify_ssl = 0` (not recommended for production)

#### 3. "Authentication failed"

**Solution**:
- Verify the API token is correct
- Check token hasn't expired
- Ensure token has read permissions

#### 4. "No data collected"

**Solution**:
- Check Splunk internal logs for errors
- Verify network connectivity to NetBox
- Test API token using curl:
  ```bash
  curl -H "Authorization: Token YOUR_TOKEN" https://netbox.example.com/api/dcim/devices/
  ```

#### 5. "Permission denied" errors

**Solution**:
- Check file permissions on bin/*.py files
- Ensure they're executable: `chmod +x bin/*.py`

### Debug Logging

Enable debug logging by adding to `local/inputs.conf`:

```ini
[netbox_connector]
loglevel = DEBUG
```

Then check logs:

```spl
index=_internal source="*ta_netbox_connector*" earliest=-1h
| table _time log_level message
```

## Uninstallation

1. Disable all inputs:
   ```bash
   $SPLUNK_HOME/bin/splunk disable app TA-netbox-connector
   ```

2. Remove the add-on:
   ```bash
   rm -rf $SPLUNK_HOME/etc/apps/TA-netbox-connector
   ```

3. Restart Splunk:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

## Upgrade

1. Disable the current version
2. Backup your configuration (`local/*.conf` files)
3. Remove old version
4. Install new version
5. Restore configuration
6. Enable and restart Splunk

## Support

For issues and questions:
- Check logs: `index=_internal source="*ta_netbox_connector*"`
- Review documentation: `README.md`
- Contact your Splunk administrator

## Next Steps

After installation:
1. Configure data inputs for your NetBox instance
2. Create dashboards to visualize NetBox data
3. Set up alerts with NetBox enrichment
4. Build correlation searches using NetBox context

Refer to `README.md` for usage examples and best practices.
