# encoding = utf-8

"""
NetBox API Client Module
Provides functionality to interact with NetBox REST API
"""

import json
import requests
from urllib.parse import urljoin
import time


class NetBoxAPIClient:
    """
    Client for interacting with NetBox REST API
    """

    def __init__(self, url, token, verify_ssl=True, timeout=30):
        """
        Initialize NetBox API client

        Args:
            url (str): NetBox instance URL
            token (str): API authentication token
            verify_ssl (bool): Whether to verify SSL certificates
            timeout (int): Request timeout in seconds
        """
        self.base_url = url.rstrip('/')
        self.api_url = urljoin(self.base_url, '/api/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self.headers = {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _make_request(self, endpoint, params=None, method='GET'):
        """
        Make HTTP request to NetBox API

        Args:
            endpoint (str): API endpoint (e.g., 'dcim/devices/')
            params (dict): Query parameters
            method (str): HTTP method

        Returns:
            dict: Response data
        """
        url = urljoin(self.api_url, endpoint)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"NetBox API request failed: {str(e)}")

    def _get_all_pages(self, endpoint, params=None, limit=1000):
        """
        Get all pages of results from paginated API endpoint

        Args:
            endpoint (str): API endpoint
            params (dict): Query parameters
            limit (int): Results per page

        Returns:
            list: All results from all pages
        """
        if params is None:
            params = {}

        params['limit'] = limit
        params['offset'] = 0

        all_results = []

        while True:
            response = self._make_request(endpoint, params=params)
            results = response.get('results', [])
            all_results.extend(results)

            # Check if there are more pages
            if not response.get('next'):
                break

            params['offset'] += limit

            # Small delay to avoid overwhelming the API
            time.sleep(0.1)

        return all_results

    def get_devices(self, limit=None, filters=None):
        """
        Get all devices from NetBox

        Args:
            limit (int): Maximum number of results (None for all)
            filters (dict): Additional filters (e.g., {'status': 'active'})

        Returns:
            list: List of device objects
        """
        endpoint = 'dcim/devices/'
        params = filters or {}

        if limit:
            params['limit'] = limit
            return self._make_request(endpoint, params=params).get('results', [])
        else:
            return self._get_all_pages(endpoint, params=params)

    def get_device_by_name(self, name):
        """
        Get device by name

        Args:
            name (str): Device name

        Returns:
            dict: Device object or None
        """
        endpoint = 'dcim/devices/'
        params = {'name': name}
        response = self._make_request(endpoint, params=params)
        results = response.get('results', [])
        return results[0] if results else None

    def get_device_by_id(self, device_id):
        """
        Get device by ID

        Args:
            device_id (int): Device ID

        Returns:
            dict: Device object
        """
        endpoint = f'dcim/devices/{device_id}/'
        return self._make_request(endpoint)

    def get_virtual_machines(self, limit=None, filters=None):
        """
        Get all virtual machines from NetBox

        Args:
            limit (int): Maximum number of results (None for all)
            filters (dict): Additional filters

        Returns:
            list: List of VM objects
        """
        endpoint = 'virtualization/virtual-machines/'
        params = filters or {}

        if limit:
            params['limit'] = limit
            return self._make_request(endpoint, params=params).get('results', [])
        else:
            return self._get_all_pages(endpoint, params=params)

    def get_vm_by_name(self, name):
        """
        Get virtual machine by name

        Args:
            name (str): VM name

        Returns:
            dict: VM object or None
        """
        endpoint = 'virtualization/virtual-machines/'
        params = {'name': name}
        response = self._make_request(endpoint, params=params)
        results = response.get('results', [])
        return results[0] if results else None

    def get_ip_addresses(self, limit=None, filters=None):
        """
        Get IP addresses from NetBox

        Args:
            limit (int): Maximum number of results (None for all)
            filters (dict): Additional filters (e.g., {'address': '192.168.1.1'})

        Returns:
            list: List of IP address objects
        """
        endpoint = 'ipam/ip-addresses/'
        params = filters or {}

        if limit:
            params['limit'] = limit
            return self._make_request(endpoint, params=params).get('results', [])
        else:
            return self._get_all_pages(endpoint, params=params)

    def get_ip_address_by_address(self, address):
        """
        Get IP address by address string

        Args:
            address (str): IP address (e.g., '192.168.1.1' or '192.168.1.1/24')

        Returns:
            dict: IP address object or None
        """
        endpoint = 'ipam/ip-addresses/'
        params = {'address': address}
        response = self._make_request(endpoint, params=params)
        results = response.get('results', [])
        return results[0] if results else None

    def get_device_interfaces(self, device_id):
        """
        Get interfaces for a specific device

        Args:
            device_id (int): Device ID

        Returns:
            list: List of interface objects
        """
        endpoint = 'dcim/interfaces/'
        params = {'device_id': device_id}
        return self._get_all_pages(endpoint, params=params)

    def get_sites(self, limit=None, filters=None):
        """
        Get all sites from NetBox

        Args:
            limit (int): Maximum number of results (None for all)
            filters (dict): Additional filters

        Returns:
            list: List of site objects
        """
        endpoint = 'dcim/sites/'
        params = filters or {}

        if limit:
            params['limit'] = limit
            return self._make_request(endpoint, params=params).get('results', [])
        else:
            return self._get_all_pages(endpoint, params=params)

    def get_racks(self, limit=None, filters=None):
        """
        Get all racks from NetBox

        Args:
            limit (int): Maximum number of results (None for all)
            filters (dict): Additional filters

        Returns:
            list: List of rack objects
        """
        endpoint = 'dcim/racks/'
        params = filters or {}

        if limit:
            params['limit'] = limit
            return self._make_request(endpoint, params=params).get('results', [])
        else:
            return self._get_all_pages(endpoint, params=params)

    def search_host(self, hostname):
        """
        Search for a host across devices and VMs

        Args:
            hostname (str): Host name to search for

        Returns:
            dict: Host information with type (device or vm)
        """
        # Try to find as device first
        device = self.get_device_by_name(hostname)
        if device:
            return {
                'type': 'device',
                'data': device
            }

        # Try to find as VM
        vm = self.get_vm_by_name(hostname)
        if vm:
            return {
                'type': 'virtual_machine',
                'data': vm
            }

        return None

    def enrich_host_data(self, hostname_or_ip):
        """
        Enrich host data by searching for hostname or IP

        Args:
            hostname_or_ip (str): Hostname or IP address

        Returns:
            dict: Enriched host data or None
        """
        # First try as hostname
        host = self.search_host(hostname_or_ip)
        if host:
            return host

        # Try as IP address
        ip_info = self.get_ip_address_by_address(hostname_or_ip)
        if ip_info:
            result = {
                'type': 'ip_address',
                'data': ip_info
            }

            # Try to get associated device or VM
            assigned_object = ip_info.get('assigned_object')
            if assigned_object:
                assigned_object_type = assigned_object.get('object_type')
                if assigned_object_type == 'dcim.interface':
                    # Get device from interface
                    device_info = assigned_object.get('device')
                    if device_info and device_info.get('id'):
                        device = self.get_device_by_id(device_info['id'])
                        result['associated_device'] = device
                elif assigned_object_type == 'virtualization.vminterface':
                    # Get VM from interface
                    vm_info = assigned_object.get('virtual_machine')
                    if vm_info:
                        result['associated_vm'] = vm_info

            return result

        return None
