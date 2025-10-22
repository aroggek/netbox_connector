# NetBox Connector for Splunk

## Overview

NetBox Connector is a Splunk Add-on that integrates NetBox DCIM/IPAM data into Splunk. It provides:

1. **Data Collection**: Pull data from NetBox into Splunk via Modular Input
2. **Data Enrichment**: Enrich Splunk events with NetBox data using custom search command
3. **Multiple Output Modes**: Store data as events, lookups, or KV Store

## Features

- Collect devices, virtual machines, IP addresses, and sites from NetBox
- Real-time enrichment of alerts with NetBox infrastructure data
- Support for both lookup tables and KV Store
- Configurable polling intervals
- Checkpoint mechanism to avoid duplicate data

## Installation

1. Extract the add-on to `$SPLUNK_HOME/etc/apps/TA-netbox-connector/`
2. Restart Splunk
3. Configure NetBox connection in the Add-on settings

## Configuration

### Modular Input Configuration

Create a new input in `inputs.conf` or via Splunk Web UI:

```ini
[netbox_connector://netbox_devices]
netbox_url = https://netbox.example.com
netbox_token = your_api_token_here
data_type = devices
output_mode = lookup
verify_ssl = 1
interval = 3600
disabled = 0
```

### Parameters

- **netbox_url**: NetBox instance URL (e.g., https://netbox.example.com)
- **netbox_token**: API authentication token from NetBox
- **data_type**: Type of data to collect
  - `devices`: Physical devices
  - `virtual_machines`: Virtual machines
  - `ip_addresses`: IP addresses
  - `sites`: Sites/locations
  - `all`: All data types
- **output_mode**: How to output data
  - `events`: Stream as Splunk events
  - `lookup`: Store in CSV lookup files
  - `kvstore`: Store in KV Store collections
- **verify_ssl**: Verify SSL certificate (default: true)
- **interval**: Polling interval in seconds (default: 3600)

## Usage

### Data Collection

After configuring the modular input, data will be automatically collected from NetBox at the specified interval.

### Event Enrichment

Use the `netboxenrich` custom search command to enrich events with NetBox data:

```spl
index=main sourcetype=firewall
| netboxenrich field=src_ip netbox_url="https://netbox.example.com" netbox_token="your_token"
| table _time src_ip netbox_name netbox_device_type netbox_site
```

### Lookup-based Enrichment

If using lookup mode, you can use standard Splunk lookups:

```spl
index=main sourcetype=firewall
| lookup netbox_devices name as hostname OUTPUT device_type site status primary_ip
```

### KV Store Queries

If using KV Store mode:

```spl
| inputlookup netbox_devices
| search site="DataCenter-1"
| table name device_type status primary_ip
```

## Use Cases

### 1. Alert Enrichment

Enrich security alerts with device context:

```spl
index=security sourcetype=ids
| netboxenrich field=dest_ip netbox_url="https://netbox.example.com" netbox_token="token"
| eval risk_score=if(netbox_device_role=="production", 10, 5)
| where risk_score > 8
```

### 2. Asset Inventory

Create dashboards showing NetBox asset inventory:

```spl
| inputlookup netbox_devices
| stats count by site device_type
| sort -count
```

### 3. Change Detection

Track changes in NetBox data:

```spl
index=netbox sourcetype=netbox:device
| transaction name
| where eventcount > 1
| table name status last_updated
```

### 4. Network Troubleshooting

Correlate network issues with infrastructure data:

```spl
index=network sourcetype=syslog
| netboxenrich field=host netbox_url="https://netbox.example.com" netbox_token="token"
| stats count by netbox_site netbox_rack
```

## Data Sources

### Devices (`netbox:device`)

Fields collected:
- id, name, device_type, device_role, site, rack
- status, primary_ip, serial, asset_tag
- last_updated, comments, tags, custom_fields

### Virtual Machines (`netbox:vm`)

Fields collected:
- id, name, status, site, cluster, role
- primary_ip, vcpus, memory, disk
- last_updated, comments, tags, custom_fields

### IP Addresses (`netbox:ip`)

Fields collected:
- id, address, status, dns_name
- assigned_object_type, assigned_object
- vrf, tenant, description
- last_updated, tags, custom_fields

### Sites (`netbox:site`)

Fields collected:
- id, name, slug, status, region
- facility, asn, time_zone
- description, physical_address
- latitude, longitude, tags, custom_fields

## Troubleshooting

### Check Logs

```spl
index=_internal source="*ta_netbox_connector*"
| stats count by log_level
```

### Test NetBox Connection

Use the enrichment command to test connectivity:

```spl
| makeresults
| eval test_host="test-device"
| netboxenrich field=test_host netbox_url="https://netbox.example.com" netbox_token="token"
```

### Verify Data Collection

```spl
index=netbox earliest=-1h
| stats count by sourcetype
```

## API Requirements

- NetBox v2.8 or higher
- Valid API token with appropriate permissions
- Network connectivity from Splunk to NetBox instance

## Security

- API tokens are stored encrypted in Splunk
- SSL certificate verification is enabled by default
- Follows principle of least privilege for API access

## Support

For issues and feature requests, please contact your Splunk administrator.

## Version History

- **1.0.0** (Initial Release)
  - Modular input for data collection
  - Custom search command for enrichment
  - Support for devices, VMs, IPs, and sites
  - Multiple output modes (events, lookup, kvstore)

## License

[Your License Here]
