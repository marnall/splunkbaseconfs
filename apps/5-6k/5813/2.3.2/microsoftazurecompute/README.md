# Microsoft Azure Compute

Publisher: Splunk <br>
Connector Version: 2.3.2 <br>
Product Vendor: Microsoft <br>
Product Name: Azure Compute <br>
Minimum Product Version: 6.0.2

This app implements virtualization actions for Microsoft Azure Virtual Machines

### Configuration variables

This table lists the configuration variables required to operate Microsoft Azure Compute. These variables are specified when configuring a Azure Compute asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**subscription_id** | required | string | Subscription ID |
**tenant_id** | required | string | Tenant ID |
**client_id** | required | string | Application (client) ID assigned to your Azure Compute app |
**client_secret** | required | password | Client Secret |
**admin_access** | optional | boolean | Admin Access Required |
**admin_consent** | optional | boolean | Admin consent already provided |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[generate token](#action-generate-token) - Generates a token <br>
[get system info](#action-get-system-info) - Get information about a VM <br>
[list vms](#action-list-vms) - Get the list of registered VMs <br>
[snapshot vm](#action-snapshot-vm) - Take a snapshot of the VM <br>
[start vm](#action-start-vm) - Start a stopped or suspended VM <br>
[stop vm](#action-stop-vm) - Stop a VM <br>
[delete vm](#action-delete-vm) - Delete a VM <br>
[deallocate vm](#action-deallocate-vm) - Shut down the virtual machine and release the compute resources. You are not billed for the compute resource that this virtual machine uses <br>
[list tags](#action-list-tags) - Get the names and values of all resource tags that are defined in the subscription <br>
[create tag](#action-create-tag) - Create or update a tag <br>
[list resource groups](#action-list-resource-groups) - Get the list of resource groups for the subscription <br>
[list snapshots](#action-list-snapshots) - Get the list of snapshots under the subscription <br>
[list security groups](#action-list-security-groups) - Get the list of all security groups in a resource group <br>
[add network group](#action-add-network-group) - Add a network security group in a resource group <br>
[add application group](#action-add-application-group) - Add an application security groups in a resource group <br>
[list virtual networks](#action-list-virtual-networks) - Get the list of virtual networks <br>
[list subnets](#action-list-subnets) - Get the list of subnets <br>
[get ip availability](#action-get-ip-availability) - Check if a private IP address is available for use <br>
[generalize vm](#action-generalize-vm) - Set the state of the virtual machine to be generalized <br>
[redeploy vm](#action-redeploy-vm) - Redeploy a virtual machine <br>
[run command](#action-run-command) - Run a command on the virtual machine <br>
[get results](#action-get-results) - Fetch the results of a previously executed run_command action

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'generate token'

Generates a token

Type: **generic** <br>
Read only: **False**

This action generated a new token whenever any action fails because of an invalid or expired token.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Token generated |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get system info'

Get information about a VM

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | testVM |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Compute/virtualMachines/testVM |
action_result.data.\*.location | string | | westus |
action_result.data.\*.name | string | `vm management virtual machine` | testVM |
action_result.data.\*.properties.diagnosticsProfile.bootDiagnostics.enabled | boolean | | True False |
action_result.data.\*.properties.diagnosticsProfile.bootDiagnostics.storageUri | string | `url` | https://myresourcegroup1diag311.blob.core.windows.net/ |
action_result.data.\*.properties.hardwareProfile.vmSize | string | | Standard_B1s |
action_result.data.\*.properties.networkProfile.networkInterfaces.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/networkInterfaces/testvm133 |
action_result.data.\*.properties.osProfile.adminUsername | string | `user name` | test |
action_result.data.\*.properties.osProfile.allowExtensionOperations | boolean | | True False |
action_result.data.\*.properties.osProfile.computerName | string | `vm management virtual machine` | testVM |
action_result.data.\*.properties.osProfile.linuxConfiguration.disablePasswordAuthentication | boolean | | True False |
action_result.data.\*.properties.osProfile.linuxConfiguration.provisionVMAgent | boolean | | True False |
action_result.data.\*.properties.osProfile.windowsConfiguration.enableAutomaticUpdates | boolean | | True False |
action_result.data.\*.properties.osProfile.windowsConfiguration.provisionVMAgent | boolean | | True False |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.storageProfile.imageReference.offer | string | | UbuntuServer |
action_result.data.\*.properties.storageProfile.imageReference.publisher | string | | Canonical |
action_result.data.\*.properties.storageProfile.imageReference.sku | string | | 18.04-LTS |
action_result.data.\*.properties.storageProfile.imageReference.version | string | | latest |
action_result.data.\*.properties.storageProfile.osDisk.caching | string | | ReadWrite |
action_result.data.\*.properties.storageProfile.osDisk.createOption | string | | FromImage |
action_result.data.\*.properties.storageProfile.osDisk.diskSizeGB | numeric | | 30 |
action_result.data.\*.properties.storageProfile.osDisk.managedDisk.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Compute/disks/testVM_OsDisk_1_1c75b0f4f5df46ba88997aac183d8ad6 |
action_result.data.\*.properties.storageProfile.osDisk.managedDisk.storageAccountType | string | | Premium_LRS |
action_result.data.\*.properties.storageProfile.osDisk.name | string | | testVM_OsDisk_1_1c75b0f4f5df46ba88997aac183d8ad6 |
action_result.data.\*.properties.storageProfile.osDisk.osType | string | | Linux |
action_result.data.\*.properties.storageProfile.osDisk.vhd.uri | string | | https://testdisks466.blob.core.windows.net/vhds/unmanagedVM20190125164741.vhd |
action_result.data.\*.properties.vmId | string | | 58a871bc-1cbb-4a86-8603-a73527071c74 |
action_result.data.\*.resources.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myresourcegroup1/providers/Microsoft.Compute/virtualMachines/virtualMachine1/extensions/OmsAgentForLinux |
action_result.data.\*.resources.\*.location | string | | eastus |
action_result.data.\*.resources.\*.name | string | | OmsAgentForLinux |
action_result.data.\*.resources.\*.properties.autoUpgradeMinorVersion | boolean | | True False |
action_result.data.\*.resources.\*.properties.provisioningState | string | | Updating |
action_result.data.\*.resources.\*.properties.publisher | string | | Microsoft.EnterpriseCloud.Monitoring |
action_result.data.\*.resources.\*.properties.settings.azureResourceId | string | | |
action_result.data.\*.resources.\*.properties.settings.stopOnMultipleConnections | string | | true |
action_result.data.\*.resources.\*.properties.settings.workspaceId | string | | 4a6116d3-9349-40bb-8b06-ac937da327b6 |
action_result.data.\*.resources.\*.properties.type | string | | OmsAgentForLinux |
action_result.data.\*.resources.\*.properties.typeHandlerVersion | string | | 1.4 |
action_result.data.\*.resources.\*.type | string | | Microsoft.Compute/virtualMachines/extensions |
action_result.data.\*.tags.author | string | | appdev |
action_result.data.\*.tags.company | string | | Splunk |
action_result.data.\*.type | string | | Microsoft.Compute/virtualMachines |
action_result.summary | string | | |
action_result.message | string | | The system info was successfully retrieved |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list vms'

Get the list of registered VMs

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | optional | Name of the resource group | string | `vm management resource group` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/MYRESOURCEGROUP1/providers/Microsoft.Compute/virtualMachines/virtualMachine1 |
action_result.data.\*.location | string | | eastus |
action_result.data.\*.name | string | `vm management virtual machine` | virtualMachine1 |
action_result.data.\*.properties.diagnosticsProfile.bootDiagnostics.enabled | boolean | | True False |
action_result.data.\*.properties.diagnosticsProfile.bootDiagnostics.storageUri | string | `url` | https://myresourcegroup1diag406.blob.core.windows.net/ |
action_result.data.\*.properties.hardwareProfile.vmSize | string | | Standard_B1s |
action_result.data.\*.properties.networkProfile.networkInterfaces.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/networkInterfaces/virtualmachine1259 |
action_result.data.\*.properties.osProfile.adminUsername | string | `user name` | test-user |
action_result.data.\*.properties.osProfile.allowExtensionOperations | boolean | | True False |
action_result.data.\*.properties.osProfile.computerName | string | `vm management virtual machine` | virtualMachine1 |
action_result.data.\*.properties.osProfile.linuxConfiguration.disablePasswordAuthentication | boolean | | True False |
action_result.data.\*.properties.osProfile.linuxConfiguration.provisionVMAgent | boolean | | True False |
action_result.data.\*.properties.osProfile.linuxConfiguration.ssh.publicKeys.\*.keyData | string | | ssh-rsa sample_rsa_AAAbWxYa/Cw
I3pXrnLZbh2obel1riER4uqamt1mbM+maPPxCCyBDyDIy31
KTDYhRJ7j2vNbaa5Oyt6H8Zasypmpzth2jEwKDDi62EkQTyrNsm/CFkycMuflVZx
eVxXjIFG2ix0ENkSg1VXbAb6Nz0r+zBFXkOppdpSe/j+oqKihw7KjFLe0YtIwxiN
Fu0MHCBBvdSBmFtzrhkk3g7bnMqbD8JQdzKgkNW4xM9
ZRjXtwdsn7XOVcNsJ2K0e4u5xJfb6RmBQAh3IplVXX
GOMl3d9S/AWmL2FLO/j9250ntbi2BsU+g0G6E
cpC9JxMu5laUd/Cee2EhG+27U51nzE4O/eaVQwNAEKdYRYP9rocOisx
peqy6TbUwnrrir/4y8woNYso+R4k= generated-by-azure |
action_result.data.\*.properties.osProfile.linuxConfiguration.ssh.publicKeys.\*.path | string | | /home/azureuser/.ssh/authorized_keys |
action_result.data.\*.properties.osProfile.windowsConfiguration.enableAutomaticUpdates | boolean | | True |
action_result.data.\*.properties.osProfile.windowsConfiguration.provisionVMAgent | boolean | | True |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.storageProfile.imageReference.offer | string | | UbuntuServer |
action_result.data.\*.properties.storageProfile.imageReference.publisher | string | | Canonical |
action_result.data.\*.properties.storageProfile.imageReference.sku | string | | 18.04-LTS |
action_result.data.\*.properties.storageProfile.imageReference.version | string | | latest |
action_result.data.\*.properties.storageProfile.osDisk.caching | string | | ReadWrite |
action_result.data.\*.properties.storageProfile.osDisk.createOption | string | | FromImage |
action_result.data.\*.properties.storageProfile.osDisk.diskSizeGB | numeric | | 30 |
action_result.data.\*.properties.storageProfile.osDisk.managedDisk.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Compute/disks/virtualMachine1_OsDisk_1_3475f0acf8aa4d3e8daa84c7327adde1 |
action_result.data.\*.properties.storageProfile.osDisk.managedDisk.storageAccountType | string | | StandardSSD_LRS |
action_result.data.\*.properties.storageProfile.osDisk.name | string | | virtualMachine1_OsDisk_1_3475f0acf8aa4d3e8daa84c7327adde1 |
action_result.data.\*.properties.storageProfile.osDisk.osType | string | | Linux |
action_result.data.\*.properties.storageProfile.osDisk.vhd.uri | string | | https://testdisks466.blob.core.windows.net/vhds/unmanagedVM20190125164741.vhd |
action_result.data.\*.properties.vmId | string | | 6ead047c-7405-4f68-a0da-0b12fd99e185 |
action_result.data.\*.resources.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/MYRESOURCEGROUP1/providers/Microsoft.Compute/virtualMachines/virtualMachine1/extensions/OmsAgentForLinux |
action_result.data.\*.tags.author | string | | appdev |
action_result.data.\*.tags.company | string | | Splunk |
action_result.data.\*.tags.type | string | | vm |
action_result.data.\*.type | string | | Microsoft.Compute/virtualMachines |
action_result.summary.num_vms | numeric | | 2 |
action_result.message | string | | Num vms: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'snapshot vm'

Take a snapshot of the VM

Type: **generic** <br>
Read only: **False**

While creating a snapshot using the COPY option, 'source_resource_id' parameter is required and while using the IMPORT option, 'source_uri' parameter is required. For the 'source_uri' parameter, the uri value should be valid page blob uri path. For more information refer to <a href='https://docs.microsoft.com/en-us/rest/api/compute/snapshots/create-or-update' target='_blank'>API Docs</a>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**snapshot_name** | required | The name of the snapshot that is being created. The name can't be changed after the snapshot is created. Supported characters for the name are a-z, A-Z, 0-9, and \_. The max name length is 80 characters | string | |
**location** | required | Resource location | string | |
**create_option** | required | Source for disk's creation | string | |
**source_resource_id** | optional | If create_option is Copy, this is the ARM ID of the source snapshot or disk | string | |
**source_uri** | optional | If create_option is Import, this is the URI of a blob to be imported into a managed disk | string | |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.create_option | string | | Copy |
action_result.parameter.location | string | | West US |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.snapshot_name | string | | my_new_snapshot |
action_result.parameter.source_resource_id | string | | subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Compute/snapshots/mySnapshot1 |
action_result.parameter.source_uri | string | | |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.location | string | | West US |
action_result.data.\*.name | string | | my_new_snapshot |
action_result.data.\*.properties.creationData.createOption | string | | Copy |
action_result.data.\*.properties.creationData.sourceResourceId | string | | subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Compute/snapshots/mySnapshot1 |
action_result.data.\*.properties.creationData.sourceUri | string | | https://testdisks466.blob.core.windows.net/vhds/unmanagedVM20190125164741.vhd |
action_result.data.\*.properties.diskSizeBytes | numeric | | 13636730880 |
action_result.data.\*.properties.diskSizeGB | numeric | | 30 |
action_result.data.\*.properties.faultDomain | numeric | `domain` | 0 |
action_result.data.\*.properties.isArmResource | boolean | | True False |
action_result.data.\*.properties.osType | string | | Linux |
action_result.data.\*.properties.provisioningState | string | | Updating |
action_result.data.\*.sku.name | string | | Standard_LRS |
action_result.data.\*.sku.tier | string | | Standard |
action_result.data.\*.tags.author | string | | appdev |
action_result.summary.provisioning_state | string | | Updating |
action_result.summary.status | string | | Successfully created snapshot |
action_result.message | string | | Status: Successfully created snapshot, Provisioning state: Updating |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'start vm'

Start a stopped or suspended VM

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | testVM |
action_result.data | string | | |
action_result.summary.status | string | | Successfully started VM |
action_result.message | string | | Status: Successfully started VM |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'stop vm'

Stop a VM

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | testVM |
action_result.data | string | | |
action_result.summary.status | string | | Successfully stopped VM |
action_result.message | string | | Status: Successfully stopped VM |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete vm'

Delete a VM

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | DefaultResourceGroup-EUS |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | test |
action_result.data | string | | |
action_result.summary.status | string | | Successfully deleted the vm |
action_result.message | string | | Status: Successfully deleted the vm |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'deallocate vm'

Shut down the virtual machine and release the compute resources. You are not billed for the compute resource that this virtual machine uses

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | testVM |
action_result.data | string | | |
action_result.summary.status | string | | Successfully deallocated VM |
action_result.message | string | | Status: Successfully deallocated VM |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tags'

Get the names and values of all resource tags that are defined in the subscription

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.count.type | string | | Total |
action_result.data.\*.count.value | numeric | | 22 |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/tagNames/author |
action_result.data.\*.tagName | string | `vm management tag name` | author |
action_result.data.\*.values.\*.count.type | string | | Total |
action_result.data.\*.values.\*.count.value | numeric | | 22 |
action_result.data.\*.values.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/tagNames/author/tagValues/appdev |
action_result.data.\*.values.\*.tagValue | string | | appdev |
action_result.summary.num_tags | numeric | | 6 |
action_result.message | string | | Num tags: 6 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create tag'

Create or update a tag

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tag_name** | required | The name of the tag | string | `vm management tag name` |
**tag_value** | optional | The value of the tag to create or update | string | |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.subscription_id | string | | |
action_result.parameter.tag_name | string | `vm management tag name` | company |
action_result.parameter.tag_value | string | | Splunk |
action_result.data | string | | |
action_result.data.\*.count.type | string | | Total |
action_result.data.\*.count.value | numeric | | 0 |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/tagNames/QA1 |
action_result.data.\*.tagName | string | | QA1 |
action_result.summary.status | string | | Successfully created tag |
action_result.message | string | | Status: Successfully created tag |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list resource groups'

Get the list of resource groups for the subscription

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/DefaultResourceGroup-EUS |
action_result.data.\*.location | string | | eastus |
action_result.data.\*.name | string | `vm management resource group` | DefaultResourceGroup-EUS |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.tags.company | string | | mycomp |
action_result.data.\*.tags.{"keyname": "keyvalue"} | string | | abcd |
action_result.summary.num_resource_groups | numeric | | 4 |
action_result.message | string | | Num resource groups: 4 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list snapshots'

Get the list of snapshots under the subscription

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | optional | The name of the resource group | string | `vm management resource group` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Compute/snapshots/mySnapshot1 |
action_result.data.\*.location | string | | westus |
action_result.data.\*.name | string | `vm management tag name` | mySnapshot1 |
action_result.data.\*.properties.creationData.createOption | string | | Copy |
action_result.data.\*.properties.creationData.sourceResourceId | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/MYRESOURCEGROUP1/providers/Microsoft.Compute/disks/testVM_OsDisk_1_1c75b0f4f5df46ba88997aac183d8ad6 |
action_result.data.\*.properties.creationData.sourceUri | string | | https://testdisks466.blob.core.windows.net/vhds/unmanagedVM20190125164741.vhd |
action_result.data.\*.properties.diskSizeGB | numeric | | 30 |
action_result.data.\*.properties.diskState | string | | Unattached |
action_result.data.\*.properties.osType | string | | Linux |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.timeCreated | string | | 2019-01-17T20:55:06.9032116+00:00 |
action_result.data.\*.sku.name | string | | Standard_LRS |
action_result.data.\*.sku.tier | string | | Standard |
action_result.data.\*.tags.author | string | | appdev |
action_result.data.\*.tags.type | string | | snapshot |
action_result.data.\*.type | string | | Microsoft.Compute/snapshots |
action_result.summary.num_snapshots | numeric | | 3 |
action_result.message | string | | Num snapshots: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list security groups'

Get the list of all security groups in a resource group

Type: **investigate** <br>
Read only: **True**

API limitation: Network Security Group (classic) is not part of the response.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**group_type** | required | Type of security group to query | string | |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_type | string | | network application |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.etag | string | | W/"bc870279-4d7a-4ced-a4b1-0311c27b5111" |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/applicationSecurityGroups/appSGtest |
action_result.data.\*.location | string | | westus |
action_result.data.\*.name | string | `vm management group name` | appSGtest |
action_result.data.\*.properties.defaultSecurityRules.\*.etag | string | | W/"d086e328-28dc-4534-8f54-1373c8d4f255" |
action_result.data.\*.properties.defaultSecurityRules.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/test/providers/Microsoft.Network/networkSecurityGroups/aaaaa-nsg/defaultSecurityRules/AllowVnetInBound |
action_result.data.\*.properties.defaultSecurityRules.\*.name | string | | AllowVnetInBound |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.access | string | | Allow |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.description | string | | Allow inbound traffic from all VMs in VNET |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.destinationAddressPrefix | string | | VirtualNetwork |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.destinationPortRange | string | | * |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.direction | string | | Inbound |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.priority | numeric | | 65000 |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.protocol | string | | * |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.sourceAddressPrefix | string | | VirtualNetwork |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.sourcePortRange | string | | * |
action_result.data.\*.properties.defaultSecurityRules.\*.type | string | | Microsoft.Network/networkSecurityGroups/defaultSecurityRules |
action_result.data.\*.properties.networkInterfaces.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/test/providers/Microsoft.Network/networkInterfaces/aaaaa382 |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.resourceGuid | string | | 93cab2f8-f56e-44f1-b804-886405bd362a |
action_result.data.\*.properties.securityRules.\*.etag | string | | W/"1c2086b4-b285-41f2-8ce0-9898a57f60ad" |
action_result.data.\*.properties.securityRules.\*.id | string | | /subscriptions/4c357906-2c22-4d91-98aa-180d9a85a370/resourceGroups/Test_Group/providers/Microsoft.Network/networkSecurityGroups/test.vm-3-nsg/securityRules/SSH |
action_result.data.\*.properties.securityRules.\*.name | string | | SSH |
action_result.data.\*.properties.securityRules.\*.properties.access | string | | Allow |
action_result.data.\*.properties.securityRules.\*.properties.destinationAddressPrefix | string | | * |
action_result.data.\*.properties.securityRules.\*.properties.destinationPortRange | string | | 22 |
action_result.data.\*.properties.securityRules.\*.properties.direction | string | | Inbound |
action_result.data.\*.properties.securityRules.\*.properties.priority | numeric | | 300 |
action_result.data.\*.properties.securityRules.\*.properties.protocol | string | | TCP |
action_result.data.\*.properties.securityRules.\*.properties.sourceAddressPrefix | string | | * |
action_result.data.\*.properties.securityRules.\*.properties.sourcePortRange | string | | * |
action_result.data.\*.properties.securityRules.\*.type | string | | Microsoft.Network/networkSecurityGroups/securityRules |
action_result.data.\*.tags.author | string | | Splunk |
action_result.data.\*.type | string | | Microsoft.Network/applicationSecurityGroups |
action_result.summary.num_security_groups | numeric | | 1 |
action_result.message | string | | Num security groups: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add network group'

Add a network security group in a resource group

Type: **generic** <br>
Read only: **False**

The 'security_rules' parameter accept JSON format value. For non-JSON values, the parameter values will be ignored. Refer to <a href='https://docs.microsoft.com/en-us/rest/api/virtualnetwork/networksecuritygroups/createorupdate' target='_blank'>API Docs</a> for more information on adding a network security group.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**group_name** | required | Name of security group to add | string | `vm management group name` |
**location** | required | Resource location | string | |
**tags** | optional | String object of resource tags | string | |
**default_security_rules** | optional | Comma separated list of default security rules for the network security group | string | |
**provisioning_state** | optional | The provisioning state of the public IP resource | string | |
**resource_guid** | optional | The resource GUID property of the network security group resource | string | |
**security_rules** | optional | Comma separated list of security rules of the network security group | string | |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.default_security_rules | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.group_name | string | `vm management group name` | netwGroup1 |
action_result.parameter.location | string | | West US 2 |
action_result.parameter.provisioning_state | string | | Updating |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.resource_guid | string | | |
action_result.parameter.security_rules | string | | [{"name": "rule1", "properties": { "protocol": "\*", "sourceAddressPrefix": "\*", "destinationAddressPrefix": "\*", "access": "Allow", "destinationPortRange": "80", "sourcePortRange": "\*", "priority": 130, "direction": "Inbound" } }] |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.tags | string | | {"author":"test-user"} |
action_result.data.\*.etag | string | | W/"12b43767-ecc7-4ed4-af5f-0c13b78dae0e" W/"d62d2fcf-970a-4955-b996-d586ea2f8a3c" |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/networkSecurityGroups/netwGroup1 |
action_result.data.\*.location | string | | westus2 |
action_result.data.\*.name | string | | netwGroup1 |
action_result.data.\*.properties.defaultSecurityRules.\*.etag | string | | W/"12b43767-ecc7-4ed4-af5f-0c13b78dae0e" W/"d62d2fcf-970a-4955-b996-d586ea2f8a3c" |
action_result.data.\*.properties.defaultSecurityRules.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/networkSecurityGroups/netwGroup1/defaultSecurityRules/AllowVnetInBound |
action_result.data.\*.properties.defaultSecurityRules.\*.name | string | | AllowVnetInBound |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.access | string | | Allow |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.description | string | | Allow inbound traffic from all VMs in VNET |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.destinationAddressPrefix | string | | VirtualNetwork |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.destinationPortRange | string | | * |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.direction | string | | Inbound |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.priority | numeric | | 65000 |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.protocol | string | | * |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.provisioningState | string | | Succeeded Updating |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.sourceAddressPrefix | string | | VirtualNetwork |
action_result.data.\*.properties.defaultSecurityRules.\*.properties.sourcePortRange | string | | * |
action_result.data.\*.properties.defaultSecurityRules.\*.type | string | | Microsoft.Network/networkSecurityGroups/defaultSecurityRules |
action_result.data.\*.properties.provisioningState | string | | Succeeded Updating |
action_result.data.\*.properties.resourceGuid | string | | 0214f54b-2274-470c-b87a-85578d05b942 |
action_result.data.\*.tags.author | string | | test-user |
action_result.data.\*.type | string | | Microsoft.Network/networkSecurityGroups |
action_result.summary.status | string | | Successfully added or updated security group |
action_result.message | string | | Status: Successfully added or updated security group |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add application group'

Add an application security groups in a resource group

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**group_name** | required | Name of security group to add | string | `vm management group name` |
**location** | required | Resource location | string | |
**tags** | optional | String object of resource tags. It should be in JSON format | string | |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_name | string | `vm management group name` | test_group |
action_result.parameter.location | string | | West US |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.tags | string | | {"author":"Splunk"} |
action_result.data.\*.etag | string | | W/"b6eab29d-32f4-48d2-80e1-06f8dfb3616a" |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/applicationSecurityGroups/test_group |
action_result.data.\*.location | string | | westus |
action_result.data.\*.name | string | `vm management group name` | example_name |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.tags.author | string | | Splunk |
action_result.data.\*.type | string | | Microsoft.Network/applicationSecurityGroups |
action_result.summary.status | string | | Successfully added or updated security group |
action_result.message | string | | Status: Successfully added or updated security group |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list virtual networks'

Get the list of virtual networks

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | optional | The name of the resource group | string | `vm management resource group` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data.\*.etag | string | | W/"afd6a89a-57fd-4eb4-bcbf-49ee9d377fc5" |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/virtualNetworks/myNetworkInterface1 |
action_result.data.\*.location | string | | westus |
action_result.data.\*.name | string | `vm management virtual network` | myNetworkInterface1 |
action_result.data.\*.properties.addressSpace.addressPrefixes | string | | 10.0.0.0/24 |
action_result.data.\*.properties.enableDdosProtection | boolean | | True False |
action_result.data.\*.properties.enableVmProtection | boolean | | True False |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.resourceGuid | string | | 1b6e07c0-a869-4a24-abfe-e93390cd0095 |
action_result.data.\*.properties.subnets.\*.etag | string | | W/"afd6a89a-57fd-4eb4-bcbf-49ee9d377fc5" |
action_result.data.\*.properties.subnets.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/virtualNetworks/myNetworkInterface1/subnets/default |
action_result.data.\*.properties.subnets.\*.name | string | | default |
action_result.data.\*.properties.subnets.\*.properties.addressPrefix | string | | 10.1.0.0/24 |
action_result.data.\*.properties.subnets.\*.properties.ipConfigurations.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/networkInterfaces/testvm133/ipConfigurations/ipconfig1 |
action_result.data.\*.properties.subnets.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.properties.subnets.\*.type | string | | Microsoft.Network/virtualNetworks/subnets |
action_result.data.\*.tags.author | string | | appdev |
action_result.data.\*.type | string | | Microsoft.Network/virtualNetworks |
action_result.summary.num_virtual_networks | numeric | | 3 |
action_result.message | string | | Num virtual networks: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list subnets'

Get the list of subnets

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**virtual_network_name** | required | The name of the virtual network | string | `vm management virtual network` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.virtual_network_name | string | `vm management virtual network` | myNetworkInterface1 |
action_result.data.\*.etag | string | | W/"2290fbd6-434f-410c-a80a-3e66f030cdb2" |
action_result.data.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/myResourceGroup1/providers/Microsoft.Network/virtualNetworks/myNetworkInterface1/subnets/default |
action_result.data.\*.name | string | | default |
action_result.data.\*.properties.addressPrefix | string | | 10.1.0.0/24 |
action_result.data.\*.properties.ipConfigurations.\*.id | string | | /subscriptions/a81fccf8-0405-43ae-990c-ab1389e40c6d/resourceGroups/test/providers/Microsoft.Network/networkInterfaces/unmanagedvm260/ipConfigurations/ipconfig1 |
action_result.data.\*.properties.provisioningState | string | | Succeeded |
action_result.data.\*.type | string | | Microsoft.Network/virtualNetworks/subnets |
action_result.summary.num_subnets | numeric | | 2 |
action_result.message | string | | Num subnets: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ip availability'

Check if a private IP address is available for use

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**virtual_network_name** | required | The name of the virtual network | string | `vm management virtual network` |
**ip_address** | required | The private IP address to be verified | string | `ip` `ipv6` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_address | string | `ip` `ipv6` | 10.1.0.0 |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.virtual_network_name | string | `vm management virtual network` | myNetworkInterface1 |
action_result.data.\*.availableAddress | string | `ip` `ipv6` | 10.1.0.4 |
action_result.summary.available | boolean | | True False |
action_result.summary.num_ips_available | numeric | | 5 |
action_result.message | string | | Available: False, Num ips available: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'generalize vm'

Set the state of the virtual machine to be generalized

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | aGroup |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | abc |
action_result.data | string | | |
action_result.summary.status | string | | Successfully generalized the vm |
action_result.message | string | | Status: Successfully generalized the vm |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'redeploy vm'

Redeploy a virtual machine

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource_group_name | string | `vm management resource group` | myResourceGroup1 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | virtualMachine1 |
action_result.data | string | | |
action_result.summary.status | string | | Successfully redeployed the vm |
action_result.message | string | | Status: Successfully redeployed the vm |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'run command'

Run a command on the virtual machine

Type: **generic** <br>
Read only: **False**

Run a command or a script in an Azure Windows or Linux VM. Refer to <a href='https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/run-command?tabs=HTTP' target='_blank'>API Docs</a> for more information.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource_group_name** | required | The name of the resource group | string | `vm management resource group` |
**vm_name** | required | The name of the virtual machine | string | `vm management virtual machine` |
**command_id** | required | The command to run against the VM | string | `vm management command id` |
**script** | optional | The script to be executed. When this value is given, the given script will override the default script of the command | string | |
**script_parameters** | optional | The run command parameters | string | |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.command_id | string | `vm management command id` | RunShellScript |
action_result.parameter.resource_group_name | string | `vm management resource group` | sample_vm_group |
action_result.parameter.script | string | | echo $arg1 $arg2 |
action_result.parameter.script_parameters | string | | [{"name": "arg1", "value": "hello"},{"name": "arg2", "value": "world" }] |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.parameter.vm_name | string | `vm management virtual machine` | sample_vm |
action_result.data | string | | |
action_result.data.\*.displayStatus | string | | Provisioning succeeded |
action_result.data.\*.results_url | string | `vm management results url` | https://management.azure.com/subscriptions/\<subscription_id>/providers/Microsoft.Compute/locations/<location>/operations/\<operation_id>monitor=true&api-version=2017-03-30 |
action_result.data.results.\*.code | string | | ComponentStatus/StdOut/succeeded ComponentStatus/StdErr/succeeded |
action_result.data.results.\*.level | string | | Info Error Warning |
action_result.data.results.\*.message | string | | |
action_result.summary.status | string | | Successfully executed command |
action_result.message | string | | Status: Successfully executed command |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get results'

Fetch the results of a previously executed run_command action

Type: **investigate** <br>
Read only: **True**

Commands in Azure can take up to 90 minutes to execute. This allows you to retrieve results of previously executed actions. Refer to <a href='https://docs.microsoft.com/en-us/azure/virtual-machines/windows/run-command' target='_blank'>API Docs</a> for more information.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**results_url** | required | URL to fetch result of run command | string | `vm management results url` |
**subscription_id** | optional | Subscription ID to overwrite asset configuration value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.results_url | string | `vm management results url` | https://management.azure.com/subscriptions/\<subscription_id>/providers/Microsoft.Compute/locations/<location>/operations/\<operation_id>monitor=true&api-version=2017-03-30 |
action_result.parameter.subscription_id | string | | 123asd789-2311-4zs1-12ms-180dra85a480 |
action_result.data | string | | |
action_result.data.\*.displayStatus | string | | Provisioning succeeded |
action_result.data.results.\*.code | string | | ComponentStatus/StdOut/succeeded ComponentStatus/StdErr/succeeded |
action_result.data.results.\*.level | string | | Info |
action_result.data.results.\*.message | string | | |
action_result.data.results_url | string | | https://management.azure.com/subscriptions/\<subscription_id>/providers/Microsoft.Compute/locations/<location>/operations/\<operation_id>monitor=true&api-version=2017-03-30 |
action_result.summary.status | string | | Successfully executed command |
action_result.message | string | | Status: Successfully executed command |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
