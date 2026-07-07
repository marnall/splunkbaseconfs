## SA-sslcert_lookup

This supporting add-on provides an external lookup called `sslcert_lookup` to collect the attributes of an SSL cert at a given address and port. It is built on the Splunk SDK.

Version: 1.1.5

Lookup reference:

# sslcert_lookup

## Description

Given the input of a domain or ip address and optionally a connecting port (defaults to https 443 port if not specified), the `sslcert_lookup` returns various attributes of an SSL certificate.

## Syntax

` * | lookup sslcert_lookup dest AS <search field with domain or ip> [dest_port AS <search field with port>] [OUTPUT <specfic field list>] `

### Required arguments

 **dest field from search**  
    **Syntax:** * | lookup sslcert_lookup dest AS \<search field with domain or ip\>
    **Description:** Specify a field with a domain or ip address value.

### Optional arguments

 **dest\_port field from search**  
   	**Syntax:** * | lookup sslcert_lookup dest AS \<search field with domain or ip\> dest\_port AS <search field with port\>
   	**Description:** Specify a field with a port to connect to.
   	**Default:** 443

# sslcert macro

## Description

Simple method for running the sslcert\_lookup.

## Syntax

``` * | `sslcert(<search field with domain or ip>[, <search field with port>])` ```

### Required arguments

 **dest field from search**
    **Syntax:** * | \`sslcert(\<search field with domain or ip\>)\`
    **Description:** Specify a field with a domain or ip address value.

### Optional arguments

 **dest\_port field from search**
        **Syntax:** * | \`sslcert(\<search field with domain or ip\>, \<search field with port\>)\`
        **Description:** Specify a field with a port to connect to.
        **Default:** 443

# Possible Fields Returned

ssl\_end\_time, ssl\_engine, ssl\_hash, ssl\_is\_valid, ssl\_issuer, ssl\_issuer\_common\_name, ssl\_issuer\_email, ssl\_issuer\_locality, ssl\_issuer\_organization, ssl\_issuer\_state, ssl\_issuer\_street, ssl\_issuer\_unit, ssl\_name, ssl\_policies, ssl\_publickey, ssl\_publickey\_algorithm, ssl\_self\_issued, ssl\_self\_signed, ssl\_serial, ssl\_session\_id, ssl\_signature\_algorithm, ssl\_start\_time, ssl\_subject, ssl\_subject\_alt\_name, ssl\_subject\_common\_name, ssl\_subject\_email, ssl\_subject\_locality, ssl\_subject\_organization, ssl\_subject\_state, ssl\_subject\_street, ssl\_subject\_unit, ssl\_validity\_window, ssl\_version

## Examples

### **1: Connect to domain**

`| makeresults | eval dest="splunk.com" | lookup sslcert_lookup dest`

### **2: Connect to domain using macro**

``` | makeresults | eval dest="splunk.com" | `sslcert(dest)` ```

### **3: Connect to ip**

`| makeresults | eval dest="8.8.8.8" | lookup sslcert_lookup dest`

### **4: Connect to host and port**

`| makeresults | eval dest="mysplunkserver", dest_port=8000 | lookup sslcert_lookup dest dest_port`

### **5: Connect to host and port using macro**

``` | makeresults | eval dest="mysplunkserver", dest_port=8000 | `sslcert(dest, dest_port)` ```

### **6: Connect to ip and get only CN**

`| makeresults | eval dest="8.8.8.8" | lookup sslcert_lookup dest OUTPUT ssl_subject_common_name`

### **6: Connect to ip and get only CN and SAN**

`| makeresults | eval dest="8.8.8.8" | lookup sslcert_lookup dest OUTPUT ssl_subject_common_name ssl_subject_alt_name | eval ssl_subject_alt_name = split(ssl_subject_alt_name,"|")`

### Support
Support will be provided through Splunkbase

### Release Notes
* 1.1.5: Added fast-fail timeout for unreachable hosts in sslcert_lookup external command (improves performance when destination does not exist). Update splunklib from 2.0.2 to 2.1.1.
* 1.1.4: Updated splunklib from 1.7.3 to 2.0.2.