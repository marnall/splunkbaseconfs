#!/usr/bin/env python3

import os
import sys
import time
import json
import logging
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ta_securitybridge", "aob_py3"))

import splunk
import splunk.entity as en
from splunk.appserver.mrsparkle.lib import util
from solnlib import log
from solnlib.modular_input import ModularInput, Argument, InputDefinition


class SAPPushMonitor(ModularInput):
    """
    Monitoring and alerting for SAP Push API integration
    """

    def __init__(self):
        super(SAPPushMonitor, self).__init__("sap_push_monitor", "SAP Push API Monitor")
        self.logger = None
        self.last_health_check = None
        self.error_count = 0
        self.alert_threshold = 5

    def get_args(self):
        """Define input arguments"""
        return [
            Argument(
                "check_interval",
                title="Health Check Interval (seconds)",
                description="How often to check webhook health",
                data_type=Argument.data_type_number,
                default=60
            ),
            Argument(
                "alert_threshold",
                title="Error Alert Threshold",
                description="Number of consecutive errors before alerting",
                data_type=Argument.data_type_number,
                default=5
            ),
            Argument(
                "monitor_log_file",
                title="Monitor Webhook Log File",
                description="Path to webhook log file for monitoring",
                data_type=Argument.data_type_string,
                default="/opt/splunk/var/log/splunk/sap_push_webhook.log"
            )
        ]

    def stream_events(self, inputs, event_writer):
        """Main monitoring loop"""
        self.logger = log.Logs().get_logger('sap_push_monitor')
        
        for input_name, input_item in inputs.inputs.items():
            check_interval = int(input_item.get('check_interval', 60))
            self.alert_threshold = int(input_item.get('alert_threshold', 5))
            log_file = input_item.get('monitor_log_file')

            self.logger.info(f"Starting SAP Push API monitoring with interval {check_interval}s")

            while True:
                try:
                    # Perform health checks
                    health_status = self.check_webhook_health()
                    log_health = self.check_log_file_health(log_file) if log_file else True
                    
                    # Generate monitoring events
                    self.write_health_event(event_writer, health_status, log_health)
                    
                    # Check for errors and alerts
                    if not health_status or not log_health:
                        self.error_count += 1
                        if self.error_count >= self.alert_threshold:
                            self.write_alert_event(event_writer, health_status, log_health)
                            self.error_count = 0  # Reset after alerting
                    else:
                        self.error_count = 0

                    time.sleep(check_interval)

                except Exception as e:
                    self.logger.error(f"Monitor error: {str(e)}")
                    self.write_error_event(event_writer, str(e))
                    time.sleep(check_interval)

    def check_webhook_health(self):
        """Check webhook endpoint health"""
        try:
            import urllib3
            http = urllib3.PoolManager()
            
            # Try to reach the health endpoint
            response = http.request(
                'GET',
                'http://localhost:8000/en-US/app/TA-SecurityBridge/sap_push_webhook/health',
                timeout=10
            )
            
            if response.status == 200:
                try:
                    data = json.loads(response.data)
                    return data.get('status') == 'healthy'
                except json.JSONDecodeError:
                    return False
            return False
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    def check_log_file_health(self, log_file):
        """Check webhook log file for recent activity and errors"""
        try:
            if not os.path.exists(log_file):
                return False

            # Check if log file has been modified recently (within last 5 minutes)
            stat = os.stat(log_file)
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            if datetime.now() - last_modified > timedelta(minutes=5):
                return True  # No recent activity is okay

            # Check for recent errors in log file
            with open(log_file, 'r') as f:
                # Read last 50 lines
                lines = f.readlines()[-50:]
                
            recent_errors = 0
            for line in lines:
                if '[ERROR]' in line and self.is_recent_log_entry(line):
                    recent_errors += 1

            # Alert if more than 3 errors in recent logs
            return recent_errors < 3

        except Exception as e:
            self.logger.error(f"Log file health check failed: {str(e)}")
            return False

    def is_recent_log_entry(self, log_line, minutes=5):
        """Check if log entry is from recent time period"""
        try:
            # Extract timestamp from log line (format: YYYY-MM-DD HH:MM:SS)
            parts = log_line.split(' ')
            if len(parts) >= 2:
                timestamp_str = f"{parts[0]} {parts[1]}"
                log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                return datetime.now() - log_time < timedelta(minutes=minutes)
            return False
        except Exception:
            return False

    def write_health_event(self, event_writer, webhook_health, log_health):
        """Write health status event"""
        event_data = {
            "timestamp": int(time.time()),
            "event_type": "sap_push_health_check",
            "webhook_status": "healthy" if webhook_health else "unhealthy",
            "log_status": "healthy" if log_health else "unhealthy",
            "overall_status": "healthy" if webhook_health and log_health else "unhealthy",
            "error_count": self.error_count,
            "source": "sap_push_monitor"
        }

        event = self.create_event_object(
            data=json.dumps(event_data),
            sourcetype="sap:push:monitor",
            source="sap_push_monitor"
        )
        event_writer.write_event(event)

    def write_alert_event(self, event_writer, webhook_health, log_health):
        """Write alert event when thresholds are exceeded"""
        event_data = {
            "timestamp": int(time.time()),
            "event_type": "sap_push_alert",
            "alert_level": "critical",
            "alert_message": f"SAP Push API unhealthy for {self.error_count} consecutive checks",
            "webhook_status": "healthy" if webhook_health else "unhealthy",
            "log_status": "healthy" if log_health else "unhealthy",
            "consecutive_errors": self.error_count,
            "threshold": self.alert_threshold,
            "source": "sap_push_monitor"
        }

        event = self.create_event_object(
            data=json.dumps(event_data),
            sourcetype="sap:push:alert",
            source="sap_push_monitor"
        )
        event_writer.write_event(event)
        
        self.logger.error(f"SAP Push API Alert: {event_data['alert_message']}")

    def write_error_event(self, event_writer, error_message):
        """Write error event"""
        event_data = {
            "timestamp": int(time.time()),
            "event_type": "sap_push_monitor_error",
            "error_message": error_message,
            "source": "sap_push_monitor"
        }

        event = self.create_event_object(
            data=json.dumps(event_data),
            sourcetype="sap:push:monitor:error",
            source="sap_push_monitor"
        )
        event_writer.write_event(event)

    def create_event_object(self, data, sourcetype, source):
        """Create Splunk event object"""
        event = {
            "time": time.time(),
            "host": self.get_local_hostname(),
            "source": source,
            "sourcetype": sourcetype,
            "data": data
        }
        return event

    def get_local_hostname(self):
        """Get local hostname"""
        import socket
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"


if __name__ == "__main__":
    exit_code = SAPPushMonitor().run(sys.argv)
    sys.exit(exit_code)