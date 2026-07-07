import splunk.admin as admin
import sc_rest 

class AlertsOverlayHandler(sc_rest.BaseResource):
    required_args = ['threshold_type']
    optional_args = ['business_impact', 'description', 'escalation', 'remediation', 'threshold_min', 'threshold_max', 'threshold_unit']
    endpoint = 'admin/conf-alert_overlay'

if __name__ == "__main__":
    admin.init(sc_rest.ResourceHandler(AlertsOverlayHandler), admin.CONTEXT_APP_ONLY)
