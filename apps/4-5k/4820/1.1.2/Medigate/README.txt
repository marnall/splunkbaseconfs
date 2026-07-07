Medigate App and Add-on

Created by: Medigate - support@medigate.io

Description:  This app was created to import Medigate data into Splunk.

Installation:

1. Create a Medigate Index.

2. Verify UF (Universal Forwarder) receive data is enabled on port 9997.

3. Install Baboon Bones - REST API Modular Input baboonbones.com and activate.

4. Setup a new REST API data input using the following attributes:
   - REST API Input Name: Medigate All Assets CSV
   - Endpoint URL: https://<sensor_ip>:3210/assets ("sensor_ip" supplied by Medigate)
   - Authentication Type: basic
   - Authentication User: splunk
   - Authentication Password: <password> (supplied by Medigate)
   - Polling Interval: 600
   - Set sourcetype: Manual
   - Source type: medigate_assets_csv
   - Index: medigate

5. Install Medigate App.

6. Set the "medigate" index' app to Medigate.
