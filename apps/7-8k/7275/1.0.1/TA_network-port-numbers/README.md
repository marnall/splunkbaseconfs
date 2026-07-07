![icon](static/appIcon_2x.png)

# TA_network-port-numbers

A Splunk technology add-on (TA) to enrich network port numbers with service names and descriptions.

## Purpose

This TA adds fields to any event that contains a `transport` field and either a `dest_port` or `src_port` field.
These fields are elements of the Splunk Common Information Model (CIM) for networking.

Depending on which fields are available in an event, service fields and service description fields may be added -- if they are registered with IANA.
The following table lists the added fields (in **bold**). If both dest and src exist, both sets of service fields may be added.

| transport | port | | service | service description |
| :--- | :--- | :---: | :--- | :--- |
| `transport` | `dest_port` | &rarr; | **`dest_svc`** | **`dest_svc_description`** |
| `transport` | `src_port` | &rarr; | **`src_svc`** | **`src_svc_description`** |

The `dest_svc` or `src_svc` field is the IANA service name for the port in question and follows the naming convention recommended for the Network CIM.
The `dest_svc_description` or `src_svc_description` field is the IANA description of the service.

## Prerequisites and Dependencies

The TA should be installed only on search heads. It can be deployed to a search head cluster via a deployer. It will run on Linux or Windows.

Once per month (by default), the TA runs a scheduled search (named `network-port-numbers_update_iana_ports`) that updates the lookup table with the latest port information from [IANA](https://www.iana.org/assignments/service-names-port-numbers).
This functionality requires Splunk 8.0 or later (i.e. Python 3). The search heads should have Internet web access for this to work.

## Developer

The TA was developed by Frank Wayne.

## Support Contact

Contact [the developer](mailto:frank.wayne@northwestern.edu?subject=TA_network-port-numbers) with questions, bug reports or change requests. You can also refer or contribute to the [GitHub repository](https://github.com/thatfrankwayne/TA_network-port-numbers).
