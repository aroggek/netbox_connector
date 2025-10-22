# encoding = utf-8

"""
NetBox Data Collection Module for Splunk
Handles data collection from NetBox API and sends to Splunk
"""

import os
import sys
import time
import json
import csv
from datetime import datetime

# Add the current directory to path to import netbox_api
sys.path.insert(0, os.path.dirname(__file__))
import netbox_api


def validate_input(helper, definition):
    """
    Validate input configuration

    Args:
        helper: Splunk modular input helper
        definition: Input definition with parameters
    """
    netbox_url = definition.parameters.get('netbox_url', None)
    netbox_token = definition.parameters.get('netbox_token', None)
    data_type = definition.parameters.get('data_type', None)

    if not netbox_url:
        raise ValueError("NetBox URL is required")
    if not netbox_token:
        raise ValueError("NetBox API Token is required")
    if not data_type:
        raise ValueError("Data type is required")


def write_to_splunk(helper, ew, data, source, sourcetype):
    """
    Write event to Splunk

    Args:
        helper: Splunk modular input helper
        ew: Event writer
        data: Data to write (dict or string)
        source: Event source
        sourcetype: Event sourcetype
    """
    if isinstance(data, dict):
        data_str = json.dumps(data, ensure_ascii=False)
    else:
        data_str = str(data)

    event = helper.new_event(
        data_str,
        time=time.time(),
        host=None,
        source=source,
        sourcetype=sourcetype,
        done=True,
        unbroken=True
    )

    try:
        ew.write_event(event)
    except Exception as e:
        helper.log_error(f"Failed to write event to Splunk: {str(e)}")
        raise e


