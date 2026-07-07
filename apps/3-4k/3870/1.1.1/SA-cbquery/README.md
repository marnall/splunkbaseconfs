## SA-cbquery

This supporting add-on provides the commands -- `cbquery` and `cbedit`. It is built on Carbon Black's cbapi and the Splunk SDK (note that this is not an offical product of Carbon Black).

Version: 1.1.1

Command reference:

# cbquery

## Description

The `cbquery` queries Carbon Black’s API (cbapi) and generates Splunk events from the results returned. This app has only been tested with Cb Protection and Cb Response but should also work with Cb Defense. Credentials must be generated and setup before command will work.

The command requires that the specific Cb product to query is specified as well as an model object class from their API. Finally a Cb query is fed to the command. The query syntax can be a bit tricky at first, see the Examples tab and the documentation to the appropriate product on [Cb’s API Documentation](https://cbapi.readthedocs.io/en/latest/index.html#api-documentation) or the Reference tab on [Carbon Black's Developer Network](https://developer.carbonblack.com).

## Syntax

cbquery product=\<string> model=\<string> query="\<string>" \[fields="\<comma-seperated-field-list>"]

### Required arguments

 **product**  
   	**Syntax:** product=\<string>
   	**Description:** Specify a Cb Product to query
   	**Usage:** product=defense | product=protection | product=response

 **model**  
   	**Syntax:** model=\<string>
   	**Description:** Specify a Model Object Class (UpperCamelCase) from the appropriate Cb Product to query
   	**Usage:** i.e. model=Computer | model=FileCatalog

 **query**  
   	**Syntax:** query="\<string>"
   	**Description:** Specify a Cb API query, allows combined clauses and boolean statements (<a href="https://cbapi.readthedocs.io/en/latest/index.html#api-documentation">See appropriate product documentation</a>)
   	**Usage:** i.e. query="all()" | query="where('deleted:False')" | "query="where('deleted:False')\[:10]" | "query="where('fileType:Application|Package').and\_('prevalence>0').and\_('effectiveState:Unapproved').and\_('certificateState:1')"

### Optional arguments

  **fields**  
   	**Syntax:** fields="\<comma-seperated-field-list\>"  
   	**Description:** Name of the fields to limit the query to (note limiting the fields can decrease the query response time)
   	**Usage:** i.e. fields="fileName,fileSize,md5,pathName,prevalence"
   	**Default:** all fields returned if not specified

## Examples

### **1: Unsure which fields to query on so bring back all results (slower)**

`| cbquery product=protection model=Computer query="all()"`

### **2: Single where clause on boolean field**

`| cbquery product=protection model=Computer query="where('deleted:False')"`

### **3: Bring back only the first 10 results**

`| cbquery product=protection model=Computer query="where('deleted:False')[:10]"`

### **4: Multiple clauses, multiple conditions (or, greater than, equals), only specific fields (faster)**

`| cbquery product=protectionmodel=FileCatalog query="where('fileType:Application|Package').and_('prevalence>0').and_('effectiveState:Unapproved').and_('certificateState:1')" fields="fileName,fileSize,md5,pathName,prevalence" | sort -prevalence`

### **5: Look for first 10 results of processes of a specific name **

`cbquery product=response model=Process query="where('process_name:notepad.exe')[:10]"`

### **6: Look for first 10 results of processes talking to specific domain **

`| cbquery product=response model=Process query="where('domain:splunk.com')[:10]"`

### **7: Look for first 10 results of processes talking to specific IP and port**

`| cbquery product=response model=Process query="where('ipaddr:8.8.8.8 ipport:53')[:10]"`

# cbedit

## Description

The `cbedit` updates Carbon Black’s API (cbapi) and generates Splunk events from the results returned along with an audit field that is logged. This command has only been tested with Cb Protection but should also work with Cb Response and Cb Defense. Credentials must be generated and setup before command will work and the api user would need to have rights to edit the given target.

The command requires that the specific Cb product to query is specified as well as an model object class from their API. Finally a Cb query is fed to the command. The query syntax can be a bit tricky at first, see the Examples tab and the documentation to the appropriate product on [Cb’s API Documentation](https://cbapi.readthedocs.io/en/latest/index.html#api-documentation) or the Reference tab on [Carbon Black's Developer Network](https://developer.carbonblack.com).

## Syntax

cbedit product=\<string> model=\<string> query="\<string>" target=\<field> value\"\<string> \[ticket="\<string>"]

### Required arguments

 **product**  
   	**Syntax:** product=\<string>
   	**Description:** Specify a Cb Product to query
   	**Usage:** product=defense | product=protection | product=response

 **model**  
   	**Syntax:** model=\<string>
   	**Description:** Specify a Model Object Class (UpperCamelCase) from the appropriate Cb Product to query
   	**Usage:** i.e. model=Policy

 **query**  
   	**Syntax:** query="\<string>"
   	**Description:** Specify a Cb API query, allows combined clauses and boolean statements (<a href="https://cbapi.readthedocs.io/en/latest/index.html#api-documentation">See appropriate product documentation</a>)
   	**Usage:** i.e. query="where('deleted:False').and\_('name:\*my\_host')"

 **target**  
   	**Syntax:** target=\<field>
   	**Description:** Specify a field from the appropriate Cb Product to update. Requires permission and not all fields are able to be updated.
   	**Usage:** i.e. target=policyId

 **value**  
   	**Syntax:** value=\<string>
   	**Description:** Specify the new value for the target field specified
   	**Usage:** i.e. value=3

### Optional arguments

  **ticket**  
   	**Syntax:** ticket="\<string\>"  
   	**Description:** Value of associated change ticket to be returned in audit field and log
   	**Usage:** i.e. ticket="HELPDESK-12345"
   	**Default:** None

## Examples

### **1: Update enforcement policy**

`| cbedit product=protection model=Computer query="where('name:computer1')" target="policyId" value=3`

### Release Notes
Added new cbedit command. Updated for Python 3 compatibility. Updated response to use newer API. Tested cbquery with CB Response. Updated packages to latest versions - cbapi, concurrent, dateutil, splunklib, yaml. Added package solrq. Updates for splunk appinspect compliance. Updated documentation. Added examples for Response. 
