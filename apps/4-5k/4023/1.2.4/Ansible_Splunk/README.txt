## Ansible Monitoring & Diagnostics

This Splunk application is specifically design to work with the Ansible Splunk Callback maintained by Converging Data Pty Ltd. This Splunk application provides guided navigation for the monitoring and diagnostics of Ansible plays.

---

## Getting Started Overview

Below is an overview of how to get this Splunk application and the Ansible Splunk Callback working:

1. Install this **Ansible Monitoring & Diagnostics** using the normal Splunk process
2. In Splunk add a **HTTP Event Collector** data input.
3. Place the **splunk.py** Ansible callback file, currently in the apps **bin** directory into a directory within the root of your Ansible playbook called **callbacks**
4. Update your **"ansible.cfg"** with settings from the Splunk HTTP Event Collector data input

When you run your ansible plays, detailed JSON formatted results will now be sent to Splunk.

---

## Converging Data

Converging Data are a Splunk specialist partner and we developed this application for internal use for our DevOps teams who use and develop Ansible extensively. Our Splunk specialists deploy all customer Splunk deployments using our **Data Platform as a Service** tool kit which is Ansible based. We have extended Ansible Monitoring & Diagnostics solutions that enable large organisations and teams to use a common Splunk service providing enterprise class monitoring and logging for your DepOps Teams.

If you would like explore how we can enable Splunk and or Ansible solutions for your team please get in touch [https://convergingdata.com](https://convergingdata.com/)
