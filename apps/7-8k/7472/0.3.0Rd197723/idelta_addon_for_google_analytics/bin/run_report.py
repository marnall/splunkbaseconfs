ƒimport import_declare_test
import json
import logging
import sys
import traceback
import os
import time
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "idelta_addon_for_google_analytics"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_propertyid(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-idelta_addon_for_google_analytics_account",
    )
    account_conf_file = cfm.get_conf("idelta_addon_for_google_analytics_account")
    return account_conf_file.get(account_name).get("google_analytics_property")


def get_data_from_api(logger: logging.Logger, property_id: str, metric_names:str, dimension_names:str,start_date:str,end_date:str):

    #property_id=api_key
    startDate=start_date
    endDate=end_date
    dimensions_input_list=dimension_names
    metrics_input_list=metric_names

    #Set the path to the credentials JSON file
    os.environ['GOOGLE_APPLICATION_CREDENTIALS']=os.getenv('SPLUNK_HOME')+"/etc/apps/"+ADDON_NAME+"/bin/google_analytics_credentials.json"
    logger.debug("Current directory: "+os.getcwd())
    logger.debug("Splunk Home: "+ os.getenv('SPLUNK_HOME'))
    #commented out so that credentials / api key never logged
    #logger.debug("Using Google Analytics Private Key: "+os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
    logger.info("Collecting data for Google Analytics propertyID: "+property_id)
   
    #Build list of Dimensions for API call from the dimensions input
    dimensions_list=dimensions_input_list.split(",")
    requestDimList=[]
    for dimListEntry in dimensions_list:
        d = Dimension(name=dimListEntry.strip())
        requestDimList.append(d)
    logger.debug("Dimensions List: "+str(requestDimList))
    
    #Build list of Metrics for API call from the metrics input
    metrics_list=metrics_input_list.split(",")
    requestMetricList=[]
    for metricListEntry in metrics_list:
        m = Metric(name=metricListEntry.strip())
        requestMetricList.append(m)
    logger.debug("Metrics List: "+str(requestMetricList))


    # Using a default constructor instructs the client to use the credentials
    # specified in GOOGLE_APPLICATION_CREDENTIALS environment variable.
    client = BetaAnalyticsDataClient()
    logger.info('Created Google Analytics API client')

    #Construct the API request using objects created above
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=requestDimList,
        metrics=requestMetricList,
        date_ranges=[DateRange(start_date=startDate, end_date=endDate)],
    )
    logger.info('Making API call')

    beforeAPICallTime=time.time()
    tstamp_str=time.strftime("%Y-%m-%dT%H:%M:%S%z",time.gmtime())
    response = client.run_report(request)
    afterAPICallTime=time.time()
    apiCallTime=afterAPICallTime - beforeAPICallTime
    logger.info('Google Analytics API responded in (secs): ' + "google_analytics_api_response_time_secs="+str(apiCallTime))
    
    #Create dimensions name lists for event from response.dimension_headers
    #Handles situation where there could be more than one dimensiom
    dimensionsNames = []
    for dimensionHeader in response.dimension_headers:
        logger.debug("Appending dimension to list for event: "+str(dimensionHeader))
        dimensionsNames.append(dimensionHeader.name)

    #Create metric name lists for event from response.metric_headers
    #Handles situation where there could be more than one metric   
    metricNames = []
    for metricHeader in response.metric_headers:
        logger.debug("Appending metric to list for event: "+str(metricHeader))
        metricNames.append(metricHeader.name)
    logger.debug('Dimensions list: '+str(dimensionsNames))
    logger.debug('Metrics list: '+str(metricNames))
    
    #Create an event per row of response and append it to a events list:
    events=[]
    event=""
    for row in response.rows:
        #set the timestamp
        event=tstamp_str+" start_date="+startDate+" end_date="+endDate
        #Output header values:
        i=0
        for dimension_value in row.dimension_values:
            event=event+" "+dimensionsNames[i]+"=\""+dimension_value.value+"\""
            i=i+1
        j=0
        for metric_value in row.metric_values:
            event=event+" "+metricNames[j]+"=\""+metric_value.value+"\""
            j=j+1
        logger.debug("Processed row data: "+str(row))
        logger.debug("Created event from row data: "+str(event))
        events.append(event)
        event=""
    
    
    return events


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("run_report")
        scheme.description = "run_report input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "metric_names", title="Metric Name(s)",description="Google Analytics Metric Name(s)",required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "dimension_names", title="Dimension Name(s)",description="Google Analytics Dimension Name(s)",required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "start_date", title="Start Date",description="Start Date in Google Analytics API format",required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "end_date", title="End Date",description="End Date in Google Analytics API format",required_on_create=True
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        # inputs.inputs is a Python dictionary object like:
        # {
        #   "run_report://<input_name>": {
        #     "account": "<account_name>",
        #     "disabled": "0",
        #     "host": "$decideOnStartup",
        #     "index": "<index_name>",
        #     "interval": "<interval_value>",
        #     "python.version": "python3",
        #   },
        # }
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = logger_for_input(normalized_input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name=f"{ADDON_NAME}_settings",
                )
                logger.setLevel(log_level)
                log.modular_input_start(logger, normalized_input_name)
                #Get fields from account and input definition:
                google_property_id = get_account_propertyid(session_key, input_item.get("account"))
                metric_names = input_item.get("metric_names")
                logger.info("Retrieved metric names from input definition: "+metric_names)
                dimension_names = input_item.get("dimension_names")
                logger.info("Retrieved dimension names from input definition: "+dimension_names)
                start_date = input_item.get("start_date")
                end_date = input_item.get("end_date")
                #Call the API with the input paramters passed in
                data = get_data_from_api(logger, google_property_id,metric_names,dimension_names,start_date,end_date)
                sourcetype = "google:analytics:metrics"
                for line in data:
                    event_writer.write_event(
                        smi.Event(
                            #data=json.dumps(line, ensure_ascii=False, default=str),
                            data=line,
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                        )
                    )
                log.events_ingested(
                    logger, normalized_input_name, sourcetype, len(data)
                )
                log.modular_input_end(logger, normalized_input_name)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"run_report: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
