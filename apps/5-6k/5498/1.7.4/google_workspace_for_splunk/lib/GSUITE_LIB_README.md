# GSUITE Libraries

There are so many things required for this to work. 

These libraries were installed from a linux VM, using the pip command below.
The requirements file was generated for the correct version of Python (3.9) with Splunk 9.4.
The commands are run from `$SPLUNK_HOME/etc/apps/google_workspace_for_splunk/lib`

    pip3 install pip-tools
    pip-tools compile ./requirements.in

If your operating system is different from x64 linux, you may need to run this command from this folder.

    /opt/splunk/bin/splunk cmd python3 -m pip install --upgrade -t . -r requirements.txt

This command was run on a linux vm with Splunk 9.4.0.


## Reduction of size

Various items of the python packages were removed to reduce size of the overall package.

### lib/googleapiclient/discovery_cache/documents

These files were removed due to non-use within the Google workspace app.
These were ~30Mb total.

* dialogflow.v3.json
* dialogflow.v3beta1.json
* dfareporting.v4.json
* displayvideo.v1.json
* displayvideo.v2.json
* dialogflow.v2.json
* dialogflow.v2beta1.json
* compute.v1.json
* compute.beta.json
* compute.alpha.json
* contentwarehouse.v1.json
* dfareporting.v3.3.json
* dfareporting.v3.5.json
* dfareporting.v3.4.json
* apigee.v1.json
* healthcare.v1beta1.json
* retail.v2beta.json
* retail.v2alpha.json
* vision.v1.json
* healthcare.v1.json
* container.v1beta1.json
* retail.v2.json
* dataplex.v1.json
* vision.v1p1beta1.json
* vision.v1p2beta1.json
* youtube.v3.json  
* youtubeAnalytics.v1.json  
* youtubeAnalytics.v2.json  
* youtubereporting.v1.json


    cd googleapiclient/discovery_cache/documents
    rm -f dialogflow.*.json dfareporting.*.json displayvideo.*.json compute.*.json contentwarehouse.*.json apigee.*.json healthcare.*.json retail.*.json vision.*.json container.*.json dataplex.*.json vision.*.json  youtube*.json 