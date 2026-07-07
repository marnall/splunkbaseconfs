[comment]: # "Auto-generated SOAR connector documentation"
# Exodus

Publisher: Mhike  
Connector Version: 1\.0\.1  
Product Vendor: Mhike  
Product Name: Exodus  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 4\.9\.0  

The Exodus app manages various operations used in migrating content from dev to prod


## Requirements

Exodus migrates playbooks, custom functions, and assets via Phantom's rest API and uses containers
under an **exodus** label to specify content that is being reviewed for migration. Several things
are requires to effectively make this process flow work. You can run exodus from either your dev or
your prod instance. The chosen host is where you will configure Exodus assets and "ingestion".
Exodus does not technically ingest anything but the ingestion scheduling is used to define the
interval time between checks for now content to be migrated  

### API Tokens

You will need a Phantom API token for both your dev and your production environment  
Dev Permissions: Playbooks: R, Custom Code: RW, Apps: R, Assets: R  
Prod Permissions: Playbooks: R, Custom Code: RW, Apps: R, Assets: R  
Additional permissions for exodus ingestion host: Container: RW, Assets: W, Playbooks: W  
  

### File System

During migration, playbook and custom function tarballs are temporarily written to /tmp on the
filesystem  
  

### Label

This app creates containers under the label **exodus** . This label should be created in your
Phantom host that will run exodus. Permissions for this label should be restricted to roles that are
authorized to review and approve content for production  
  

### Tag

Exodus identifies "new" content for migration based on 2 things: object ID and tags. Any playbook
that has a new ID (because it has been changed) and a **prod** tag will be considered a candidate
for migration. The **prod** tag should be created in your dev phantom environment for this
purpose.  
  

### Playbooks and Custom Functions

Exodus identifies candidate playbooks and custom functions and creates **exodus** containers. Once
these containers are created, the only requirement left to signal Exodus to move the content to prod
is to run the Exodus action **add approval** . The methodology for how that action is invoked and
what the process looks like is defined by the organization. It can be as simple as requiring leads
on the dev team to review all new exodus containers and manually run the add approval action if they
approve or close the container if they don't approve. It is recommended that an active playbook be
created for the exodus containers that builds and sends an approval request via prompts, slack,
email, etc in order to make your process smoother and more auditable. It would be wise to store
these playbooks in an "admin" repo to prevent unauthorized users from adversly modifying the
approval process playbook.  
  

### Assets

If assets are to be migrated, exodus must be executed on the source host that the assets are
initially created on in order to stay intact.  
If assets are "pulled" from their host instead of "pushed" pasword fields will be broken.  
  


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Exodus asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**source\_base\_url** |  required  | string | URL for source SOAR host
**source\_api\_token** |  required  | password | API token for source SOAR host
**source\_dev\_repo\_id** |  required  | string | Dev Repository ID for source SOAR host
**source\_prod\_repo\_id** |  optional  | string | Prod repository ID on source SOAR host
**source\_tenant\_id** |  optional  | string | Tenant ID on source SOAR host
**target\_base\_url** |  required  | string | URL for target SOAR host
**target\_api\_token** |  required  | password | API token for target SOAR host
**target\_repo\_id** |  required  | string | Prod repository ID on target SOAR host
**debug** |  optional  | boolean | Print debugging statements to log

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied credentials  
[add approval](#action-add-approval) - Add approval artifact to container  
[on poll](#action-on-poll) - Execute migration options  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied credentials

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'add approval'
Add approval artifact to container

Type: **generic**  
Read only: **False**

Add a specifically formatted artifact that is required for the approval process for exodus containers\.

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'on poll'
Execute migration options

Type: **ingest**  
Read only: **False**

Create required exodus containers and migrate approved content to production system\.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output