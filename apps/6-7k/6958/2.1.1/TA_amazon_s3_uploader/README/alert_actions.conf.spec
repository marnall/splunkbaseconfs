[amazon_s3_upload]
param.bucket_name = <string> Bucket name. It's a required parameter.
param.object_key = <string> Object key. It's a required parameter.
param.account = <list> Account. It's a required parameter. It's default value is Boto3.
param.role = <list> Role.
param.aws_region = <string> Region.
param.utc = <bool> Use UTC.
param.upload_empty = <bool> Allow empty results.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
