import sys

try:
    from VaronisSearchBase import VaronisSearchBase
except ImportError:
    from bin.VaronisSearchBase import VaronisSearchBase
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import logging
logger = logging.getLogger('splunk.VaronisSearchUserAccessAudit')
logger.setLevel(logging.DEBUG)

import datetime
datetime_format = '%Y-%m-%d %H:%M:%S'
date_format = '%Y-%m-%d'

COLUMNS = 'Time,File_Server_Domain,Event_Status,Event_Type,Event_Description,Operation_By'

@Configuration()
class VaronisSearchUserAccessAudit(VaronisSearchBase):
    columns = Option(
        doc='Comma-separated list of requested columns',
        require=False,
        default=COLUMNS
    )

    start_date = Option(
        doc='Optional end_date parameter with default value as a day before now',
        require=False,
        default=(datetime.datetime.now() - datetime.timedelta(days=1)).strftime(datetime_format)
    )

    end_date = Option(
        doc='Optional start_date parameter with default value as now',
        require=False,
        default=datetime.datetime.now().strftime(datetime_format)
    )

    sam_account_name = Option(
        doc='Username / SAM account / Service account',
        require=False
    )
    
    def get_query(self):

        try:
            #if Splunk time picker was used, convert provided epoch string to integer and use it
            self.start_date = datetime.datetime.fromtimestamp(int(self.search_results_info.search_et)).strftime(datetime_format)
            self.end_date = datetime.datetime.fromtimestamp(int(self.search_results_info.search_lt)).strftime(datetime_format)
        except Exception as e: logger.debug(e)
            
            #if "all time" is used no search_et is defined, or if nothing was provided, default to 24h to follow DataSet default
            
            
        # Use the time range values in your Python script
        # For example, you can print them:
        logger.debug("Earliest time:")
        logger.debug(self.start_date)
        logger.debug("Latest time:")
        logger.debug(self.end_date)
        
        logger.debug("building query: ")
        
        query = "SELECT " + self.columns + " from User_Access_Log where "
        query += "Show_data_from = 'Audit_events'"
        query += " and (time between '" + self.start_date + "' and '" + self.end_date + "')"
        if self.sam_account_name:
            query += " and SamAccountName_acting_object = '" + self.sam_account_name + "'"  
        query += " order by time desc"
        return query

if __name__ == "__main__":
    dispatch(VaronisSearchUserAccessAudit, sys.argv, sys.stdin, sys.stdout, __name__)
