# DocoDoco Advance 1.2.0

## OVERVIEW
You can get local information and organizational information from IP addresses by using this add-on.  
**Current version:** 1.2.0

This add-on enables you to enrich logs with location data, organization information, and anonymized network indicators based on IP addresses.  
It supports two data acquisition routes:

- **DocoDoco JP Direct Route**  
- **API Hub Route**

Depending on your subscription and chosen route, the available data fields and IP support differ.

---

## NOTICE
- It is necessary to subscribe to a paid plan of **DocoDoco (Paid services)** **or** sign up for a plan via **API Hub** to use this add-on.  
  - [DocoDoco](https://www.docodoco.jp/)  
  - [API Hub](https://api.sbi-digitalhub.co.jp/)  

- After joining a plan, **select the APIs you want to use** and **register the required API keys**.  
  - ⚠️ **Be careful:** Keys for unselected APIs will be invalidated/removed.

- Internet access is required (to request data from `api.docodoco.jp` or API Hub endpoints).

---

## DATA SOURCE OPTIONS

### 1. DocoDoco JP Direct Route
- Provides **location, organization, anonymized network**, and other additional data depending on your contracted plan.  
- The exact response fields depend on your contract with DocoDoco.  
- Supports **IPv4 and IPv6** (depending on your subscription and plan).  
- For details about the parameters returned, see:  
  [DocoDoco REST API Parameters](https://www.docodoco.jp/api/master-data/)

### 2. API Hub Route
- Provides **organization information, location information, and anonymized network data only**.  

---

## INSTALLATION

1. Install **DocoDoco Advance Add-on (version 1.2.0)**  
   Download from [Splunkbase](https://splunkbase.splunk.com/)

2. Subscribe to a plan:  
   - Either **DocoDoco (Paid services)** or **API Hub**.

3. Obtain the API key(s) for the services you selected.  
   - DocoDoco: [DocoDoco JP](https://www.docodoco.jp/)  
   - API Hub: [API Hub](https://api.sbi-digitalhub.co.jp/)

4. Set the API key(s) in the **configuration dashboard** of this add-on.


## EXAMPLE
Run the custom search command `docodoco` to enrich logs with IP-based data:

```spl
| docodoco ipfield=<IP address field>
```

The data returned by "DocoDoco" are based on return parameters of "DocoDoco". 
Look at the following URL about return parameters. 
https://www.docodoco.jp/api/master-data/

## Performance
・6 core cpu and 10 parallel : about 1000 req/min
