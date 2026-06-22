# Dark Web Scan by Bechtle App (for Splunk)

## Description
See if your company's data was leaked to the dark web with this app for the Dark Web Scan by [Bechtle](https://bechtle.com/?utm_source=darkwebscan_splunk). 

Credentials of your employees, customers, suppliers and service technicians get stolen by cybercriminals and are sold on the dark web. Get notified about any new offers or leaks regarding your company using this app. 

- We permanently look out for new forums, marketplaces or chat groups and get access.
- Then we crawl data from these sources on the digital underground and save it to our database.
- You get notified if there's something about your company being sold.

Using the custom Splunk search commands, you can even customize your automations. For example, you could set up your own automation to send an email to users with leaked credentials or reset their passwords automatically. (The automation requires additional setup and is not part of the app.)

Additionally, the Dark Web Scan by Bechtle also allows you to search for common misconfigurations or other risks that could lead to security incidents in the future, e.g. email security settings, the security of your website against common cyberattacks or OSINT info like publicly discoverable email addresses or subdomains.

This app offers the following search commands:
```
| darkwebscanfindcompromised companyId=123
```
```
| darkwebscanemailsecurity companyId=123
```
```
| darkwebscanwaf companyId=123
```
```
| darkwebscanosint companyId=123
```
See the dashboard for usage examples.

---


## Support
For support, please open an issue on [GitHub](https://github.com/darkwebscan/darkwebscan-for-splunk) or see [www.darkwebscan.app/contact](https://darkwebscan.app/contact).


---


## System requirements
- [Splunk](https://splunk.com) for Enterprise installed or Splunk Cloud in use
- Active subscription to the Dark Web Scan by Bechtle at [www.darkwebscan.app](https://darkwebscan.app) (Active subscription required. Does not work with one-time scans!)
- The Splunk instance must be able to reach [https://api.darkwebscan.app](https://api.darkwebscan.app) (HTTPS/Port 443 usage only, no HTTP connection needed).
- If the connection does not work, read the "Troubleshooting" section below.


---


## Installation
- Log in to your Splunk instance
- In the menu at the top, Click 
```
Apps > Manage Apps 
```
(or alternatively, open [http://127.0.0.1:8000/en-US/manager/search/apps/local](http://127.0.0.1:8000/en-US/manager/search/apps/local), assuming your Splunk instance is located at 127.0.0.1:8000)
- Click "Install app from file" and upload the downloaded .tar.gz file. 
- Then, check "Upgrade app. Checking this will overwrite the app if it already exists".
- Click "Upload"
- Alternatively, click on "Browse More Apps", search for "Dark Web Scan by Bechtle App" and click install on the search result matching this query.


---


## Configuration
1. Open the app
2. Open the setup page. If it's not showing automatically after opening the app for the first time, use the "Setup" tab in the menu of the app.
3. Insert your API key (and if required: additional headers as key:value pairs, one request header per line) into the appropriate input fields.
4. Click "Save".
5. Open the "Overview" dashboard of the app "Dark Web Scan by Bechtle App". If you don't see any data loading there, repeat steps 1-5 and double-check that you've copied your API key (and optionally, additional request headers) exactly, without spaces. If you don't see data, please contact the support team of this app.


---


## License usage
This app uses "splunklib" which is licensed under the Apache License, Version 2.0. Please see files in the folder "splunklib" for additional licensing information.


--- 


## Troubleshooting
- Please make sure that nothing is blocking connections to https://api.darkwebscan.app (HTTPS/Port 443)
- If you are using SSL inspection/Deep Packet Inspection on your Splunk instance, you might need to disable it for https://api.darkwebscan.app
- Verify that your subscription of the Dark Web Scan by Bechtle at www.darkwebscan.app has not expired.
- Please double-check your API key (and optionally, additional request headers) and re-enter them in the "Setup" page of the app again.
- If you still don't see any data loading there, please contact support as detailed above.


---


## How to run the app
- Install the app to your existing Splunk for Enterprise instance or in Splunk Cloud as described in "Installation" above
- Open the "Dark Web Scan by Bechtle App" in Splunk.
- Configure settings as described in "Configuration" above.
- Open the "Overview" tab in the app.
- There, your data will show up.
- For a more detailed view, click on "Learn more" or use the magnifying icon in the dashboard panels.
