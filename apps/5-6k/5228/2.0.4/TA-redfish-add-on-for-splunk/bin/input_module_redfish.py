import os
import sys
import time
import datetime
import json
import requests
import time
from requests.auth import HTTPBasicAuth


def validate_input(helper, definition):
    pass


###############################
# Manager endpoint collection #
###############################
def manager_endpoint_collection(redfish_ip, redfish_user, redfish_password, ew, helper):
    helper.log_info("MANAGER: Trying data collection for: " + redfish_ip)
    try:
        manager_url = "https://%s/redfish/v1/Managers" % (redfish_ip)
        manager_check_url = requests.get(
            manager_url,
            auth=HTTPBasicAuth(redfish_user, redfish_password),
            verify=False,
        )
        # How many managers?
        manager_count = json.loads(manager_check_url.text)["Members@odata.count"]
        helper.log_info(
            "MANAGER: Found " + str(manager_count) + " managers for: " + redfish_ip
        )
        manager_counter = 0

        while manager_counter < manager_count:
            manager_id = json.loads(manager_check_url.text)["Members"][manager_counter][
                "@odata.id"
            ]
            manager_id_url = "https://" + redfish_ip + manager_id
            manager_response = requests.get(
                manager_id_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            helper.log_info("MANAGER: Collected overview data for: " + redfish_ip)
            manager_json = manager_response.json()
            manager_udid = json.loads(manager_response.text)["UUID"]
            # Write in manager UDID for consistency
            manager_json["managerUUID"] = manager_udid
            # Write manager event if selected
            event = helper.new_event(
                host=redfish_ip,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype="redfish:manager",
                data=json.dumps(manager_json),
                done=True,
                unbroken=False,
            )
            ew.write_event(event)
            helper.log_info("MANAGER: Event data created for: " + redfish_ip)
            manager_counter += 1
    except:
        helper.log_error("MANAGER: URL not found for: " + redfish_ip)
    return manager_udid


##########################################################
# Writing data from individual Chassis to Splunk indexer #
##########################################################
def write_chassis_data_to_splunk(
    chassis_collection_dropdown,
    chassis_id_endpoint,
    chassis_check_url,
    manager_udid,
    redfish_ip,
    redfish_user,
    redfish_password,
    ew,
    helper,
):
    helper.log_info("CHASSIS: url: " + chassis_check_url.text + redfish_ip)

    # Write chassis event if selected
    for option in chassis_collection_dropdown:

        if option == "overview":
            chassis_id_overview_url = "https://" + redfish_ip + chassis_id_endpoint
            chassis_overview_response = requests.get(
                chassis_id_overview_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            chassis_overview_json = chassis_overview_response.json()
            if manager_udid:
                chassis_overview_json["managerUUID"] = manager_udid
            helper.log_info("CHASSIS: Collected overview data for: " + redfish_ip)
            event = helper.new_event(
                host=redfish_ip,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype="redfish:chassis",
                data=json.dumps(chassis_overview_json),
                done=True,
                unbroken=False,
            )
            ew.write_event(event)
            helper.log_info("CHASSIS: Overview event data created for: " + redfish_ip)

        if option == "thermal":
            chassis_id_thermal_url = (
                "https://" + redfish_ip + chassis_id_endpoint + "/Thermal"
            )
            chassis_thermal_response = requests.get(
                chassis_id_thermal_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            chassis_thermal_json = chassis_thermal_response.json()
            if manager_udid:
                chassis_thermal_json["managerUUID"] = manager_udid
            helper.log_info("CHASSIS: Collected thermal data for: " + redfish_ip)
            event = helper.new_event(
                host=redfish_ip,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype="redfish:chassis:thermal",
                data=json.dumps(chassis_thermal_json),
                done=True,
                unbroken=False,
            )
            ew.write_event(event)
            helper.log_info("CHASSIS: Thermal event data created for: " + redfish_ip)

        if option == "power":
            chassis_id_power_url = (
                "https://" + redfish_ip + chassis_id_endpoint + "/Power"
            )
            chassis_power_response = requests.get(
                chassis_id_power_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            chassis_power_json = chassis_power_response.json()
            if manager_udid:
                chassis_power_json["managerUUID"] = manager_udid
            helper.log_info("CHASSIS: Collected power data for: " + redfish_ip)
            event = helper.new_event(
                host=redfish_ip,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype="redfish:chassis:power",
                data=json.dumps(chassis_power_json),
                done=True,
                unbroken=False,
            )
            ew.write_event(event)
            helper.log_info("CHASSIS: Power event data created for: " + redfish_ip)


###############################
# Chassis endpoint collection #
###############################
def cassis_endpoint_collection(
    chassis_collection_dropdown,
    redfish_ip,
    redfish_user,
    redfish_password,
    manager_udid,
    ew,
    helper,
):
    helper.log_info("CHASSIS: Trying data collection for: " + redfish_ip)
    try:
        chassis_url = "https://%s/redfish/v1/Chassis" % (redfish_ip)
        chassis_check_url = requests.get(
            chassis_url,
            auth=HTTPBasicAuth(redfish_user, redfish_password),
            verify=False,
        )

        chassis_selection_textinput = helper.get_arg("chassis_selection_textinput")
        if not chassis_selection_textinput or chassis_selection_textinput == "":
            # How many chassis?
            helper.log_info("CHASSIS: Querying all available chassis!")
            chassis_count = json.loads(chassis_check_url.text)["Members@odata.count"]
            helper.log_info(
                "CHASSIS: Found: " + str(chassis_count) + " chassis for: " + redfish_ip
            )
            chassis_counter = 0
            while chassis_counter < chassis_count:
                chassis_id_endpoint = json.loads(chassis_check_url.text)["Members"][
                    chassis_counter
                ]["@odata.id"]
                write_chassis_data_to_splunk(
                    chassis_collection_dropdown,
                    chassis_id_endpoint,
                    chassis_check_url,
                    manager_udid,
                    redfish_ip,
                    redfish_user,
                    redfish_password,
                    ew,
                    helper,
                )
                chassis_counter += 1
        else:
            chassis_ids = chassis_selection_textinput.split(",")
            for chassis_id in chassis_ids:
                if chassis_id == "":
                    continue
                helper.log_info(f"CHASSIS: Querying Chassis with ID {chassis_id}.")
                chassis_id_endpoint = f"/redfish/v1/Chassis/{chassis_id}"
                try:
                    write_chassis_data_to_splunk(
                        chassis_collection_dropdown,
                        chassis_id_endpoint,
                        chassis_check_url,
                        manager_udid,
                        redfish_ip,
                        redfish_user,
                        redfish_password,
                        ew,
                        helper,
                    )
                except Exception as chassis_exception:
                    helper.log_error(
                        f"Something went wrong when querying for individual chassis ID: {chassis_id}: {str(chassis_exception)}. Data from this Chassis will not be written to Splunk."
                    )
                    continue
    except Exception as e:
        helper.log_error(
            f"Something went wrong during chassis endpoint collection: {str(e)}"
        )
        raise e


###############################
# Systems endpoint collection #
###############################
def systems_endpoint_collection(
    systems_dropdown, redfish_ip, redfish_user, redfish_password, ew, helper
):
    helper.log_info("Trying systems data collection for: " + redfish_ip)
    try:
        systems_url = "https://%s/redfish/v1/Systems" % (redfish_ip)
        systems_check = requests.get(
            systems_url,
            auth=HTTPBasicAuth(redfish_user, redfish_password),
            verify=False,
        )
        # How many systems?
        systems_count = json.loads(systems_check.text)["Members@odata.count"]
        helper.log_info(
            "SYSTEMS: Found " + str(systems_count) + " systems for: " + redfish_ip
        )
        systems_counter = 0
        while systems_counter < systems_count:

            # Build systems overview URL(s) - could be multiple in blade chassis
            # e.g. https://<ip>/redfish/v1/Systems/1
            systems_overview_path = json.loads(systems_check.text)["Members"][
                systems_counter
            ]["@odata.id"]
            systems_overview_url = "https://" + redfish_ip + systems_overview_path
            # Get systems overview data
            systems_overview_response = requests.get(
                systems_overview_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            systems_overview_json = systems_overview_response.json()

            # Build systems / processor URL(s) for each system(s)
            # e.g. https://<ip>/redfish/v1/Systems/1/Processors
            systems_processors_path = json.loads(systems_overview_response.text)[
                "Processors"
            ]["@odata.id"]
            systems_processors_url = "https://" + redfish_ip + systems_processors_path
            systems_processors_response = requests.get(
                systems_processors_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            # How many processors?
            processor_count = json.loads(systems_processors_response.text)[
                "Members@odata.count"
            ]
            helper.log_info(
                "SYSTEMS: Found "
                + str(processor_count)
                + " processors for: "
                + redfish_ip
            )
            processor_counter = 0
            # Read each processor URL(s) - may be multiple
            # e.g. https://<ip>/redfish/v1/Systems/1/Processors/1
            while processor_counter < processor_count:
                processor_id_path = json.loads(systems_processors_response.text)[
                    "Members"
                ][processor_counter]["@odata.id"]
                processor_id_overview_url = "https://" + redfish_ip + processor_id_path
                # Get processor details
                processor_id_overview_response = requests.get(
                    processor_id_overview_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                processor_id_overview_json = processor_id_overview_response.json()
                # Write in manager UDID in overview, processors
                # try:
                #     processor_id_overview_json['managerUUID'] = manager_udid
                #     processor_id_overview_json['chassisSerial'] = chassis_serial
                #     helper.log_info("SYSTEMS: Wrote manager UUID and system serial data in json for: " + redfish_ip)
                # except:
                #     helper.log_error("SYSTEMS: Cannot write manager UUID and system serial data in json for: " + redfish_ip)
                # Read each processor data if selected
                for option in systems_dropdown:
                    if option == "processors":
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:systems:processors",
                            data=json.dumps(processor_id_overview_json),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "SYSTEMS: Processors event data created for: " + redfish_ip
                        )
                processor_counter += 1

            # Build systems / ethernet URL(s) for each system(s)
            # e.g. https://<ip>/redfish/v1/Systems/1/EthernetInterfaces
            systems_ethernet_path = json.loads(systems_overview_response.text)[
                "EthernetInterfaces"
            ]["@odata.id"]
            systems_ethernet_url = "https://" + redfish_ip + systems_ethernet_path
            systems_ethernet_response = requests.get(
                systems_ethernet_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            # How many ethernet interfaces?
            ethernet_count = json.loads(systems_ethernet_response.text)[
                "Members@odata.count"
            ]
            helper.log_info(
                "SYSTEMS: Found "
                + str(ethernet_count)
                + " ethernet interfaces for: "
                + redfish_ip
            )
            ethernet_counter = 0
            # Read each ethernet URL(s) - may be multiple
            # e.g. https://<ip>/redfish/v1/Systems/1/EthernetInterfaces/1
            while ethernet_counter < ethernet_count:
                ethernet_id_path = json.loads(systems_ethernet_response.text)[
                    "Members"
                ][ethernet_counter]["@odata.id"]
                ethernet_id_overview_url = "https://" + redfish_ip + ethernet_id_path
                # Get processor details
                ethernet_id_overview_response = requests.get(
                    ethernet_id_overview_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                ethernet_id_overview_json = ethernet_id_overview_response.json()
                # Write in manager UDID in processors
                """
                try:
                    ethernet_id_overview_json['managerUUID'] = manager_udid
                    ethernet_id_overview_json['chassisSerial'] = chassis_serial
                    helper.log_info("SYSTEMS: Wrote manager UUID and system serial in json ethernet for: " + redfish_ip)
                except:
                    helper.log_error("SYSTEMS: Cannot write manager UUID and system serial in json ethernet for: " + redfish_ip)
                """
                # Read each processor data if selected
                for option in systems_dropdown:
                    if option == "ethernet":
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:systems:ethernet",
                            data=json.dumps(ethernet_id_overview_json),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "SYSTEMS: Ethernet event data created for: " + redfish_ip
                        )
                ethernet_counter += 1

            # Build systems / memory URL(s) for each system(s)
            # e.g. https://<ip>/redfish/v1/Systems/1/Memory
            systems_memory_path = json.loads(systems_overview_response.text)["Memory"][
                "@odata.id"
            ]
            systems_memory_url = "https://" + redfish_ip + systems_memory_path
            systems_memory_response = requests.get(
                systems_memory_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            # How many ethernet interfaces?
            memory_count = json.loads(systems_memory_response.text)[
                "Members@odata.count"
            ]
            helper.log_info(
                "SYSTEMS: Found "
                + str(memory_count)
                + " memory dimms for: "
                + redfish_ip
            )
            memory_counter = 0
            # Read each memory URL(s) - may be multiple
            # e.g. https://<ip>/redfish/v1/Systems/1/Memory/1
            while memory_counter < memory_count:
                memory_id_path = json.loads(systems_memory_response.text)["Members"][
                    memory_counter
                ]["@odata.id"]
                memory_id_overview_url = "https://" + redfish_ip + memory_id_path
                # Get memory details
                memory_id_overview_response = requests.get(
                    memory_id_overview_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                memory_id_overview_json = memory_id_overview_response.json()
                # Write in manager UDID in memory
                """
                try:
                    memory_id_overview_json['managerUUID'] = manager_udid
                    memory_id_overview_json['chassisSerial'] = chassis_serial
                    helper.log_info("SYSTEMS: Wrote manager UUID and system serial data in ethernet json for: " + redfish_ip)
                except:
                    helper.log_error("SYSTEMS: Cannot write manager UUID and system serial data in ethernet json for: " + redfish_ip)
                """
                # Read each memory data if selected
                for option in systems_dropdown:
                    if option == "memory":
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:systems:memory",
                            data=json.dumps(memory_id_overview_json),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "SYSTEMS: Memory event data created for: " + redfish_ip
                        )
                memory_counter += 1

            # Build systems / simple_storage URL for each system(s)
            # e.g. https://<ip>/redfish/v1/Systems/1/SimpleStorage
            systems_simple_storage_path = json.loads(systems_overview_response.text)[
                "SimpleStorage"
            ]["@odata.id"]
            systems_simple_storage_url = (
                "https://" + redfish_ip + systems_simple_storage_path
            )
            systems_simple_storage_response = requests.get(
                systems_simple_storage_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            # How many storage devices?
            simple_storage_count = json.loads(systems_simple_storage_response.text)[
                "Members@odata.count"
            ]
            helper.log_info(
                "SYSTEMS: Found "
                + str(simple_storage_count)
                + " simple_storage devices for: "
                + redfish_ip
            )
            simple_storage_counter = 0
            # Read each simple_storage URL(s) - may be multiple
            # e.g. https://<ip>/redfish/v1/Systems/1/Simple_Storage/1
            while simple_storage_counter < simple_storage_count:
                simple_storage_id_path = json.loads(
                    systems_simple_storage_response.text
                )["Members"][simple_storage_counter]["@odata.id"]
                simple_storage_id_overview_url = (
                    "https://" + redfish_ip + simple_storage_id_path
                )
                # Get simple_storage details
                simple_storage_id_overview_response = requests.get(
                    simple_storage_id_overview_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                simple_storage_id_overview_json = (
                    simple_storage_id_overview_response.json()
                )
                # Write in manager UDID in simple_storage
                """
                try:
                    simple_storage_id_overview_json['managerUUID'] = manager_udid
                    simple_storage_id_overview_json['chassisSerial'] = chassis_serial
                    helper.log_info("SYSTEMS: Wrote manager UUID and system serial data in simple_storage json for: " + redfish_ip)
                except:
                    helper.log_error("SYSTEMS: Cannot write manager UUID and system serial data in simple_storage json for: " + redfish_ip)
                """
                # Read each simple_storage data if selected
                for option in systems_dropdown:
                    if option == "simple_storage":
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:systems:simplestorage",
                            data=json.dumps(simple_storage_id_overview_json),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "SYSTEMS: Simple_storage event data created for: "
                            + redfish_ip
                        )
                simple_storage_counter += 1

            # Build systems / storage URL for each system(s)
            # e.g. https://<ip>/redfish/v1/Systems/1/Storage
            systems_storage_path = json.loads(systems_overview_response.text)[
                "Storage"
            ]["@odata.id"]
            systems_storage_url = "https://" + redfish_ip + systems_storage_path
            systems_storage_response = requests.get(
                systems_storage_url,
                auth=HTTPBasicAuth(redfish_user, redfish_password),
                verify=False,
            )
            # How many storage devices?
            storage_count = json.loads(systems_storage_response.text)[
                "Members@odata.count"
            ]
            helper.log_info(
                "SYSTEMS: Found "
                + str(storage_count)
                + " storage devices for: "
                + redfish_ip
            )
            storage_counter = 0
            # Read each storage URL(s) - may be multiple
            # e.g. https://<ip>/redfish/v1/Systems/1/Storage/1
            while storage_counter < storage_count:
                storage_id_path = json.loads(systems_storage_response.text)["Members"][
                    storage_counter
                ]["@odata.id"]
                storage_id_overview_url = "https://" + redfish_ip + storage_id_path
                # Get storage details
                storage_id_overview_response = requests.get(
                    storage_id_overview_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                storage_id_overview_json = storage_id_overview_response.json()
                # Write in manager UDID in storage
                """
                try:
                    storage_id_overview_json['managerUUID'] = manager_udid
                    storage_id_overview_json['chassisSerial'] = chassis_serial
                    helper.log_info("SYSTEMS: Wrote manager UUID and system serial data in storage json for: " + redfish_ip)
                except:
                    helper.log_error("SYSTEMS: Cannot write manager UUID and system serial data in storage json for: " + redfish_ip)
                """
                # Read each memory data if selected
                for option in systems_dropdown:
                    if option == "storage":
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:systems:storage",
                            data=json.dumps(storage_id_overview_json),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "SYSTEMS: Storage event data created for: " + redfish_ip
                        )
                storage_counter += 1

            # Write in manager UDID in overview
            """
            try:
                systems_overview_json['managerUUID'] = manager_udid
                systems_overview_json['chassisSerial'] = chassis_serial
                helper.log_info("SYSTEMS: Wrote manager UUID and system serial data in json overview for: " + redfish_ip)
            except:
                helper.log_error("SYSTEMS: Cannot write manager UUID and system serial data in json overview for: " + redfish_ip) 
            """
            # Write systems event if selected
            for option in systems_dropdown:
                if option == "overview":
                    event = helper.new_event(
                        host=redfish_ip,
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype="redfish:systems",
                        data=json.dumps(systems_overview_json),
                        done=True,
                        unbroken=False,
                    )
                    ew.write_event(event)
                    helper.log_info(
                        "SYSTEMS: Overview event data created for: " + redfish_ip
                    )
            systems_counter += 1
    except:
        helper.log_error("SYSTEMS: URL not found for: " + redfish_ip)


#############################
# Metric Reports collection #
#############################
def metric_report_collection(
    reports_dropdown, redfish_ip, redfish_user, redfish_password, ew, helper
):
    helper.log_info("Metric Reports: Trying data collection for: " + redfish_ip)
    try:
        for option in reports_dropdown:
            helper.log_info(
                "MetricsReports: Starting MetricReports collection for: " + redfish_ip
            )

            if option == "AggregationMetrics":
                AggregationMetrics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/AggregationMetrics"
                )
                AggregationMetrics_response = requests.get(
                    AggregationMetrics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                AggregationMetrics_count = json.loads(AggregationMetrics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "AggregationMetrics: FOUND "
                    + str(AggregationMetrics_count)
                    + "AggregationMetrics for: "
                    + redfish_ip
                )
                AggregationMetrics_counter = 0

                while AggregationMetrics_counter < AggregationMetrics_count:
                    AggregationMetrics_path = json.loads(
                        AggregationMetrics_response.text
                    )["MetricValues"][AggregationMetrics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:aggregationmetrics",
                            data=json.dumps(AggregationMetrics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "AggregationMetrics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "AggregationMetrics: Cannot write AggregationMetrics events for: "
                            + redfish_ip
                        )
                    AggregationMetrics_counter += 1

            if option == "CPUMemMetrics":
                CPUMemMetrics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/CPUMemMetrics"
                )
                CPUMemMetrics_response = requests.get(
                    CPUMemMetrics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                CPUMemMetrics_count = json.loads(CPUMemMetrics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "CPUMemMetrics: FOUND "
                    + str(CPUMemMetrics_count)
                    + "CPUMemMetrics for: "
                    + redfish_ip
                )
                CPUMemMetrics_counter = 0

                while CPUMemMetrics_counter < CPUMemMetrics_count:
                    CPUMemMetrics_path = json.loads(CPUMemMetrics_response.text)[
                        "MetricValues"
                    ][CPUMemMetrics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:cpumemmetrics",
                            data=json.dumps(CPUMemMetrics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "CPUMemMetrics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "CPUMemMetrics: Cannot write CPUMemMetrics events for: "
                            + redfish_ip
                        )
                    CPUMemMetrics_counter += 1

            if option == "CPUSensor":
                CPUSensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/CPUSensor"
                )
                CPUSensor_response = requests.get(
                    CPUSensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                CPUSensor_count = json.loads(CPUSensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "CPUSensor: FOUND "
                    + str(CPUSensor_count)
                    + "CPUSensor for: "
                    + redfish_ip
                )
                CPUSensor_counter = 0

                while CPUSensor_counter < CPUSensor_count:
                    CPUSensor_path = json.loads(CPUSensor_response.text)[
                        "MetricValues"
                    ][CPUSensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:cpusensor",
                            data=json.dumps(CPUSensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "CPUSensor: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "CPUSensor: Cannot write CPUSensor events for: "
                            + redfish_ip
                        )
                    CPUSensor_counter += 1

            if option == "CUPS":
                CUPS_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/CUPS"
                )
                CUPS_response = requests.get(
                    CUPS_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                CUPS_count = json.loads(CUPS_response.text)["MetricValues@odata.count"]
                helper.log_info(
                    "CUPS: FOUND " + str(CUPS_count) + "CUPS for: " + redfish_ip
                )
                CUPS_counter = 0

                while CUPS_counter < CUPS_count:
                    CUPS_path = json.loads(CUPS_response.text)["MetricValues"][
                        CUPS_counter
                    ]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:cups",
                            data=json.dumps(CUPS_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "CUPS: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "CUPS: Cannot write CUPS events for: " + redfish_ip
                        )
                    CUPS_counter += 1

            if option == "FanSensor":
                FanSensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/FanSensor"
                )
                FanSensor_response = requests.get(
                    FanSensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                FanSensor_count = json.loads(FanSensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "FanSensor: FOUND "
                    + str(FanSensor_count)
                    + "FanSensor for: "
                    + redfish_ip
                )
                FanSensor_counter = 0

                while FanSensor_counter < FanSensor_count:
                    FanSensor_path = json.loads(FanSensor_response.text)[
                        "MetricValues"
                    ][FanSensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:fansensor",
                            data=json.dumps(FanSensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "FanSensor: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "FanSensor: Cannot write FanSensor events for: "
                            + redfish_ip
                        )
                    FanSensor_counter += 1

            if option == "FCSensor":
                FCSensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/FCSensor"
                )
                FCSensor_response = requests.get(
                    FCSensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                FCSensor_count = json.loads(FCSensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "FCSensor: FOUND "
                    + str(FCSensor_count)
                    + "FCSensor for: "
                    + redfish_ip
                )
                FCSensor_counter = 0

                while FCSensor_counter < FCSensor_count:
                    FCSensor_path = json.loads(FCSensor_response.text)["MetricValues"][
                        FCSensor_counter
                    ]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:fcsensor",
                            data=json.dumps(FCSensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "FCSensor: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "FCSensor: Cannot write FCSensor events for: " + redfish_ip
                        )
                    FCSensor_counter += 1

            if option == "FPGASensor":
                FPGASensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/FPGASensor"
                )
                FPGASensor_response = requests.get(
                    FPGASensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                FPGASensor_count = json.loads(FPGASensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "FPGASensor: FOUND "
                    + str(FPGASensor_count)
                    + "FPGASensor for: "
                    + redfish_ip
                )
                FPGASensor_counter = 0

                while FPGASensor_counter < FPGASensor_count:
                    FPGASensor_path = json.loads(FPGASensor_response.text)[
                        "MetricValues"
                    ][FPGASensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:fpgasensor",
                            data=json.dumps(FPGASensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "FPGASensor: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "FPGASensor: Cannot write FPGASensor events for: "
                            + redfish_ip
                        )
                    FPGASensor_counter += 1

            if option == "GPUMetrics":
                GPUMetrics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/GPUMetrics"
                )
                GPUMetrics_response = requests.get(
                    GPUMetrics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                GPUMetrics_count = json.loads(GPUMetrics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "GPUMetrics: FOUND "
                    + str(GPUMetrics_count)
                    + "GPUMetrics for: "
                    + redfish_ip
                )
                GPUMetrics_counter = 0

                while GPUMetrics_counter < GPUMetrics_count:
                    GPUMetrics_path = json.loads(GPUMetrics_response.text)[
                        "MetricValues"
                    ][GPUMetrics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:gpumetrics",
                            data=json.dumps(GPUMetrics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "GPUMetrics: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "GPUMetrics: Cannot write GPUMetrics events for: "
                            + redfish_ip
                        )
                    GPUMetrics_counter += 1

            if option == "GPUStatistics":
                GPUStatistics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/GPUStatistics"
                )
                GPUStatistics_response = requests.get(
                    GPUStatistics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                GPUStatistics_count = json.loads(GPUStatistics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "GPUStatistics: FOUND "
                    + str(GPUStatistics_count)
                    + "GPUStatistics for: "
                    + redfish_ip
                )
                GPUStatistics_counter = 0

                while GPUStatistics_counter < GPUStatistics_count:
                    GPUStatistics_path = json.loads(GPUStatistics_response.text)[
                        "MetricValues"
                    ][GPUStatistics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:gpustatistics",
                            data=json.dumps(GPUStatistics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "GPUStatistics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "GPUStatistics: Cannot write GPUStatistics events for: "
                            + redfish_ip
                        )
                    GPUStatistics_counter += 1

            if option == "MemorySensor":
                MemorySensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/MemorySensor"
                )
                MemorySensor_response = requests.get(
                    MemorySensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                MemorySensor_count = json.loads(MemorySensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "MemorySensor: FOUND "
                    + str(MemorySensor_count)
                    + "MemorySensor for: "
                    + redfish_ip
                )
                MemorySensor_counter = 0

                while MemorySensor_counter < MemorySensor_count:
                    MemorySensor_path = json.loads(MemorySensor_response.text)[
                        "MetricValues"
                    ][MemorySensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:memorysensor",
                            data=json.dumps(MemorySensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "MemorySensor: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "MemorySensor: Cannot write MemorySensor events for: "
                            + redfish_ip
                        )
                    MemorySensor_counter += 1

            if option == "NICSensor":
                NICSensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/NICSensor"
                )
                NICSensor_response = requests.get(
                    NICSensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                NICSensor_count = json.loads(NICSensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "NICSensor: FOUND "
                    + str(NICSensor_count)
                    + "NICSensor for: "
                    + redfish_ip
                )
                NICSensor_counter = 0

                while NICSensor_counter < NICSensor_count:
                    NICSensor_path = json.loads(NICSensor_response.text)[
                        "MetricValues"
                    ][NICSensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:nicsensor",
                            data=json.dumps(NICSensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "NICSensor: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "NICSensor: Cannot write NICSensor events for: "
                            + redfish_ip
                        )
                    NICSensor_counter += 1

            if option == "NICStatistics":
                NICStatistics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/NICStatistics"
                )
                NICStatistics_response = requests.get(
                    NICStatistics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                NICStatistics_count = json.loads(NICStatistics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "NICStatistics: FOUND "
                    + str(NICStatistics_count)
                    + "NICStatistics for: "
                    + redfish_ip
                )
                NICStatistics_counter = 0

                while NICStatistics_counter < NICStatistics_count:
                    NICStatistics_path = json.loads(NICStatistics_response.text)[
                        "MetricValues"
                    ][NICStatistics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:nicstatistics",
                            data=json.dumps(NICStatistics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "NICStatistics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "NICStatistics: Cannot write NICStatistics events for: "
                            + redfish_ip
                        )
                    NICStatistics_counter += 1

            if option == "NVMeSMARTData":
                NVMeSMARTData_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/NVMeSMARTData"
                )
                NVMeSMARTData_response = requests.get(
                    NVMeSMARTData_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                NVMeSMARTData_count = json.loads(NVMeSMARTData_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "NVMeSMARTData: FOUND "
                    + str(NVMeSMARTData_count)
                    + "NVMeSMARTData for: "
                    + redfish_ip
                )
                NVMeSMARTData_counter = 0

                while NVMeSMARTData_counter < NVMeSMARTData_count:
                    NVMeSMARTData_path = json.loads(NVMeSMARTData_response.text)[
                        "MetricValues"
                    ][NVMeSMARTData_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:nvmesmartdata",
                            data=json.dumps(NVMeSMARTData_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "NVMeSMARTData: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "NVMeSMARTData: Cannot write NVMeSMARTData events for: "
                            + redfish_ip
                        )
                    NVMeSMARTData_counter += 1

            if option == "PowerMetrics":
                PowerMetrics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/PowerMetrics"
                )
                PowerMetrics_response = requests.get(
                    PowerMetrics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                PowerMetrics_count = json.loads(PowerMetrics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "PowerMetrics: FOUND "
                    + str(PowerMetrics_count)
                    + "PowerMetrics for: "
                    + redfish_ip
                )
                PowerMetrics_counter = 0

                while PowerMetrics_counter < PowerMetrics_count:
                    PowerMetrics_path = json.loads(PowerMetrics_response.text)[
                        "MetricValues"
                    ][PowerMetrics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:powermetrics",
                            data=json.dumps(PowerMetrics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "PowerMetrics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "PowerMetrics: Cannot write PowerMetrics events for: "
                            + redfish_ip
                        )
                    PowerMetrics_counter += 1

            if option == "PowerStatistics":
                PowerStatistics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/PowerStatistics"
                )
                PowerStatistics_response = requests.get(
                    PowerStatistics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                PowerStatistics_count = json.loads(PowerStatistics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "PowerStatistics: FOUND "
                    + str(PowerStatistics_count)
                    + "PowerStatistics for: "
                    + redfish_ip
                )
                PowerStatistics_counter = 0

                while PowerStatistics_counter < PowerStatistics_count:
                    PowerStatistics_path = json.loads(PowerStatistics_response.text)[
                        "MetricValues"
                    ][PowerStatistics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:powerstatistics",
                            data=json.dumps(PowerStatistics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "PowerStatistics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "PowerStatistics: Cannot write PowerStatistics events for: "
                            + redfish_ip
                        )
                    PowerStatistics_counter += 1

            if option == "PSUMetrics":
                PSUMetrics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/PSUMetrics"
                )
                PSUMetrics_response = requests.get(
                    PSUMetrics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                PSUMetrics_count = json.loads(PSUMetrics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "PSUMetrics: FOUND "
                    + str(PSUMetrics_count)
                    + "PSUMetrics for: "
                    + redfish_ip
                )
                PSUMetrics_counter = 0

                while PSUMetrics_counter < PSUMetrics_count:
                    PSUMetrics_path = json.loads(PSUMetrics_response.text)[
                        "MetricValues"
                    ][PSUMetrics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:psumetrics",
                            data=json.dumps(PSUMetrics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "PSUMetrics: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "PSUMetrics: Cannot write PSUMetrics events for: "
                            + redfish_ip
                        )
                    PSUMetrics_counter += 1

            if option == "Sensor":
                Sensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/Sensor"
                )
                Sensor_response = requests.get(
                    Sensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                Sensor_count = json.loads(Sensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "Sensor: FOUND " + str(Sensor_count) + "Sensor for: " + redfish_ip
                )
                Sensor_counter = 0

                while Sensor_counter < Sensor_count:
                    Sensor_path = json.loads(Sensor_response.text)["MetricValues"][
                        Sensor_counter
                    ]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:sensor",
                            data=json.dumps(Sensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "Sensor: Overview event data created for: " + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "Sensor: Cannot write Sensor events for: " + redfish_ip
                        )
                    Sensor_counter += 1

            if option == "StorageDiskSMARTData":
                StorageDiskSMARTData_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/StorageDiskSMARTData"
                )
                StorageDiskSMARTData_response = requests.get(
                    StorageDiskSMARTData_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                StorageDiskSMARTData_count = json.loads(
                    StorageDiskSMARTData_response.text
                )["MetricValues@odata.count"]
                helper.log_info(
                    "StorageDiskSMARTData: FOUND "
                    + str(StorageDiskSMARTData_count)
                    + "StorageDiskSMARTData for: "
                    + redfish_ip
                )
                StorageDiskSMARTData_counter = 0

                while StorageDiskSMARTData_counter < StorageDiskSMARTData_count:
                    StorageDiskSMARTData_path = json.loads(
                        StorageDiskSMARTData_response.text
                    )["MetricValues"][StorageDiskSMARTData_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:storagedisksmartdata",
                            data=json.dumps(StorageDiskSMARTData_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "StorageDiskSMARTData: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "StorageDiskSMARTData: Cannot write StorageDiskSMARTData events for: "
                            + redfish_ip
                        )
                    StorageDiskSMARTData_counter += 1

            if option == "StorageSensor":
                StorageSensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/StorageSensor"
                )
                StorageSensor_response = requests.get(
                    StorageSensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                StorageSensor_count = json.loads(StorageSensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "StorageSensor: FOUND "
                    + str(StorageSensor_count)
                    + "StorageSensor for: "
                    + redfish_ip
                )
                StorageSensor_counter = 0

                while StorageSensor_counter < StorageSensor_count:
                    StorageSensor_path = json.loads(StorageSensor_response.text)[
                        "MetricValues"
                    ][StorageSensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:storagesensor",
                            data=json.dumps(StorageSensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "StorageSensor: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "StorageSensor: Cannot write StorageSensor events for: "
                            + redfish_ip
                        )
                    StorageSensor_counter += 1

            if option == "ThermalMetrics":
                ThermalMetrics_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/ThermalMetrics"
                )
                ThermalMetrics_response = requests.get(
                    ThermalMetrics_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                ThermalMetrics_count = json.loads(ThermalMetrics_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "ThermalMetrics: FOUND "
                    + str(ThermalMetrics_count)
                    + "ThermalMetrics for: "
                    + redfish_ip
                )
                ThermalMetrics_counter = 0

                while ThermalMetrics_counter < ThermalMetrics_count:
                    ThermalMetrics_path = json.loads(ThermalMetrics_response.text)[
                        "MetricValues"
                    ][ThermalMetrics_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:thermalmetrics",
                            data=json.dumps(ThermalMetrics_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "ThermalMetrics: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "ThermalMetrics: Cannot write ThermalMetrics events for: "
                            + redfish_ip
                        )
                    ThermalMetrics_counter += 1

            if option == "ThermalSensor":
                ThermalSensor_url = (
                    "https://"
                    + redfish_ip
                    + "/redfish/v1/TelemetryService/MetricReports/ThermalSensor"
                )
                ThermalSensor_response = requests.get(
                    ThermalSensor_url,
                    auth=HTTPBasicAuth(redfish_user, redfish_password),
                    verify=False,
                )
                ThermalSensor_count = json.loads(ThermalSensor_response.text)[
                    "MetricValues@odata.count"
                ]
                helper.log_info(
                    "ThermalSensor: FOUND "
                    + str(ThermalSensor_count)
                    + "ThermalSensor for: "
                    + redfish_ip
                )
                ThermalSensor_counter = 0

                while ThermalSensor_counter < ThermalSensor_count:
                    ThermalSensor_path = json.loads(ThermalSensor_response.text)[
                        "MetricValues"
                    ][ThermalSensor_counter]
                    try:
                        event = helper.new_event(
                            host=redfish_ip,
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype="redfish:telemetry:thermalsensor",
                            data=json.dumps(ThermalSensor_path),
                            done=True,
                            unbroken=False,
                        )
                        ew.write_event(event)
                        helper.log_info(
                            "ThermalSensor: Overview event data created for: "
                            + redfish_ip
                        )
                    except:
                        helper.log_error(
                            "ThermalSensor: Cannot write ThermalSensor events for: "
                            + redfish_ip
                        )
                    ThermalSensor_counter += 1

            helper.log_info(
                "MetricsReports: Finished MetricReports collection for: " + redfish_ip
            )

    except:
        helper.log_error("Metric Reports: URL not found for: " + redfish_ip)


def collect_events(helper, ew):

    # Get input settings
    global_account = helper.get_arg("global_account")
    redfish_user = global_account["username"]
    redfish_password = global_account["password"]
    redfish_ip = helper.get_arg("redfish_ip")
    # redfish_st = helper.get_arg("redfish_st")

    # Get what to collect
    manager_collection = helper.get_arg("manager_collection")
    chassis_collection_dropdown = helper.get_arg("chassis_collection_dropdown")
    systems_dropdown = helper.get_arg("systems_dropdown")
    reports_dropdown = helper.get_arg("reports_dropdown")

    helper.log_info("START: Beginning collection for: " + redfish_ip)
    start = time.time()

    # Manager endpoint collection
    manager_udid = None
    if manager_collection == "1":
        manager_udid = manager_endpoint_collection(
            redfish_ip, redfish_user, redfish_password, ew, helper
        )
    else:
        helper.log_info("Skipping MANAGER endpoint collection.")

    # Chassis Collection
    if chassis_collection_dropdown is not None:
        cassis_endpoint_collection(
            chassis_collection_dropdown,
            redfish_ip,
            redfish_user,
            redfish_password,
            manager_udid,
            ew,
            helper,
        )
    else:
        helper.log_info("Skipping CHASSIS endpoint collection.")

    # Systems endpoint collection
    if systems_dropdown is not None:
        systems_endpoint_collection(
            systems_dropdown, redfish_ip, redfish_user, redfish_password, ew, helper
        )
    else:
        helper.log_info("Skipping SYSTEMS endpoint collection.")

    # Metric report collection
    if reports_dropdown is not None:
        metric_report_collection(
            reports_dropdown, redfish_ip, redfish_user, redfish_password, ew, helper
        )
    else:
        helper.log_info("Skipping METRIC report collection.")

    # Finish up
    helper.log_info("FINISH: Ending collection for: " + redfish_ip)
    end_time = round(time.time() - start, 2)
    helper.log_info(
        "FINISH: Collection took: "
        + str(end_time)
        + " secs to collect data for: "
        + redfish_ip
    )