def write_to_lookup(helper, data, lookup_name, fieldnames=None):
    """
    Write data to CSV lookup file

    Args:
        helper: Splunk modular input helper
        data: List of dictionaries to write
        lookup_name: Name of the lookup file
        fieldnames: List of field names (if None, auto-detect from first item)
    """
    try:
        # Get the app's lookups directory
        app_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
        lookups_dir = os.path.join(app_home, 'etc', 'apps', 'TA-netbox-connector', 'lookups')

        # Create lookups directory if it doesn't exist
        os.makedirs(lookups_dir, exist_ok=True)

        lookup_path = os.path.join(lookups_dir, lookup_name)

        if not data:
            helper.log_warning(f"No data to write to lookup {lookup_name}")
            return

        # Auto-detect fieldnames if not provided
        if fieldnames is None and len(data) > 0:
            fieldnames = list(data[0].keys())

        # Write CSV file
        with open(lookup_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                # Flatten nested objects to JSON strings
                flattened_item = {}
                for key, value in item.items():
                    if isinstance(value, (dict, list)):
                        flattened_item[key] = json.dumps(value)
                    else:
                        flattened_item[key] = value
                writer.writerow(flattened_item)

        helper.log_info(f"Successfully wrote {len(data)} records to lookup {lookup_name}")

    except Exception as e:
        helper.log_error(f"Failed to write to lookup {lookup_name}: {str(e)}")
        raise e


def write_to_kvstore(helper, data, collection_name):
    """
    Write data to KV Store

    Args:
        helper: Splunk modular input helper
        data: List of dictionaries to write
        collection_name: Name of the KV Store collection
    """
    try:
        import splunklib.client as client

        # Get Splunk service
        service = helper.service

        # Get or create collection
        collections = service.kvstore

        try:
            collection = collections[collection_name]
        except KeyError:
            helper.log_info(f"Creating KV Store collection: {collection_name}")
            # Collection will be created via collections.conf
            collection = collections[collection_name]

        # Batch insert data
        collection.data.batch_save(*data)

        helper.log_info(f"Successfully wrote {len(data)} records to KV Store collection {collection_name}")

    except Exception as e:
        helper.log_error(f"Failed to write to KV Store collection {collection_name}: {str(e)}")
        raise e


def is_checkpoint_exists(checkpoint_file, item_id):
    """
    Check if item ID exists in checkpoint file

    Args:
        checkpoint_file: Path to checkpoint file
        item_id: Item ID to check

    Returns:
        bool: True if exists, False otherwise
    """
    if not os.path.exists(checkpoint_file):
        return False

    with open(checkpoint_file, 'r') as f:
        processed_ids = f.read().splitlines()
        return str(item_id) in processed_ids


def write_to_checkpoint(checkpoint_file, item_id):
    """
    Write item ID to checkpoint file

    Args:
        checkpoint_file: Path to checkpoint file
        item_id: Item ID to write
    """
    # Create checkpoint directory if it doesn't exist
    checkpoint_dir = os.path.dirname(checkpoint_file)
    os.makedirs(checkpoint_dir, exist_ok=True)

    with open(checkpoint_file, 'a') as f:
        f.write(str(item_id) + '\n')


def get_checkpoint_timestamp(checkpoint_file):
    """
    Get last modification timestamp from checkpoint file

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        float: Timestamp or None if file doesn't exist
    """
    if os.path.exists(checkpoint_file):
        return os.path.getmtime(checkpoint_file)
    return None


def collect_devices(helper, client, ew, output_mode, checkpoint_file):
    """
    Collect devices from NetBox

    Args:
        helper: Splunk modular input helper
        client: NetBox API client
        ew: Event writer
        output_mode: Output mode (events, lookup, kvstore)
        checkpoint_file: Checkpoint file path
    """
    helper.log_info("Collecting devices from NetBox")

    try:
        devices = client.get_devices()
        helper.log_info(f"Retrieved {len(devices)} devices from NetBox")

        if output_mode == 'events':
            # Write each device as separate event
            for device in devices:
                device_id = device.get('id')
                if not is_checkpoint_exists(checkpoint_file, device_id):
                    write_to_splunk(helper, ew, device, 'netbox:devices', 'netbox:device')
                    write_to_checkpoint(checkpoint_file, device_id)

        elif output_mode == 'lookup':
            # Prepare data for lookup
            lookup_data = []
            for device in devices:
                lookup_data.append({
                    'id': device.get('id'),
                    'name': device.get('name'),
                    'device_type': device.get('device_type', {}).get('display') if device.get('device_type') else '',
                    'device_role': device.get('device_role', {}).get('name') if device.get('device_role') else '',
                    'site': device.get('site', {}).get('name') if device.get('site') else '',
                    'rack': device.get('rack', {}).get('name') if device.get('rack') else '',
                    'status': device.get('status', {}).get('value') if device.get('status') else '',
                    'primary_ip': device.get('primary_ip', {}).get('address') if device.get('primary_ip') else '',
                    'serial': device.get('serial', ''),
                    'asset_tag': device.get('asset_tag', ''),
                    'last_updated': device.get('last_updated', ''),
                    'comments': device.get('comments', ''),
                    'tags': json.dumps([tag.get('name') for tag in device.get('tags', [])]),
                    'custom_fields': json.dumps(device.get('custom_fields', {}))
                })
            write_to_lookup(helper, lookup_data, 'netbox_devices.csv')

        elif output_mode == 'kvstore':
            write_to_kvstore(helper, devices, 'netbox_devices')

    except Exception as e:
        helper.log_error(f"Failed to collect devices: {str(e)}")
        raise e


def collect_virtual_machines(helper, client, ew, output_mode, checkpoint_file):
    """
    Collect virtual machines from NetBox

    Args:
        helper: Splunk modular input helper
        client: NetBox API client
        ew: Event writer
        output_mode: Output mode (events, lookup, kvstore)
        checkpoint_file: Checkpoint file path
    """
    helper.log_info("Collecting virtual machines from NetBox")

    try:
        vms = client.get_virtual_machines()
        helper.log_info(f"Retrieved {len(vms)} virtual machines from NetBox")

        if output_mode == 'events':
            for vm in vms:
                vm_id = vm.get('id')
                if not is_checkpoint_exists(checkpoint_file, vm_id):
                    write_to_splunk(helper, ew, vm, 'netbox:virtual_machines', 'netbox:vm')
                    write_to_checkpoint(checkpoint_file, vm_id)

        elif output_mode == 'lookup':
            lookup_data = []
            for vm in vms:
                lookup_data.append({
                    'id': vm.get('id'),
                    'name': vm.get('name'),
                    'status': vm.get('status', {}).get('value') if vm.get('status') else '',
                    'site': vm.get('site', {}).get('name') if vm.get('site') else '',
                    'cluster': vm.get('cluster', {}).get('name') if vm.get('cluster') else '',
                    'role': vm.get('role', {}).get('name') if vm.get('role') else '',
                    'primary_ip': vm.get('primary_ip', {}).get('address') if vm.get('primary_ip') else '',
                    'vcpus': vm.get('vcpus', ''),
                    'memory': vm.get('memory', ''),
                    'disk': vm.get('disk', ''),
                    'last_updated': vm.get('last_updated', ''),
                    'comments': vm.get('comments', ''),
                    'tags': json.dumps([tag.get('name') for tag in vm.get('tags', [])]),
                    'custom_fields': json.dumps(vm.get('custom_fields', {}))
                })
            write_to_lookup(helper, lookup_data, 'netbox_virtual_machines.csv')

        elif output_mode == 'kvstore':
            write_to_kvstore(helper, vms, 'netbox_virtual_machines')

    except Exception as e:
        helper.log_error(f"Failed to collect virtual machines: {str(e)}")
        raise e


def collect_ip_addresses(helper, client, ew, output_mode, checkpoint_file):
    """
    Collect IP addresses from NetBox

    Args:
        helper: Splunk modular input helper
        client: NetBox API client
        ew: Event writer
        output_mode: Output mode (events, lookup, kvstore)
        checkpoint_file: Checkpoint file path
    """
    helper.log_info("Collecting IP addresses from NetBox")

    try:
        ip_addresses = client.get_ip_addresses()
        helper.log_info(f"Retrieved {len(ip_addresses)} IP addresses from NetBox")

        if output_mode == 'events':
            for ip in ip_addresses:
                ip_id = ip.get('id')
                if not is_checkpoint_exists(checkpoint_file, ip_id):
                    write_to_splunk(helper, ew, ip, 'netbox:ip_addresses', 'netbox:ip')
                    write_to_checkpoint(checkpoint_file, ip_id)

        elif output_mode == 'lookup':
            lookup_data = []
            for ip in ip_addresses:
                assigned_obj = ip.get('assigned_object', {})
                lookup_data.append({
                    'id': ip.get('id'),
                    'address': ip.get('address'),
                    'status': ip.get('status', {}).get('value') if ip.get('status') else '',
                    'dns_name': ip.get('dns_name', ''),
                    'assigned_object_type': assigned_obj.get('object_type', '') if assigned_obj else '',
                    'assigned_object': assigned_obj.get('name', '') if assigned_obj else '',
                    'vrf': ip.get('vrf', {}).get('name') if ip.get('vrf') else '',
                    'tenant': ip.get('tenant', {}).get('name') if ip.get('tenant') else '',
                    'description': ip.get('description', ''),
                    'last_updated': ip.get('last_updated', ''),
                    'tags': json.dumps([tag.get('name') for tag in ip.get('tags', [])]),
                    'custom_fields': json.dumps(ip.get('custom_fields', {}))
                })
            write_to_lookup(helper, lookup_data, 'netbox_ip_addresses.csv')

        elif output_mode == 'kvstore':
            write_to_kvstore(helper, ip_addresses, 'netbox_ip_addresses')

    except Exception as e:
        helper.log_error(f"Failed to collect IP addresses: {str(e)}")
        raise e


def collect_sites(helper, client, ew, output_mode, checkpoint_file):
    """
    Collect sites from NetBox

    Args:
        helper: Splunk modular input helper
        client: NetBox API client
        ew: Event writer
        output_mode: Output mode (events, lookup, kvstore)
        checkpoint_file: Checkpoint file path
    """
    helper.log_info("Collecting sites from NetBox")

    try:
        sites = client.get_sites()
        helper.log_info(f"Retrieved {len(sites)} sites from NetBox")

        if output_mode == 'events':
            for site in sites:
                site_id = site.get('id')
                if not is_checkpoint_exists(checkpoint_file, site_id):
                    write_to_splunk(helper, ew, site, 'netbox:sites', 'netbox:site')
                    write_to_checkpoint(checkpoint_file, site_id)

        elif output_mode == 'lookup':
            lookup_data = []
            for site in sites:
                lookup_data.append({
                    'id': site.get('id'),
                    'name': site.get('name'),
                    'slug': site.get('slug'),
                    'status': site.get('status', {}).get('value') if site.get('status') else '',
                    'region': site.get('region', {}).get('name') if site.get('region') else '',
                    'facility': site.get('facility', ''),
                    'asn': site.get('asn', ''),
                    'time_zone': site.get('time_zone', ''),
                    'description': site.get('description', ''),
                    'physical_address': site.get('physical_address', ''),
                    'latitude': site.get('latitude', ''),
                    'longitude': site.get('longitude', ''),
                    'tags': json.dumps([tag.get('name') for tag in site.get('tags', [])]),
                    'custom_fields': json.dumps(site.get('custom_fields', {}))
                })
            write_to_lookup(helper, lookup_data, 'netbox_sites.csv')

        elif output_mode == 'kvstore':
            write_to_kvstore(helper, sites, 'netbox_sites')

    except Exception as e:
        helper.log_error(f"Failed to collect sites: {str(e)}")
        raise e


def collect_events(helper, ew):
    """
    Main function to collect events from NetBox

    Args:
        helper: Splunk modular input helper
        ew: Event writer
    """
    # Get input parameters
    netbox_url = helper.get_arg('netbox_url')
    netbox_token = helper.get_arg('netbox_token')
    verify_ssl = helper.get_arg('verify_ssl')
    data_type = helper.get_arg('data_type')
    output_mode = helper.get_arg('output_mode')

    # Convert string to boolean
    if isinstance(verify_ssl, str):
        verify_ssl = verify_ssl.lower() in ('true', '1', 'yes')

    helper.log_info(f"Starting NetBox data collection - Type: {data_type}, Mode: {output_mode}")

    try:
        # Initialize NetBox API client
        client = netbox_api.NetBoxAPIClient(
            url=netbox_url,
            token=netbox_token,
            verify_ssl=verify_ssl
        )

        # Setup checkpoint file
        checkpoint_dir = os.path.join(os.path.dirname(__file__), 'checkpoint')
        checkpoint_file = os.path.join(checkpoint_dir, f'checkpoint_netbox_{data_type}')

        # Collect data based on type
        if data_type == 'devices':
            collect_devices(helper, client, ew, output_mode, checkpoint_file)
        elif data_type == 'virtual_machines':
            collect_virtual_machines(helper, client, ew, output_mode, checkpoint_file)
        elif data_type == 'ip_addresses':
            collect_ip_addresses(helper, client, ew, output_mode, checkpoint_file)
        elif data_type == 'sites':
            collect_sites(helper, client, ew, output_mode, checkpoint_file)
        elif data_type == 'all':
            # Collect all data types
            collect_devices(helper, client, ew, output_mode, os.path.join(checkpoint_dir, 'checkpoint_netbox_devices'))
            collect_virtual_machines(helper, client, ew, output_mode, os.path.join(checkpoint_dir, 'checkpoint_netbox_vms'))
            collect_ip_addresses(helper, client, ew, output_mode, os.path.join(checkpoint_dir, 'checkpoint_netbox_ips'))
            collect_sites(helper, client, ew, output_mode, os.path.join(checkpoint_dir, 'checkpoint_netbox_sites'))
        else:
            raise ValueError(f"Unknown data type: {data_type}")

        helper.log_info("NetBox data collection completed successfully")

    except Exception as e:
        helper.log_error(f"Error during NetBox data collection: {str(e)}")
        raise e
