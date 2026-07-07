import logging
import socket
from subprocess import call
import sys
import time
from modular_alert_example_app.modular_alert import ModularAlert, Field, IntegerField, FieldValidationException

class NagiosAlerts(ModularAlert):
    """
    This alert just makes a log message (its an example).
    """
    
    def __init__(self, **kwargs):
        params = [
            Field("alert_destination"),
            Field("description"),
            Field("escape_backslashes"),
            Field("gearman_key", empty_allowed=True),
            Field("gearman_path", empty_allowed=True),
            Field("gearman_port", empty_allowed=True),
            Field("hostname"),
            IntegerField("livestatus_port", empty_allowed=True),
            Field("nagios_hostname"),
            IntegerField("sendresults"),
            Field("servicename"),
            IntegerField("status"),
        ]
        
        super(NagiosAlerts, self).__init__(params, logger_name="nagios_alerts", log_to_file=True, log_level=logging.INFO )

    def netcat(self, nagios_hostname, livestatus_port, content):
        """
        https://stackoverflow.com/questions/1908878/netcat-implementation-in-python/1909355#1909355
        :param nagios_hostname: Hostname of nagios instance
        :param livestatus_port: Port of livestatus listener
        :param content: Content to send to livestatus.
            Format: "COMMAND [_timestamp_] PROCESS_SERVICE_CHECK_RESULT;_hostname_;_servicename;__status_;_description"
        :return: null
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((nagios_hostname, livestatus_port))
        s.sendall(content)
        s.sendall("\n")
        s.shutdown(socket.SHUT_WR)
        while 1:
            data = s.recv(1024)
            if data == "":
                break
            self.logger.info("Received:", repr(data))
        s.close()
        self.logger.info("Connection closed.")

    def send_gearman(self, gearman_path, nagios_hostname, gearman_port, hostname, servicename, status, description, gearman_key):
        """
        :param gearman_path: Full path to sned_gearman executable
        :param nagios_hostname: Hostname of nagios instance
        :param hostname: Hostname for nagios alert
        :param servicename: Servicename for nagios alert
        :param status: Status for nagios alert
        :param description: Message for nagios alert
        :param gearman_key: Encryption key for gearman
        :return: null
        """
        # TODO: If gearman_key is empty, set --encryption=no
        command = '%s --server=%s:%s --host=%s --service="%s" --returncode=%s --message="%s" --encryption=yes --key="%s"' \
               % (gearman_path, nagios_hostname, gearman_port, hostname, servicename, status, description, gearman_key)
        log_command = command.replace(gearman_key, "REDACTED")
        self.logger.info(log_command)
        call(command, shell=True)

    def run(self, cleaned_params, payload):
        """
        :param cleaned_params: Dict of params passed to script
        :param payload: Results of search
        :return:
        """
        # Required parameters
        alert_destination = cleaned_params.get('alert_destination')
        description = cleaned_params.get('description')
        escape_backslashes = cleaned_params.get('escape_backslashes'),
        hostname = cleaned_params.get('hostname')
        nagios_hostname = cleaned_params.get('nagios_hostname')
        sendresults = cleaned_params.get('sendresults')
        servicename = cleaned_params.get('servicename')
        status = cleaned_params.get('status')

        # Append search results if we're supposed to
        if (sendresults == 1):
            results = str(payload['result'])
            results = results.replace(',', ',\n')
            description = '%s\n\n%s' % (description, results)

        # Replace linebreaks with a literal "\\n" to make nagios happy
        if (escape_backslashes == 1):
            description = description.replace('\r', '')
            description = description.replace('\n', '\\n')

        # Send alert to nagios and log stuff
        if (alert_destination == "livestatus"):
            livestatus_port = cleaned_params.get('livestatus_port')
            content = "COMMAND [%i] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%s;%s" \
                      % (time.time(), hostname, servicename, status, description)
            self.logger.info("Sending to livestatus %s:%s", nagios_hostname, livestatus_port)
            self.logger.info("Content: %s" % content)
            self.netcat(nagios_hostname, livestatus_port, content)
            self.logger.info("Sent to livestatus")
        elif (alert_destination == "gearman"):
            gearman_key = cleaned_params.get('gearman_key')
            gearman_path = cleaned_params.get('gearman_path')
            gearman_port = cleaned_params.get('gearman_port')
            self.logger.info("Sending to gearman")
            self.send_gearman(gearman_path, nagios_hostname, gearman_port, hostname, servicename, status, description, gearman_key)
            self.logger.info("Sent to gearman")

"""
If the script is being called directly from the command-line, then this is likely being executed by Splunk.
"""
if __name__ == '__main__':
    
    # Make sure this is a call to execute
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        
        try:
            modular_alert = NagiosAlerts()
            modular_alert.execute()
            sys.exit(0)
        except Exception as e:
            # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
            print >> sys.stderr, "Unhandled exception was caught, this may be due to a defect in the script:" + str(e)
            raise
        
    else:
        print >> sys.stderr, "Unsupported execution mode (expected --execute flag)"
        sys.exit(1)