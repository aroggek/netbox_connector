#!/usr/bin/env python
# encoding = utf-8

"""
NetBox Connector Modular Input for Splunk
Main entry point for the modular input
"""

import os
import sys
import json

# Add bin directory to path
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

try:
    from splunklib import modularinput as smi
    import input_module_netbox as input_module
except ImportError as e:
    print(f"Import error: {str(e)}")
    sys.exit(1)


class ModInputNetBox(smi.Script):
    """
    NetBox Modular Input class
    """

    def get_scheme(self):
        """
        Define the input scheme with all parameters

        Returns:
            Scheme: Modular input scheme
        """
        scheme = smi.Scheme("NetBox Connector")
        scheme.description = "Collects data from NetBox DCIM/IPAM system via REST API"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.streaming_mode_xml = True

        # Input name
        scheme.add_argument(smi.Argument(
            name="name",
            title="Input Name",
            description="Unique name for this NetBox data input",
            data_type=smi.Argument.data_type_string,
            required_on_create=True
        ))

        # NetBox URL
        scheme.add_argument(smi.Argument(
            name="netbox_url",
            title="NetBox URL",
            description="NetBox instance URL (e.g., https://netbox.example.com)",
            data_type=smi.Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        ))

        # NetBox API Token
        scheme.add_argument(smi.Argument(
            name="netbox_token",
            title="NetBox API Token",
            description="API authentication token from NetBox",
            data_type=smi.Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        ))

        # Data Type
        scheme.add_argument(smi.Argument(
            name="data_type",
            title="Data Type",
            description="Type of data to collect (devices, virtual_machines, ip_addresses, sites, all)",
            data_type=smi.Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        ))

        # Output Mode
        scheme.add_argument(smi.Argument(
            name="output_mode",
            title="Output Mode",
            description="How to output data (events, lookup, kvstore)",
            data_type=smi.Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        ))

        # Verify SSL
        scheme.add_argument(smi.Argument(
            name="verify_ssl",
            title="Verify SSL Certificate",
            description="Verify SSL certificate when connecting to NetBox",
            data_type=smi.Argument.data_type_boolean,
            required_on_create=False,
            required_on_edit=False
        ))

        # Interval (built-in)
        scheme.add_argument(smi.Argument(
            name="interval",
            title="Interval",
            description="Polling interval in seconds",
            data_type=smi.Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        ))

        return scheme

    def validate_input(self, validation_definition):
        """
        Validate input parameters

        Args:
            validation_definition: Validation definition object

        Raises:
            Exception: If validation fails
        """
        try:
            input_module.validate_input(self, validation_definition)
        except Exception as e:
            raise Exception(f"Input validation failed: {str(e)}")

    def stream_events(self, inputs, ew):
        """
        Stream events to Splunk

        Args:
            inputs: Input definitions
            ew: Event writer
        """
        # Get input configuration
        for input_name, input_item in inputs.inputs.items():
            try:
                # Create a helper-like object with input parameters
                helper = InputHelper(input_item, self.service, ew)

                # Collect events
                input_module.collect_events(helper, ew)

            except Exception as e:
                ew.log(smi.EventWriter.ERROR, f"Error collecting events for input {input_name}: {str(e)}")


class InputHelper:
    """
    Helper class to provide Splunk modular input helper interface
    """

    def __init__(self, input_item, service, ew):
        """
        Initialize helper

        Args:
            input_item: Input item configuration
            service: Splunk service
            ew: Event writer
        """
        self.input_item = input_item
        self.service = service
        self.ew = ew

    def get_arg(self, arg_name):
        """
        Get input argument value

        Args:
            arg_name: Argument name

        Returns:
            Argument value
        """
        return self.input_item.get(arg_name)

    def log_info(self, message):
        """
        Log info message

        Args:
            message: Message to log
        """
        self.ew.log(smi.EventWriter.INFO, message)

    def log_error(self, message):
        """
        Log error message

        Args:
            message: Message to log
        """
        self.ew.log(smi.EventWriter.ERROR, message)

    def log_warning(self, message):
        """
        Log warning message

        Args:
            message: Message to log
        """
        self.ew.log(smi.EventWriter.WARN, message)

    def log_debug(self, message):
        """
        Log debug message

        Args:
            message: Message to log
        """
        self.ew.log(smi.EventWriter.DEBUG, message)

    def new_event(self, data, time=None, host=None, source=None, sourcetype=None, done=True, unbroken=True):
        """
        Create new event

        Args:
            data: Event data
            time: Event time
            host: Event host
            source: Event source
            sourcetype: Event sourcetype
            done: Event done flag
            unbroken: Event unbroken flag

        Returns:
            Event object
        """
        event = smi.Event()
        event.data = data

        if time:
            event.time = time
        if host:
            event.host = host
        if source:
            event.source = source
        if sourcetype:
            event.sourcetype = sourcetype
        if done:
            event.done = done
        if unbroken:
            event.unbroken = unbroken

        return event


if __name__ == "__main__":
    exitcode = ModInputNetBox().run(sys.argv)
    sys.exit(exitcode)
