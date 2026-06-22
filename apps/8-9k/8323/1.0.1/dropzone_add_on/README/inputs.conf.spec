[dropzone_health_check://<name>]
api_key = Optional API key for authentication (e.g., Api-Key YOUR_KEY)
base_url = The URL of your Dropzone AI instance (e.g., https://app.dropzone.ai) (Default: https://127.0.0.1)
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 30)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[dropzone_investigations://<name>]
api_key = API key for authentication (required). Format: Api-Key YOUR_KEY
base_url = The URL of your Dropzone AI instance (e.g., https://app.dropzone.ai) (Default: https://127.0.0.1)
index = (Default: default)
interval = Time interval of the data input, in seconds. This determines how often to poll for new completed investigations. (Default: 300)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
