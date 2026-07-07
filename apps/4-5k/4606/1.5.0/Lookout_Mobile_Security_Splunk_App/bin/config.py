"""Initial global configuration for Splunk App"""
import os.path

app = "Lookout_Mobile_Security_Splunk_App"
app_root_path = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", app)
app_log_path = os.path.join(os.environ["SPLUNK_HOME"], "var", "log", "splunk")
api_url = "https://api.lookout.com"
kvstore_location = (
    "https://localhost:8089/servicesNS/nobody/{}"
    "/storage/collections/data/lookout_mra_configuration_data/"
).format(app)
random_id = "6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51"
