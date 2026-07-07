#!/usr/bin/env python3

import sys
import os
import json
import hashlib
import hmac
import time
import traceback
from urllib.parse import parse_qs
import splunk.rest as rest
import splunk.entity as en

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ta_securitybridge", "aob_py3"))

import splunk
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.util
import splunk.secure
import cherrypy


class SAPPushWebhookHandler(controllers.BaseController):
    """
    Webhook handler for receiving SAP SecurityBridge push notifications
    """

    def __init__(self):
        controllers.BaseController.__init__(self)
        self.logger = splunk.util.make_splunkhome_path(["var", "log", "splunk", "sap_push_webhook.log"])

    def log_message(self, level, message):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} [{level}] {message}\n"
        try:
            with open(self.logger, "a") as f:
                f.write(log_entry)
        except Exception:
            pass

    def validate_webhook_signature(self, payload, signature, secret):
        """Validate webhook signature using HMAC-SHA256"""
        if not signature or not secret:
            return False
        
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            received_signature = signature.replace('sha256=', '') if signature.startswith('sha256=') else signature
            return hmac.compare_digest(expected_signature, received_signature)
        except Exception as e:
            self.log_message("ERROR", f"Signature validation error: {str(e)}")
            return False

    def get_webhook_config(self):
        """Get webhook configuration from Splunk settings"""
        try:
            session_key = cherrypy.session.get('sessionKey')
            if not session_key:
                return None

            # Get configuration from the TA settings
            config_endpoint = f"/servicesNS/nobody/TA-SecurityBridge/configs/conf-ta_securitybridge_settings/webhook_config"
            response, content = rest.simpleRequest(
                config_endpoint,
                sessionKey=session_key,
                method='GET'
            )
            
            if response.status == 200:
                config_data = json.loads(content)
                if 'entry' in config_data and config_data['entry']:
                    return config_data['entry'][0]['content']
            
            return {}
        except Exception as e:
            self.log_message("ERROR", f"Failed to get webhook config: {str(e)}")
            return {}

    @expose_page(must_login=False, methods=['POST'])
    @route('/sap_push_webhook')
    def webhook_receiver(self, **kwargs):
        """Main webhook receiver endpoint"""
        try:
            # Log incoming request
            self.log_message("INFO", f"Received webhook request from {cherrypy.request.remote.ip}")
            
            # Get request body
            content_length = int(cherrypy.request.headers.get('Content-Length', 0))
            if content_length == 0:
                self.log_message("ERROR", "Empty request body")
                cherrypy.response.status = 400
                return json.dumps({"error": "Empty request body"})

            raw_body = cherrypy.request.body.read(content_length)
            payload = raw_body.decode('utf-8')
            
            # Get webhook configuration
            config = self.get_webhook_config()
            
            # Validate signature if configured
            signature = cherrypy.request.headers.get('X-SAP-Signature') or cherrypy.request.headers.get('X-Hub-Signature-256')
            if config.get('enable_signature_validation', False):
                webhook_secret = config.get('webhook_secret')
                if not self.validate_webhook_signature(payload, signature, webhook_secret):
                    self.log_message("ERROR", "Invalid webhook signature")
                    cherrypy.response.status = 401
                    return json.dumps({"error": "Invalid signature"})

            # Validate content type
            content_type = cherrypy.request.headers.get('Content-Type', '')
            if not content_type.startswith('application/json'):
                self.log_message("ERROR", f"Invalid content type: {content_type}")
                cherrypy.response.status = 400
                return json.dumps({"error": "Content-Type must be application/json"})

            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                self.log_message("ERROR", f"Invalid JSON payload: {str(e)}")
                cherrypy.response.status = 400
                return json.dumps({"error": "Invalid JSON"})

            # Process the data
            processed_count = self.process_sap_data(data)
            
            # Return success response
            response = {
                "status": "success",
                "processed_events": processed_count,
                "timestamp": int(time.time())
            }
            
            self.log_message("INFO", f"Successfully processed {processed_count} events")
            cherrypy.response.status = 200
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(response)

        except Exception as e:
            error_msg = f"Webhook processing error: {str(e)}"
            self.log_message("ERROR", f"{error_msg}\n{traceback.format_exc()}")
            cherrypy.response.status = 500
            return json.dumps({"error": "Internal server error"})

    def process_sap_data(self, data):
        """Process SAP data and forward to HEC"""
        try:
            # Handle both single event and batch formats
            events = []
            
            if isinstance(data, dict):
                if 'events' in data:
                    # Batch format: {"events": [...]}
                    events = data['events']
                elif 'results' in data:
                    # OData format: {"results": [...]}
                    events = data['results']
                else:
                    # Single event
                    events = [data]
            elif isinstance(data, list):
                # Direct array
                events = data
            else:
                self.log_message("ERROR", f"Unexpected data format: {type(data)}")
                return 0

            # Forward each event to HEC
            processed_count = 0
            for event in events:
                if self.forward_to_hec(event):
                    processed_count += 1
                    
            return processed_count

        except Exception as e:
            self.log_message("ERROR", f"Error processing SAP data: {str(e)}")
            return 0

    def forward_to_hec(self, event_data):
        """Forward individual event to Splunk HEC"""
        try:
            # Get HEC configuration
            config = self.get_webhook_config()
            hec_token = config.get('hec_token')
            hec_url = config.get('hec_url', 'https://localhost:8088/services/collector')
            
            if not hec_token:
                self.log_message("ERROR", "HEC token not configured")
                return False

            # Prepare HEC event format
            hec_event = {
                "time": event_data.get('timestamp') or int(time.time()),
                "source": "sap:securitybridge:push",
                "sourcetype": "sapsb_push_json",
                "index": config.get('target_index', 'main'),
                "event": event_data
            }

            # Send to HEC (simplified - in production, use proper HTTP client)
            import urllib3
            http = urllib3.PoolManager()
            
            headers = {
                'Authorization': f'Splunk {hec_token}',
                'Content-Type': 'application/json'
            }
            
            response = http.request(
                'POST',
                hec_url,
                body=json.dumps(hec_event),
                headers=headers
            )
            
            if response.status == 200:
                return True
            else:
                self.log_message("ERROR", f"HEC request failed: {response.status} - {response.data}")
                return False

        except Exception as e:
            self.log_message("ERROR", f"Error forwarding to HEC: {str(e)}")
            return False

    @expose_page(must_login=False, methods=['GET'])
    @route('/sap_push_webhook/health')
    def health_check(self, **kwargs):
        """Health check endpoint"""
        response = {
            "status": "healthy",
            "timestamp": int(time.time()),
            "version": "1.0.0"
        }
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(response)