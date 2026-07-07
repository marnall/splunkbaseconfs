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

def collect_events(helper, ew):

    # Get input settings
    global_account = helper.get_arg('global_account')
    redfish_user = global_account['username']
    redfish_password = global_account['password']
    redfish_ip = helper.get_arg("redfish_ip")

    #what to collect
    reports_dropdown  = helper.get_arg('reports_dropdown')
    
    #starter log for error checking
    helper.log_info("START: Beginning collection for: " + redfish_ip)
    start = time.time()
    try:
        for option in reports_dropdown:
            helper.log_info("MetricsReports: Starting MetricReports collection for: " + redfish_ip)
            
            if option == 'AggregationMetrics':
                AggregationMetrics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/AggregationMetrics'
                AggregationMetrics_response = requests.get(AggregationMetrics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                AggregationMetrics_count = json.loads(AggregationMetrics_response.text)["MetricValues@odata.count"]
                helper.log_info("AggregationMetrics: FOUND " + str(AggregationMetrics_count) + "AggregationMetrics for: " + redfish_ip)
                AggregationMetrics_counter = 0

                while AggregationMetrics_counter < AggregationMetrics_count:
                    AggregationMetrics_path = json.loads(AggregationMetrics_response.text)["MetricValues"][AggregationMetrics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:aggregationmetrics", data=json.dumps(AggregationMetrics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("AggregationMetrics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("AggregationMetrics: Cannot write AggregationMetrics events for: " + redfish_ip)    
                    AggregationMetrics_counter += 1

            if option == 'CPUMemMetrics':
                CPUMemMetrics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/CPUMemMetrics'
                CPUMemMetrics_response = requests.get(CPUMemMetrics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                CPUMemMetrics_count = json.loads(CPUMemMetrics_response.text)["MetricValues@odata.count"]
                helper.log_info("CPUMemMetrics: FOUND " + str(CPUMemMetrics_count) + "CPUMemMetrics for: " + redfish_ip)
                CPUMemMetrics_counter = 0

                while CPUMemMetrics_counter < CPUMemMetrics_count:
                    CPUMemMetrics_path = json.loads(CPUMemMetrics_response.text)["MetricValues"][CPUMemMetrics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:cpumemmetrics", data=json.dumps(CPUMemMetrics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("CPUMemMetrics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("CPUMemMetrics: Cannot write CPUMemMetrics events for: " + redfish_ip)    
                    CPUMemMetrics_counter += 1

            if option == 'CPUSensor':
                CPUSensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/CPUSensor'
                CPUSensor_response = requests.get(CPUSensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                CPUSensor_count = json.loads(CPUSensor_response.text)["MetricValues@odata.count"]
                helper.log_info("CPUSensor: FOUND " + str(CPUSensor_count) + "CPUSensor for: " + redfish_ip)
                CPUSensor_counter = 0

                while CPUSensor_counter < CPUSensor_count:
                    CPUSensor_path = json.loads(CPUSensor_response.text)["MetricValues"][CPUSensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:cpusensor", data=json.dumps(CPUSensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("CPUSensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("CPUSensor: Cannot write CPUSensor events for: " + redfish_ip)    
                    CPUSensor_counter += 1

            if option == 'CUPS':
                CUPS_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/CUPS'
                CUPS_response = requests.get(CUPS_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                CUPS_count = json.loads(CUPS_response.text)["MetricValues@odata.count"]
                helper.log_info("CUPS: FOUND " + str(CUPS_count) + "CUPS for: " + redfish_ip)
                CUPS_counter = 0

                while CUPS_counter < CUPS_count:
                    CUPS_path = json.loads(CUPS_response.text)["MetricValues"][CUPS_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:cups", data=json.dumps(CUPS_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("CUPS: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("CUPS: Cannot write CUPS events for: " + redfish_ip)    
                    CUPS_counter += 1

            if option == 'FanSensor':
                FanSensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/FanSensor'
                FanSensor_response = requests.get(FanSensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                FanSensor_count = json.loads(FanSensor_response.text)["MetricValues@odata.count"]
                helper.log_info("FanSensor: FOUND " + str(FanSensor_count) + "FanSensor for: " + redfish_ip)
                FanSensor_counter = 0

                while FanSensor_counter < FanSensor_count:
                    FanSensor_path = json.loads(FanSensor_response.text)["MetricValues"][FanSensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:fansensor", data=json.dumps(FanSensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("FanSensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("FanSensor: Cannot write FanSensor events for: " + redfish_ip)    
                    FanSensor_counter += 1
      
            if option == 'FCSensor':
                FCSensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/FCSensor'
                FCSensor_response = requests.get(FCSensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                FCSensor_count = json.loads(FCSensor_response.text)["MetricValues@odata.count"]
                helper.log_info("FCSensor: FOUND " + str(FCSensor_count) + "FCSensor for: " + redfish_ip)
                FCSensor_counter = 0

                while FCSensor_counter < FCSensor_count:
                    FCSensor_path = json.loads(FCSensor_response.text)["MetricValues"][FCSensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:fcsensor", data=json.dumps(FCSensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("FCSensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("FCSensor: Cannot write FCSensor events for: " + redfish_ip)    
                    FCSensor_counter += 1
                    
            if option == 'FPGASensor':
                FPGASensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/FPGASensor'
                FPGASensor_response = requests.get(FPGASensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                FPGASensor_count = json.loads(FPGASensor_response.text)["MetricValues@odata.count"]
                helper.log_info("FPGASensor: FOUND " + str(FPGASensor_count) + "FPGASensor for: " + redfish_ip)
                FPGASensor_counter = 0

                while FPGASensor_counter < FPGASensor_count:
                    FPGASensor_path = json.loads(FPGASensor_response.text)["MetricValues"][FPGASensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:fpgasensor", data=json.dumps(FPGASensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("FPGASensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("FPGASensor: Cannot write FPGASensor events for: " + redfish_ip)    
                    FPGASensor_counter += 1

            if option == 'GPUMetrics':
                GPUMetrics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/GPUMetrics'
                GPUMetrics_response = requests.get(GPUMetrics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                GPUMetrics_count = json.loads(GPUMetrics_response.text)["MetricValues@odata.count"]
                helper.log_info("GPUMetrics: FOUND " + str(GPUMetrics_count) + "GPUMetrics for: " + redfish_ip)
                GPUMetrics_counter = 0

                while GPUMetrics_counter < GPUMetrics_count:
                    GPUMetrics_path = json.loads(GPUMetrics_response.text)["MetricValues"][GPUMetrics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:gpumetrics", data=json.dumps(GPUMetrics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("GPUMetrics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("GPUMetrics: Cannot write GPUMetrics events for: " + redfish_ip)    
                    GPUMetrics_counter += 1

            if option == 'GPUStatistics':
                GPUStatistics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/GPUStatistics'
                GPUStatistics_response = requests.get(GPUStatistics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                GPUStatistics_count = json.loads(GPUStatistics_response.text)["MetricValues@odata.count"]
                helper.log_info("GPUStatistics: FOUND " + str(GPUStatistics_count) + "GPUStatistics for: " + redfish_ip)
                GPUStatistics_counter = 0

                while GPUStatistics_counter < GPUStatistics_count:
                    GPUStatistics_path = json.loads(GPUStatistics_response.text)["MetricValues"][GPUStatistics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:gpustatistics", data=json.dumps(GPUStatistics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("GPUStatistics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("GPUStatistics: Cannot write GPUStatistics events for: " + redfish_ip)    
                    GPUStatistics_counter += 1

            if option == 'MemorySensor':
                MemorySensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/MemorySensor'
                MemorySensor_response = requests.get(MemorySensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                MemorySensor_count = json.loads(MemorySensor_response.text)["MetricValues@odata.count"]
                helper.log_info("MemorySensor: FOUND " + str(MemorySensor_count) + "MemorySensor for: " + redfish_ip)
                MemorySensor_counter = 0

                while MemorySensor_counter < MemorySensor_count:
                    MemorySensor_path = json.loads(MemorySensor_response.text)["MetricValues"][MemorySensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:memorysensor", data=json.dumps(MemorySensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("MemorySensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("MemorySensor: Cannot write MemorySensor events for: " + redfish_ip)    
                    MemorySensor_counter += 1

            if option == 'NICSensor':
                NICSensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/NICSensor'
                NICSensor_response = requests.get(NICSensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                NICSensor_count = json.loads(NICSensor_response.text)["MetricValues@odata.count"]
                helper.log_info("NICSensor: FOUND " + str(NICSensor_count) + "NICSensor for: " + redfish_ip)
                NICSensor_counter = 0

                while NICSensor_counter < NICSensor_count:
                    NICSensor_path = json.loads(NICSensor_response.text)["MetricValues"][NICSensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:nicsensor", data=json.dumps(NICSensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("NICSensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("NICSensor: Cannot write NICSensor events for: " + redfish_ip)    
                    NICSensor_counter += 1

            if option == 'NICStatistics':
                NICStatistics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/NICStatistics'
                NICStatistics_response = requests.get(NICStatistics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                NICStatistics_count = json.loads(NICStatistics_response.text)["MetricValues@odata.count"]
                helper.log_info("NICStatistics: FOUND " + str(NICStatistics_count) + "NICStatistics for: " + redfish_ip)
                NICStatistics_counter = 0

                while NICStatistics_counter < NICStatistics_count:
                    NICStatistics_path = json.loads(NICStatistics_response.text)["MetricValues"][NICStatistics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:nicstatistics", data=json.dumps(NICStatistics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("NICStatistics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("NICStatistics: Cannot write NICStatistics events for: " + redfish_ip)    
                    NICStatistics_counter += 1

            if option == 'NVMeSMARTData':
                NVMeSMARTData_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/NVMeSMARTData'
                NVMeSMARTData_response = requests.get(NVMeSMARTData_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                NVMeSMARTData_count = json.loads(NVMeSMARTData_response.text)["MetricValues@odata.count"]
                helper.log_info("NVMeSMARTData: FOUND " + str(NVMeSMARTData_count) + "NVMeSMARTData for: " + redfish_ip)
                NVMeSMARTData_counter = 0

                while NVMeSMARTData_counter < NVMeSMARTData_count:
                    NVMeSMARTData_path = json.loads(NVMeSMARTData_response.text)["MetricValues"][NVMeSMARTData_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:nvmesmartdata", data=json.dumps(NVMeSMARTData_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("NVMeSMARTData: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("NVMeSMARTData: Cannot write NVMeSMARTData events for: " + redfish_ip)    
                    NVMeSMARTData_counter += 1

            if option == 'PowerMetrics':
                PowerMetrics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/PowerMetrics'
                PowerMetrics_response = requests.get(PowerMetrics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                PowerMetrics_count = json.loads(PowerMetrics_response.text)["MetricValues@odata.count"]
                helper.log_info("PowerMetrics: FOUND " + str(PowerMetrics_count) + "PowerMetrics for: " + redfish_ip)
                PowerMetrics_counter = 0

                while PowerMetrics_counter < PowerMetrics_count:
                    PowerMetrics_path = json.loads(PowerMetrics_response.text)["MetricValues"][PowerMetrics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:powermetrics", data=json.dumps(PowerMetrics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("PowerMetrics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("PowerMetrics: Cannot write PowerMetrics events for: " + redfish_ip)    
                    PowerMetrics_counter += 1

            if option == 'PowerStatistics':
                PowerStatistics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/PowerStatistics'
                PowerStatistics_response = requests.get(PowerStatistics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                PowerStatistics_count = json.loads(PowerStatistics_response.text)["MetricValues@odata.count"]
                helper.log_info("PowerStatistics: FOUND " + str(PowerStatistics_count) + "PowerStatistics for: " + redfish_ip)
                PowerStatistics_counter = 0

                while PowerStatistics_counter < PowerStatistics_count:
                    PowerStatistics_path = json.loads(PowerStatistics_response.text)["MetricValues"][PowerStatistics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:powerstatistics", data=json.dumps(PowerStatistics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("PowerStatistics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("PowerStatistics: Cannot write PowerStatistics events for: " + redfish_ip)    
                    PowerStatistics_counter += 1

            if option == 'PSUMetrics':
                PSUMetrics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/PSUMetrics'
                PSUMetrics_response = requests.get(PSUMetrics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                PSUMetrics_count = json.loads(PSUMetrics_response.text)["MetricValues@odata.count"]
                helper.log_info("PSUMetrics: FOUND " + str(PSUMetrics_count) + "PSUMetrics for: " + redfish_ip)
                PSUMetrics_counter = 0

                while PSUMetrics_counter < PSUMetrics_count:
                    PSUMetrics_path = json.loads(PSUMetrics_response.text)["MetricValues"][PSUMetrics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:psumetrics", data=json.dumps(PSUMetrics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("PSUMetrics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("PSUMetrics: Cannot write PSUMetrics events for: " + redfish_ip)    
                    PSUMetrics_counter += 1

            if option == 'Sensor':
                Sensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/Sensor'
                Sensor_response = requests.get(Sensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                Sensor_count = json.loads(Sensor_response.text)["MetricValues@odata.count"]
                helper.log_info("Sensor: FOUND " + str(Sensor_count) + "Sensor for: " + redfish_ip)
                Sensor_counter = 0

                while Sensor_counter < Sensor_count:
                    Sensor_path = json.loads(Sensor_response.text)["MetricValues"][Sensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:sensor", data=json.dumps(Sensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("Sensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("Sensor: Cannot write Sensor events for: " + redfish_ip)    
                    Sensor_counter += 1

            if option == 'StorageDiskSMARTData':
                StorageDiskSMARTData_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/StorageDiskSMARTData'
                StorageDiskSMARTData_response = requests.get(StorageDiskSMARTData_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                StorageDiskSMARTData_count = json.loads(StorageDiskSMARTData_response.text)["MetricValues@odata.count"]
                helper.log_info("StorageDiskSMARTData: FOUND " + str(StorageDiskSMARTData_count) + "StorageDiskSMARTData for: " + redfish_ip)
                StorageDiskSMARTData_counter = 0

                while StorageDiskSMARTData_counter < StorageDiskSMARTData_count:
                    StorageDiskSMARTData_path = json.loads(StorageDiskSMARTData_response.text)["MetricValues"][StorageDiskSMARTData_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:storagedisksmartdata", data=json.dumps(StorageDiskSMARTData_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("StorageDiskSMARTData: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("StorageDiskSMARTData: Cannot write StorageDiskSMARTData events for: " + redfish_ip)    
                    StorageDiskSMARTData_counter += 1

            if option == 'StorageSensor':
                StorageSensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/StorageSensor'
                StorageSensor_response = requests.get(StorageSensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                StorageSensor_count = json.loads(StorageSensor_response.text)["MetricValues@odata.count"]
                helper.log_info("StorageSensor: FOUND " + str(StorageSensor_count) + "StorageSensor for: " + redfish_ip)
                StorageSensor_counter = 0

                while StorageSensor_counter < StorageSensor_count:
                    StorageSensor_path = json.loads(StorageSensor_response.text)["MetricValues"][StorageSensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:storagesensor", data=json.dumps(StorageSensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("StorageSensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("StorageSensor: Cannot write StorageSensor events for: " + redfish_ip)    
                    StorageSensor_counter += 1

            if option == 'ThermalMetrics':
                ThermalMetrics_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/ThermalMetrics'
                ThermalMetrics_response = requests.get(ThermalMetrics_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                ThermalMetrics_count = json.loads(ThermalMetrics_response.text)["MetricValues@odata.count"]
                helper.log_info("ThermalMetrics: FOUND " + str(ThermalMetrics_count) + "ThermalMetrics for: " + redfish_ip)
                ThermalMetrics_counter = 0

                while ThermalMetrics_counter < ThermalMetrics_count:
                    ThermalMetrics_path = json.loads(ThermalMetrics_response.text)["MetricValues"][ThermalMetrics_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:thermalmetrics", data=json.dumps(ThermalMetrics_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("ThermalMetrics: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("ThermalMetrics: Cannot write ThermalMetrics events for: " + redfish_ip)    
                    ThermalMetrics_counter += 1

            if option == 'ThermalSensor':
                ThermalSensor_url = 'https://' + redfish_ip + '/redfish/v1/TelemetryService/MetricReports/ThermalSensor'
                ThermalSensor_response = requests.get(ThermalSensor_url, auth=HTTPBasicAuth(redfish_user, redfish_password),  verify=False)
                ThermalSensor_count = json.loads(ThermalSensor_response.text)["MetricValues@odata.count"]
                helper.log_info("ThermalSensor: FOUND " + str(ThermalSensor_count) + "ThermalSensor for: " + redfish_ip)
                ThermalSensor_counter = 0

                while ThermalSensor_counter < ThermalSensor_count:
                    ThermalSensor_path = json.loads(ThermalSensor_response.text)["MetricValues"][ThermalSensor_counter]
                    try:
                        event = helper.new_event(host=redfish_ip, source=helper.get_input_type(), index=helper.get_output_index(), sourcetype="redfish:telemetry:thermalsensor", data=json.dumps(ThermalSensor_path), done=True, unbroken=False)
                        ew.write_event(event)
                        helper.log_info("ThermalSensor: Overview event data created for: " + redfish_ip)
                    except:
                        helper.log_error("ThermalSensor: Cannot write ThermalSensor events for: " + redfish_ip)    
                    ThermalSensor_counter += 1
            
            helper.log_info("MetricsReports: Finished MetricReports collection for: " + redfish_ip)
    
    except:
        helper.log_error("MetricsReports: URL not found for: " + redfish_ip)
    
    # Finish up
    helper.log_info("FINISH: Ending collection for: " + redfish_ip)
    end_time = round(time.time()-start,2)
    helper.log_info("FINISH: Collection took: " + str(end_time) + " secs to collect data for: " + redfish_ip)