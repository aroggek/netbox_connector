#!/usr/bin/env python
# encoding = utf-8

"""
NetBox Enrichment Custom Search Command
Enriches Splunk events with data from NetBox
"""

import sys
import os
import json

# Add bin directory to path
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    import netbox_api
except ImportError as e:
    print(f"Import error: {str(e)}")
    sys.exit(1)


@Configuration()
class NetBoxEnrichCommand(StreamingCommand):
    """
    Custom search command to enrich events with NetBox data

    Usage:
        ... | netboxenrich field=<field_name> netbox_url=<url> netbox_token=<token>

    Example:
        index=main | netboxenrich field=host netbox_url="https://netbox.example.com" netbox_token="your_token"
    """

    field = Option(
        doc='''
        **Syntax:** **field=***<field_name>*
        **Description:** Field name containing hostname or IP to enrich
        **Default:** host
        ''',
        require=False,
        default='host',
        validate=validators.Fieldname()
    )

    netbox_url = Option(
        doc='''
        **Syntax:** **netbox_url=***<url>*
        **Description:** NetBox instance URL
        **Required:** True
        ''',
        require=True
    )

    netbox_token = Option(
        doc='''
        **Syntax:** **netbox_token=***<token>*
        **Description:** NetBox API token
        **Required:** True
        ''',
        require=True
    )

    verify_ssl = Option(
        doc='''
        **Syntax:** **verify_ssl=***<bool>*
        **Description:** Verify SSL certificate
        **Default:** True
        ''',
        require=False,
        default=True,
        validate=validators.Boolean()
    )

    prefix = Option(
        doc='''
        **Syntax:** **prefix=***<prefix>*
        **Description:** Prefix for enriched fields
        **Default:** netbox_
        ''',
        require=False,
        default='netbox_'
    )

    def stream(self, records):
        """
        Process and enrich records

        Args:
            records: Iterator of event records

        Yields:
            Enriched event records
        """
        try:
            # Initialize NetBox API client
            client = netbox_api.NetBoxAPIClient(
                url=self.netbox_url,
                token=self.netbox_token,
                verify_ssl=self.verify_ssl
            )

            # Process each record
            for record in records:
                try:
                    # Get the value to lookup
                    lookup_value = record.get(self.field)

                    if not lookup_value:
                        self.logger.warning(f"Field '{self.field}' not found in record")
                        yield record
                        continue

                    # Enrich data from NetBox
                    enriched_data = client.enrich_host_data(str(lookup_value))

                    if enriched_data:
                        # Add enriched fields to record
                        record[f'{self.prefix}found'] = True
                        record[f'{self.prefix}type'] = enriched_data.get('type', '')

                        # Flatten and add data
                        data = enriched_data.get('data', {})
                        if data:
                            # Add main fields
                            record[f'{self.prefix}id'] = data.get('id', '')
                            record[f'{self.prefix}name'] = data.get('name', '')

                            if enriched_data['type'] == 'device':
                                # Device-specific fields
                                record[f'{self.prefix}device_type'] = data.get('device_type', {}).get('display', '') if data.get('device_type') else ''
                                record[f'{self.prefix}device_role'] = data.get('device_role', {}).get('name', '') if data.get('device_role') else ''
                                record[f'{self.prefix}site'] = data.get('site', {}).get('name', '') if data.get('site') else ''
                                record[f'{self.prefix}rack'] = data.get('rack', {}).get('name', '') if data.get('rack') else ''
                                record[f'{self.prefix}status'] = data.get('status', {}).get('value', '') if data.get('status') else ''
                                record[f'{self.prefix}primary_ip'] = data.get('primary_ip', {}).get('address', '') if data.get('primary_ip') else ''
                                record[f'{self.prefix}serial'] = data.get('serial', '')
                                record[f'{self.prefix}asset_tag'] = data.get('asset_tag', '')

                            elif enriched_data['type'] == 'virtual_machine':
                                # VM-specific fields
                                record[f'{self.prefix}status'] = data.get('status', {}).get('value', '') if data.get('status') else ''
                                record[f'{self.prefix}site'] = data.get('site', {}).get('name', '') if data.get('site') else ''
                                record[f'{self.prefix}cluster'] = data.get('cluster', {}).get('name', '') if data.get('cluster') else ''
                                record[f'{self.prefix}role'] = data.get('role', {}).get('name', '') if data.get('role') else ''
                                record[f'{self.prefix}primary_ip'] = data.get('primary_ip', {}).get('address', '') if data.get('primary_ip') else ''
                                record[f'{self.prefix}vcpus'] = data.get('vcpus', '')
                                record[f'{self.prefix}memory'] = data.get('memory', '')
                                record[f'{self.prefix}disk'] = data.get('disk', '')

                            elif enriched_data['type'] == 'ip_address':
                                # IP-specific fields
                                record[f'{self.prefix}address'] = data.get('address', '')
                                record[f'{self.prefix}status'] = data.get('status', {}).get('value', '') if data.get('status') else ''
                                record[f'{self.prefix}dns_name'] = data.get('dns_name', '')

                                # Add associated device or VM info
                                if 'associated_device' in enriched_data:
                                    assoc_dev = enriched_data['associated_device']
                                    record[f'{self.prefix}associated_type'] = 'device'
                                    record[f'{self.prefix}associated_name'] = assoc_dev.get('name', '')
                                    record[f'{self.prefix}associated_site'] = assoc_dev.get('site', {}).get('name', '') if assoc_dev.get('site') else ''
                                elif 'associated_vm' in enriched_data:
                                    assoc_vm = enriched_data['associated_vm']
                                    record[f'{self.prefix}associated_type'] = 'virtual_machine'
                                    record[f'{self.prefix}associated_name'] = assoc_vm.get('name', '')

                            # Add tags if present
                            if 'tags' in data:
                                tags = [tag.get('name', '') for tag in data.get('tags', [])]
                                record[f'{self.prefix}tags'] = json.dumps(tags)

                            # Add custom fields if present
                            if 'custom_fields' in data:
                                custom_fields = data.get('custom_fields', {})
                                for cf_key, cf_value in custom_fields.items():
                                    record[f'{self.prefix}cf_{cf_key}'] = str(cf_value) if cf_value else ''
                    else:
                        record[f'{self.prefix}found'] = False
                        self.logger.debug(f"No NetBox data found for: {lookup_value}")

                except Exception as e:
                    self.logger.error(f"Error enriching record: {str(e)}")
                    record[f'{self.prefix}error'] = str(e)

                yield record

        except Exception as e:
            self.logger.error(f"Fatal error in NetBox enrichment: {str(e)}")
            raise


if __name__ == "__main__":
    dispatch(NetBoxEnrichCommand, sys.argv, sys.stdin, sys.stdout, __name__)
