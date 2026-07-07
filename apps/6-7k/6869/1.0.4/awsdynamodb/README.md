# AWS DynamoDB

Publisher: Splunk <br>
Connector Version: 1.0.4 <br>
Product Vendor: AWS <br>
Product Name: AWS DynamoDB <br>
Minimum Product Version: 5.5.0

This app supports CRUD operations in a AWS DynamoDB database

<div style="margin-left: 2em">

### Expressions in DynamoDB

AWS DynamoDB uses expressions to denote the attributes that you want to read from an item. It also
uses expressions when writing an item to indicate any conditions that must be met, and to indicate
how the attributes are to be updated. Expressions are an integral part of using DynamoDB, and they
are used in a few different ways:

- #### Condition Expressions

  To manipulate data in an AWS DynamoDB table, we use the Put Item, Update Item, and Delete Item
  operations. For these data manipulation operations, we can specify a condition expression to
  determine which items should be modified. If the condition expression evaluates to true, the
  operation succeeds; otherwise, the operation fails.

- #### Update Expressions

  To update an existing item in an AWS DynamoDB table, we use the Update Item operation. We must
  provide the key of the item that we want to update. We must also provide an update expression,
  indicating the attributes that you want to modify and the values that you want to assign to
  them. There are 4 operations update expression supports:

  - [SET](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html#Expressions.UpdateExpressions.SET)
    —modifying or adding item attributes
  - [REMOVE](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html#Expressions.UpdateExpressions.REMOVE)
    —deleting attributes from an item
  - [ADD](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html#Expressions.UpdateExpressions.ADD)
    —updating numbers and sets
  - [DELETE](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.UpdateExpressions.html#Expressions.UpdateExpressions.DELETE)
    —removing elements from a set

- #### Key Condition Expressions

  They are used when querying a table with a composite primary key to limit the items selected.

- #### Filter Expressions

  They allow you to filter the results of queries and scans to allow for more efficient responses.

- #### Projection Expressions

  They are used to specify a subset of attributes you want to receive when reading Items. We used
  these in our GetItem calls in the previous lesson.

The following actions uses expressions

<table>
<colgroup>
<col style="width: 50%" />
<col style="width: 50%" />
</colgroup>
<thead>
<tr class="header">
<th>Expression Name</th>
<th>Action Name</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Condition Expression</td>
<td><ul>
<li>Delete Item</li>
<li>Put Item</li>
</ul></td>
</tr>
<tr class="even">
<td>Update Expression</td>
<td><ul>
<li>Update Item</li>
</ul></td>
</tr>
<tr class="odd">
<td>Key Condition Expression</td>
<td><ul>
<li>Query Data</li>
</ul></td>
</tr>
<tr class="even">
<td>Filter Expression</td>
<td><ul>
<li>Query Data</li>
</ul></td>
</tr>
<tr class="odd">
<td>Projection Expression</td>
<td><ul>
<li>Query Data</li>
</ul></td>
</tr>
</tbody>
</table>

#### Expression attribute names and values

While using this app certain actions will ask for **expression attribute names** and **expression
attribute values** which would be necessary while using expressions. These values are necessary to
pass for the following conditions:

- To access an attribute whose name conflicts with a DynamoDB [reserved
  words](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ReservedWords.html) .
- To create a placeholder for repeating occurrences of an attribute name in an expression.
- To prevent special characters in an attribute name from being misinterpreted in an expression.

#### To write the expression attribute data refer the code snippets given below

**Expression Attribute Names Syntax**

```
        {
          "#variable_key_name" : "actual_key_name"
        }
```

**Expression Attribute Names Example**

```
        {
          "#name":"name",
          "#age" : "age"
        }
```

**Expression Attribute Values Syntax**

```
        {
          ":variable_value_name" : {
            "datatype":"value_to_be_assigned"
          }
        }
```

**Expression Attribute Values Example**

```
        {
          ":name": {
              "S":"Jhon Doe"
          },
          ":age":{
              "N":"22"
          }
        }
```

**Local Secondary Index**

To create a local secondary index(LSI), sort key becomes necessary. The partition key remains the
same as that of the table. If you want to make single local secondary index takes, just pass a JSON
object with the attributes given below and for multiple local secondary indexes pass an array of
JSON objects.(Can only create 5 LSI at max)

- Key name: **sort_key_name**

  Description: Name of the local secondary sort key

  Required: True

  Input Type: String

- Key name: **sort_key_datatype**

  Description: Datatype for the local secondary sort key(accepts only 3 types of values as
  valid,that are **String, Number or Binary** )

  Required: True

  Input Type: String

- Key name: **attribute_projection**

  Description: Type of attribute projection. There are the following types of projections

  - KEYS_ONLY: Only the index and primary keys are projected into the index.
  - INCLUDE: Only the specified table attributes are projected into the index. The list of
    projected attributes is in NonKeyAttributes.
  - ALL: All of the table attributes are projected into the index.

  Required: True

  Input Type: String

- Key name: **non_key_attributes**

  Description: A list of one or more non-key attribute names that are projected into the secondary
  index. (Required only when the projection mode is set to INCLUDE)

  Required: False

  Input Type: Array of string values

VALUE EXAMPLE

- Single JSON object for LSI

  ```
              {
                "sort_key_name": "lsi_one",
                "sort_key_datatype": "String",
                "attribute_projection": "INCLUDE",
                "non_key_attributes": [
                    "one",
                    "two",
                    "three"
                ]
              }
  ```

- Multiple JSON object for LSI

  ```
              [
                {
                    "sort_key_name": "lsi_one",
                    "sort_key_datatype": "String",
                    "attribute_projection": "INCLUDE",
                    "non_key_attributes": [
                        "one",
                        "two",
                        "three"
                    ]
                },
                {
                    "sort_key_name": "lsi_two",
                    "sort_key_datatype": "String",
                    "attribute_projection": "ALL"
                }
              ]
  ```

**Global Secondary Index**

A partition key is required to create a global secondary index(GSI) while a sort key is optional.
All other parameters for Global Secondary Indexes remain the same as those for Local Secondary
Indexes; however partition key name and partition key name datatype are additional required
parameters. Whereas sort key name and sort key datatype are optional parameters. The provisional
read and write capacity units are the same as the original table (can only create 20 GSI at max).

- Key name: **partition_key_name**

  Description: Name of the local secondary sort key

  Required: True

  Input Type: String

- Key name: **partition_key_datatype**

  Description: Datatype for the local secondary sort key (accepts only 3 types of values as valid,
  that are **String, Number or Binary** )

  Required: True

  Input Type: String

- Key name: **sort_key_name**

  Description: Name of the global secondary sort key (required parameter)

  Required: False

  Input Type: String

- Key name: **sort_key_datatype**

  Description: Datatype for the global secondary sort key (accepts only 3 types of values as
  valid, that are **String, Number or Binary** )

  Required: False

  Input Type: String

- Key name: **attribute_projection**

  Description: Type of attribute projection. There are the following types of projections

  - KEYS_ONLY: Only the index and primary keys are projected into the index.
  - INCLUDE: Only the specified table attributes are projected into the index. The list of
    projected attributes is in NonKeyAttributes.
  - ALL: All of the table attributes are projected into the index.

  Required: True

  Input Type: String

- Key name: **non_key_attributes**

  Description: A list of one or more non-key attribute names that are projected into the secondary
  index. (Required only when the projection mode is set to INCLUDE)

  Required: False

  Input Type: Array of string values

VALUE EXAMPLE

- Single JSON object for GSI

  ```
              {
                "partition_key_name": "gsi_id",
                "partition_key_datatype": "Number",
                "sort_key_name": "gsi_one",
                "sort_key_datatype": "String",
                "attribute_projection": "INCLUDE",
                "non_key_attributes": [
                    "one",
                    "two",
                    "three"
                ]
              }
  ```

- Multiple JSON object for GSI

  ```
              [
                {
                    "partition_key_name": "gsi_id",
                    "partition_key_datatype": "Number",
                    "sort_key_name": "gsi_one",
                    "sort_key_datatype": "String",
                    "attribute_projection": "INCLUDE",
                    "non_key_attributes": [
                        "one",
                        "two",
                        "three"
                    ]
                },
                {
                    "partition_key_name": "gsi_name",
                    "partition_key_datatype": "String",
                    "attribute_projection": "ALL"
                }
              ]
  ```

#### Available AWS Regions

| | |
|---------------------------|----------------|
| REGION NAME | REGION |
| US East (Ohio) | us-east-2 |
| US East (N. Virginia) | us-east-1 |
| US West (N. California) | us-west-1 |
| US West (Oregon) | us-west-2 |
| Africa (Cape Town) | af-south-1 |
| Asia Pacific (Hong Kong) | ap-east-1 |
| Asia Pacific (Hyderabad) | ap-south-2 |
| Asia Pacific (Jakarta) | ap-southeast-3 |
| Asia Pacific (Mumbai) | ap-south-1 |
| Asia Pacific (Osaka) | ap-northeast-3 |
| Asia Pacific (Seoul) | ap-northeast-2 |
| Asia Pacific (Singapore) | ap-southeast-1 |
| Asia Pacific (Sydney) | ap-southeast-2 |
| Asia Pacific (Tokyo) | ap-northeast-1 |
| Canada (Central) | ca-central-1 |
| Europe (Frankfurt) | eu-central-1 |
| Europe (Ireland) | eu-west-1 |
| Europe (London) | eu-west-2 |
| Europe (Milan) | eu-south-1 |
| Europe (Paris) | eu-west-3 |
| Europe (Spain) | eu-south-2 |
| Europe (Stockholm) | eu-north-1 |
| Europe (Zurich) | eu-central-2 |
| Middle East (Bahrain) | me-south-1 |
| Middle East (UAE) | me-central-1 |
| South America (São Paulo) | sa-east-1 |
| AWS GovCloud (US-East) | us-gov-east-1 |
| AWS GovCloud (US-West) | us-gov-west-1 |

### Configuration variables

This table lists the configuration variables required to operate AWS DynamoDB. These variables are specified when configuring a AWS DynamoDB asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**access_key** | optional | password | Access Key |
**secret_key** | optional | password | Secret Key |
**region** | required | string | Region |
**use_role** | optional | boolean | Use attached role when running Splunk SOAR in EC2 |

### Supported Actions

[describe global table](#action-describe-global-table) - Fetch metadata of a global table <br>
[describe backup](#action-describe-backup) - Fetch metadata of a backup <br>
[describe table](#action-describe-table) - Fetch metadata of a table <br>
[create global table](#action-create-global-table) - Create a global table from an existing table in the specified regions <br>
[list global tables](#action-list-global-tables) - List the global tables of a specific region <br>
[list backups](#action-list-backups) - List all the backups present in the database <br>
[delete backup](#action-delete-backup) - Delete backup of a table <br>
[create backup](#action-create-backup) - Create a backup of an existing table <br>
[restore backup table](#action-restore-backup-table) - Create a new table from an existing backup <br>
[list tables](#action-list-tables) - List all the tables present in the database <br>
[delete table](#action-delete-table) - Delete a table from the database <br>
[create table](#action-create-table) - Create a table in the database <br>
[delete item](#action-delete-item) - Delete an item from the table <br>
[put item](#action-put-item) - Add an item to the table <br>
[update item](#action-update-item) - Update an item in the table <br>
[get item](#action-get-item) - Get an item from the table <br>
[query data](#action-query-data) - Query data from database <br>
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied configuration

## action: 'describe global table'

Fetch metadata of a global table

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**global_table_name** | required | Name of Global Table to describe | string | `aws dynamodb table name` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.global_table_name | string | `aws dynamodb table name` | room |
action_result.data.\*.GlobalTableDescription.CreationDateTime | string | | 2023-02-16 10:15:08.116000+00:00 |
action_result.data.\*.GlobalTableDescription.GlobalTableArn | string | | arn:aws:dynamodb::157568067690:global-table/test_playbook |
action_result.data.\*.GlobalTableDescription.GlobalTableName | string | | test_playbook |
action_result.data.\*.GlobalTableDescription.GlobalTableStatus | string | | ACTIVE |
action_result.data.\*.GlobalTableDescription.ReplicationGroup.\*.RegionName | string | `aws region` | us-east-1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 252 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 16 Feb 2023 10:15:09 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 3053811167 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | IVODR6MSFJFABNQ92LLHFE1BVJVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | IVODR6MSFJFABNQ92LLHFE1BVJVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | |
action_result.summary | string | | |
action_result.message | string | | Global table details fetched successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe backup'

Fetch metadata of a backup

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**backup_arn** | required | Backup ARN of backup to describe | string | `aws dynamodb backup arn` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.backup_arn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook/backup/01676542512426-8ea20723 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.data.\*.BackupDescription.BackupDetails.BackupArn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook/backup/01676542512426-8ea20723 |
action_result.data.\*.BackupDescription.BackupDetails.BackupCreationDateTime | string | | 2023-02-16 10:15:12.426000+00:00 |
action_result.data.\*.BackupDescription.BackupDetails.BackupName | string | | test_playbook_backup |
action_result.data.\*.BackupDescription.BackupDetails.BackupSizeBytes | numeric | | |
action_result.data.\*.BackupDescription.BackupDetails.BackupStatus | string | | AVAILABLE |
action_result.data.\*.BackupDescription.BackupDetails.BackupType | string | `aws dynamodb backup type` | USER |
action_result.data.\*.BackupDescription.SourceTableDetails.BillingMode | string | `aws dynamodb billing mode` | PROVISIONED |
action_result.data.\*.BackupDescription.SourceTableDetails.ItemCount | numeric | | |
action_result.data.\*.BackupDescription.SourceTableDetails.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | test_part_key |
action_result.data.\*.BackupDescription.SourceTableDetails.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.BackupDescription.SourceTableDetails.ProvisionedThroughput.ReadCapacityUnits | numeric | `aws dynamodb read capacity` | 3 |
action_result.data.\*.BackupDescription.SourceTableDetails.ProvisionedThroughput.WriteCapacityUnits | numeric | `aws dynamodb write capacity` | 3 |
action_result.data.\*.BackupDescription.SourceTableDetails.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook |
action_result.data.\*.BackupDescription.SourceTableDetails.TableCreationDateTime | string | | 2023-02-16 10:13:02.238000+00:00 |
action_result.data.\*.BackupDescription.SourceTableDetails.TableId | string | | 291c7a8f-8c39-4727-8ab6-4a078eca09ce |
action_result.data.\*.BackupDescription.SourceTableDetails.TableName | string | `aws dynamodb table name` | test_playbook |
action_result.data.\*.BackupDescription.SourceTableDetails.TableSizeBytes | numeric | | |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.IndexName | string | | gsi_part1-gsi_sort1-index |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | gsi_part1 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.ProvisionedThroughput.ReadCapacityUnits | numeric | `aws dynamodb read capacity` | 3 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.ProvisionedThroughput.WriteCapacityUnits | numeric | `aws dynamodb write capacity` | 3 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.IndexName | string | | lsi_sort1-index |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | test_part_key |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.SSEDescription.KMSMasterKeyArn | string | `aws dynamodb kms master key id` | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.SSEDescription.SSEType | string | | KMS |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.SSEDescription.Status | string | | ENABLED |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.StreamDescription.StreamEnabled | boolean | | True False |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.StreamDescription.StreamViewType | string | `aws dynamodb stream view type` | NEW_AND_OLD_IMAGES |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 2043 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 16 Feb 2023 10:15:13 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 3983538543 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | M2M76PL4BOD12BK61IEUN1604VVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | M2M76PL4BOD12BK61IEUN1604VVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | |
action_result.data.\*.Table | string | | |
action_result.data.\*.Table.TableName | string | | |
action_result.summary | string | | |
action_result.message | string | | Backup details fetched successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe table'

Fetch metadata of a table

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of the table to describe | string | `aws dynamodb table name` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.table_name | string | `aws dynamodb table name` | test_playbook_backup |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 2813 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 16 Feb 2023 10:20:13 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 3323931213 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | IVOH9V6BK0B7Q85I411VMKI4T7VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | IVOH9V6BK0B7Q85I411VMKI4T7VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | |
action_result.data.\*.Table.AttributeDefinitions.\*.AttributeName | string | | gsi_part1 |
action_result.data.\*.Table.AttributeDefinitions.\*.AttributeType | string | | N |
action_result.data.\*.Table.CreationDateTime | string | | 2023-02-16 10:15:15.823000+00:00 |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.IndexArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook_backup/index/gsi_part2-index |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.IndexName | string | | gsi_part2-index |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.IndexSizeBytes | numeric | | |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.IndexStatus | string | | ACTIVE |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.ItemCount | numeric | | |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | | gsi_part2 |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.Projection.ProjectionType | string | | ALL |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.ProvisionedThroughput.LastDecreaseDateTime | string | | 2023-02-16 10:18:06.128000+00:00 |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 1 |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.ProvisionedThroughput.ReadCapacityUnits | numeric | | 3 |
action_result.data.\*.Table.GlobalSecondaryIndexes.\*.ProvisionedThroughput.WriteCapacityUnits | numeric | | 3 |
action_result.data.\*.Table.ItemCount | numeric | | |
action_result.data.\*.Table.KeySchema.\*.AttributeName | string | | test_part_key |
action_result.data.\*.Table.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.Table.LatestStreamArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook/stream/2023-02-16T10:13:02.238 |
action_result.data.\*.Table.LatestStreamLabel | string | | 2023-02-16T10:13:02.238 |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.IndexArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook_backup/index/lsi_sort1-index |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.IndexName | string | | lsi_sort1-index |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.IndexSizeBytes | numeric | | |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.ItemCount | numeric | | |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | | test_part_key |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.Table.LocalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.Table.ProvisionedThroughput.LastDecreaseDateTime | string | | 2023-02-16 10:17:58.707000+00:00 |
action_result.data.\*.Table.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 1 |
action_result.data.\*.Table.ProvisionedThroughput.ReadCapacityUnits | numeric | | 3 |
action_result.data.\*.Table.ProvisionedThroughput.WriteCapacityUnits | numeric | | 3 |
action_result.data.\*.Table.SSEDescription.KMSMasterKeyArn | string | | arn:aws:kms:us-east-1:157568067690:key/mrk-82136a96ac4241b2afbe568dfe5d11d6 |
action_result.data.\*.Table.SSEDescription.SSEType | string | | KMS |
action_result.data.\*.Table.SSEDescription.Status | string | | ENABLED |
action_result.data.\*.Table.StreamSpecification.StreamEnabled | boolean | | True False |
action_result.data.\*.Table.StreamSpecification.StreamViewType | string | `aws dynamodb stream view type` | NEW_AND_OLD_IMAGES |
action_result.data.\*.Table.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook_backup |
action_result.data.\*.Table.TableId | string | | 44b4bcbc-b591-466f-a05d-370d7df1561b |
action_result.data.\*.Table.TableName | string | | test_playbook_backup |
action_result.data.\*.Table.TableSizeBytes | numeric | | |
action_result.data.\*.Table.TableStatus | string | | ACTIVE |
action_result.summary | string | | |
action_result.message | string | | Table details fetched successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create global table'

Create a global table from an existing table in the specified regions

Type: **generic** <br>
Read only: **False**

<ul><li><p>Conditions to create a global table : </p><ul><li>The table must have the same name as all of the other replicas</li><li>The table must have DynamoDB Streams enabled, with the stream containing both the new and the old images of the item.</li></ul></li><li><p>If you want to add a new replica table to a global table, each of the following conditions must be true:</p><ul><li>The table must have the same primary key as all of the other replicas.</li><li>The table must have the same name as all of the other replicas.</li><li>The table must have DynamoDB Streams enabled, with the stream containing both the new and the old images of the item.</li><li>None of the replica tables in the global table can contain any data.</li></ul></li><li><p>If global secondary indexes are specified, then the following conditions must also be met:</p><ul><li>The global secondary indexes must have the same name.</li><li>The global secondary indexes must have the same hash key and sort key (if present).</li></ul></li><li><p>If local secondary indexes are specified, then the following conditions must also be met:</p><ul><li>The local secondary indexes must have the same name.</li><li>The local secondary indexes must have the same hash key and sort key (if present).</li></ul></li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**global_table_name** | required | Name of table to make global | string | `aws dynamodb table name` |
**replication_group** | required | Name of region to create global table (accepts comma separated regions) | string | `aws region` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.global_table_name | string | `aws dynamodb table name` | room |
action_result.parameter.replication_group | string | `aws region` | us-east-1 |
action_result.data | string | | |
action_result.data.\*.GlobalTableDescription.CreationDateTime | string | | 2022-09-22 11:50:25.594000+00:00 |
action_result.data.\*.GlobalTableDescription.GlobalTableArn | string | | arn:aws:dynamodb::157568067690:global-table/room |
action_result.data.\*.GlobalTableDescription.GlobalTableName | string | | room |
action_result.data.\*.GlobalTableDescription.GlobalTableStatus | string | | CREATING |
action_result.data.\*.GlobalTableDescription.ReplicationGroup.\*.RegionName | string | | us-east-1 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 236 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 11:50:25 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 1081780290 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | C0FE292C187QISI6FGDGARBR7FVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | C0FE292C187QISI6FGDGARBR7FVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Created global table successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list global tables'

List the global tables of a specific region

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**exclusive_start_global_table_name** | optional | List global tables after specific given global table name | string | `aws dynamodb table name` |
**region_name** | optional | List the global tables of a given region | string | `aws region` |
**max_items** | optional | Maximum number of tables to fetch | numeric | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.exclusive_start_global_table_name | string | `aws dynamodb table name` | cars_backup |
action_result.parameter.max_items | numeric | | 3 |
action_result.parameter.region_name | string | `aws region` | us-east-1 |
action_result.data.\*.GlobalTables.\*.GlobalTableName | string | `aws dynamodb table name` | cars |
action_result.data.\*.GlobalTables.\*.ReplicationGroup.\*.RegionName | string | `aws region` | us-east-2 |
action_result.data.\*.LastEvaluatedGlobalTableName | string | | fruits |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 224 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 05:53:30 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 2321728776 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | RP572T69FGKGL2E8RI23932NPNVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | RP572T69FGKGL2E8RI23932NPNVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Fetched global table list successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list backups'

List all the backups present in the database

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**backup_type** | optional | Type of backup to list | string | `aws dynamodb backup type` |
**exclusive_start_backup_arn** | optional | List backups after specific given backup arn | string | `aws dynamodb backup arn` |
**max_items** | optional | Maximum number of backups to fetch | numeric | |
**table_name** | optional | List backups of specific table | string | `aws dynamodb table name` |
**start_date** | optional | List backups created after provided date.(Valid date format allowed: YYYY/MM/DD) | string | |
**end_date** | optional | List backups created before provided data.(Valid date format allowed: YYYY/MM/DD) | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.backup_type | string | `aws dynamodb backup type` | USER |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.end_date | string | | 2022-09-22 11:30:03.118000+00:00 |
action_result.parameter.exclusive_start_backup_arn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/cars/backup/01663158543903-413ed1de |
action_result.parameter.max_items | numeric | | 2 |
action_result.parameter.start_date | string | | 2022-09-22 11:30:03.118000+00:00 |
action_result.parameter.table_name | string | `aws dynamodb table name` | cars |
action_result.data.\*.BackupSummaries.\*.BackupArn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/test_dev_table/backup/01659614741851-9435638e |
action_result.data.\*.BackupSummaries.\*.BackupCreationDateTime | string | | 2022-08-04 12:05:41.851000+00:00 |
action_result.data.\*.BackupSummaries.\*.BackupExpiryDateTime | string | | 2022-09-22 11:30:03.118000+00:00 |
action_result.data.\*.BackupSummaries.\*.BackupName | string | | newDevTableBackup |
action_result.data.\*.BackupSummaries.\*.BackupSizeBytes | numeric | | 182 |
action_result.data.\*.BackupSummaries.\*.BackupStatus | string | | AVAILABLE |
action_result.data.\*.BackupSummaries.\*.BackupType | string | `aws dynamodb backup type` | USER |
action_result.data.\*.BackupSummaries.\*.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_dev_table |
action_result.data.\*.BackupSummaries.\*.TableId | string | | c08213e2-7a1b-4c44-abaa-bf3a52092232 |
action_result.data.\*.BackupSummaries.\*.TableName | string | `aws dynamodb table name` | test_dev_table |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 1570 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Wed, 14 Sep 2022 12:24:04 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 4139981727 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | AME57LA4RM4QDPVM614J1QTMI3VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | AME57LA4RM4QDPVM614J1QTMI3VV4KQNSO5AEMVJF66Q9ASUAAJG 6Q42SMS0AFKKI1K8PR67FNVU87VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Fetched list of backups successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete backup'

Delete backup of a table

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**backup_arn** | required | ARN associated with the backup to delete | string | `aws dynamodb backup arn` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.backup_arn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/test_dev_table/backup/01663824550617-bcee6561 |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.data.\*.BackupDescription.BackupDetails.BackupArn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/cars/backup/01663158543903-413ed1de |
action_result.data.\*.BackupDescription.BackupDetails.BackupCreationDateTime | string | | 2022-09-14 12:29:03.903000+00:00 |
action_result.data.\*.BackupDescription.BackupDetails.BackupExpiryDateTime | string | | 2022-09-22 11:30:03.118000+00:00 |
action_result.data.\*.BackupDescription.BackupDetails.BackupName | string | | cars_backup |
action_result.data.\*.BackupDescription.BackupDetails.BackupSizeBytes | numeric | | 266 |
action_result.data.\*.BackupDescription.BackupDetails.BackupStatus | string | | DELETED |
action_result.data.\*.BackupDescription.BackupDetails.BackupType | string | `aws dynamodb backup type` | USER |
action_result.data.\*.BackupDescription.SourceTableDetails.BillingMode | string | | PROVISIONED |
action_result.data.\*.BackupDescription.SourceTableDetails.ItemCount | numeric | | 3 |
action_result.data.\*.BackupDescription.SourceTableDetails.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | VID |
action_result.data.\*.BackupDescription.SourceTableDetails.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.BackupDescription.SourceTableDetails.ProvisionedThroughput.ReadCapacityUnits | numeric | | 1 |
action_result.data.\*.BackupDescription.SourceTableDetails.ProvisionedThroughput.WriteCapacityUnits | numeric | | 1 |
action_result.data.\*.BackupDescription.SourceTableDetails.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/cars |
action_result.data.\*.BackupDescription.SourceTableDetails.TableCreationDateTime | string | | 2022-07-29 12:44:24.597000+00:00 |
action_result.data.\*.BackupDescription.SourceTableDetails.TableId | string | | 0fa008bb-5e6d-4287-949e-9872a952927f |
action_result.data.\*.BackupDescription.SourceTableDetails.TableName | string | `aws dynamodb table name` | cars |
action_result.data.\*.BackupDescription.SourceTableDetails.TableSizeBytes | numeric | | 266 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.IndexName | string | | gsi_part1-gsi_sort1-index |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | | gsi_part1 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.ProvisionedThroughput.ReadCapacityUnits | numeric | | 3 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.GlobalSecondaryIndexes.\*.ProvisionedThroughput.WriteCapacityUnits | numeric | | 3 |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.IndexName | string | | lsi_sort1-index |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | | test_part_key |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.LocalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.SSEDescription.KMSMasterKeyArn | string | | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.SSEDescription.SSEType | string | | KMS |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.SSEDescription.Status | string | | ENABLED |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.StreamDescription.StreamEnabled | boolean | | True |
action_result.data.\*.BackupDescription.SourceTableFeatureDetails.StreamDescription.StreamViewType | string | `aws dynamodb stream view type` | NEW_AND_OLD_IMAGES |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 769 810 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Wed, 14 Sep 2022 12:29:44 GMT Thu, 22 Sep 2022 10:45:17 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 408729803 2968903155 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | HTKF2F7HA47UIUFP1V5TS6MFJBVV4KQNSO5AEMVJF66Q9ASUAAJG UNOSU88UQ1G3AOQEJHGVV5IJDBVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | HTKF2F7HA47UIUFP1V5TS6MFJBVV4KQNSO5AEMVJF66Q9ASUAAJG UNOSU88UQ1G3AOQEJHGVV5IJDBVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Deleted backup successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create backup'

Create a backup of an existing table

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of the table to backup | string | `aws dynamodb table name` |
**backup_name** | required | Name of the backup | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.backup_name | string | | newtable123-backup |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.table_name | string | `aws dynamodb table name` | newtable123 |
action_result.data.\*.BackupDetails.BackupArn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/cars/backup/01663158543903-413ed1de |
action_result.data.\*.BackupDetails.BackupCreationDateTime | string | | 2022-09-14 12:29:03.903000+00:00 |
action_result.data.\*.BackupDetails.BackupExpiryDateTime | string | | 2022-09-22 11:30:03.118000+00:00 |
action_result.data.\*.BackupDetails.BackupName | string | | cars_backup |
action_result.data.\*.BackupDetails.BackupSizeBytes | numeric | | 266 |
action_result.data.\*.BackupDetails.BackupStatus | string | | CREATING |
action_result.data.\*.BackupDetails.BackupType | string | `aws dynamodb backup type` | USER |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 252 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Wed, 14 Sep 2022 12:29:03 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 1789868498 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | K109PP9CK2RGFK6BV1HDE87C5JVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | K109PP9CK2RGFK6BV1HDE87C5JVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Created backup successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'restore backup table'

Create a new table from an existing backup

Type: **generic** <br>
Read only: **False**

<p> <strong>Restore Secondary Indexes</strong><p>The Restore Secondary Indexes parameter is used to restore the secondary indexes of the newly restored table. These are following two options for the parameter:<ul><li><strong>Restore the entire table</strong><p>Restores table with original indexes as saved in the backup</p></li><li> <strong> Restore the table without secondary indexes </strong> (Selected by Default) <p> Restores table without any indexes. There will be no Local and Global Secondary Indexes. You can only create Global Secondary Indexes. Local Secondary Indexes cannot be created once the table is created after the table is created. </p></li></ul></p></p><p> <strong>NOTE</strong><p> If while restoring table <strong>Restore the table without secondary indexes </strong> option is selected then there will be no Local Secondary Indexes. </p></p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of the table to restore | string | `aws dynamodb table name` |
**backup_arn** | required | Amazon Resource Name (ARN) associated with the backup | string | `aws dynamodb backup arn` |
**billing_mode_override** | optional | Billing mode of the restored table | string | `aws dynamodb billing mode` |
**read_capacity_override** | optional | Read capacity override (for PROVISIONED billing mode) | numeric | `aws dynamodb read capacity` |
**write_capacity_override** | optional | Write capacity override (for PROVISIONED billing mode) | numeric | `aws dynamodb write capacity` |
**restore_secondary_indexes** | required | Restore secondary indexes | string | |
**sse_enable_override** | optional | Server-side encryption(SSE) setting | string | |
**kms_master_key_id** | optional | Key to use for the AWS KMS encryption (Used when SSE is enabled) | string | `aws dynamodb kms master key id` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.backup_arn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/newtable123/backup/01663846203118-f405802d |
action_result.parameter.billing_mode_override | string | `aws dynamodb billing mode` | PROVISIONED |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.kms_master_key_id | string | `aws dynamodb kms master key id` | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.parameter.read_capacity_override | numeric | `aws dynamodb read capacity` | 4 |
action_result.parameter.restore_secondary_indexes | string | | Restore the entire table |
action_result.parameter.sse_enable_override | string | | True |
action_result.parameter.table_name | string | `aws dynamodb table name` | retorenewtable123 |
action_result.parameter.write_capacity_override | numeric | `aws dynamodb write capacity` | 4 |
action_result.data | string | | |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 1995 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 11:43:36 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 4165026467 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | D1PGDOFSG8MPUAOL4TM2NN7TR7VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | D1PGDOFSG8MPUAOL4TM2NN7TR7VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.TableDescription.AttributeDefinitions.\*.AttributeName | string | `aws dynamodb attribute name` | newname |
action_result.data.\*.TableDescription.AttributeDefinitions.\*.AttributeType | string | `aws dynamodb attribute datatype` | S |
action_result.data.\*.TableDescription.BillingModeSummary.BillingMode | string | | PROVISIONED |
action_result.data.\*.TableDescription.CreationDateTime | string | | 2022-09-22 11:43:36.491000+00:00 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/retorenewtable123/index/newid-newname-index |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexName | string | | newid-newname-index |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | newid |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.Projection.NonKeyAttributes | string | | num1 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 0 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ProvisionedThroughput.ReadCapacityUnits | numeric | `aws dynamodb read capacity` | 4 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ProvisionedThroughput.WriteCapacityUnits | numeric | `aws dynamodb write capacity` | 4 |
action_result.data.\*.TableDescription.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | ID |
action_result.data.\*.TableDescription.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.IndexArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/retorenewtable123/index/testdatast-index |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.IndexName | string | | testdatast-index |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.IndexSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | ID |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.Projection.ProjectionType | string | | ALL |
action_result.data.\*.TableDescription.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 0 |
action_result.data.\*.TableDescription.ProvisionedThroughput.ReadCapacityUnits | numeric | `aws dynamodb read capacity` | 4 |
action_result.data.\*.TableDescription.ProvisionedThroughput.WriteCapacityUnits | numeric | `aws dynamodb write capacity` | 4 |
action_result.data.\*.TableDescription.RestoreSummary.RestoreDateTime | string | | 2022-09-22 11:30:03.118000+00:00 |
action_result.data.\*.TableDescription.RestoreSummary.RestoreInProgress | boolean | | True |
action_result.data.\*.TableDescription.RestoreSummary.SourceBackupArn | string | `aws dynamodb backup arn` | arn:aws:dynamodb:us-east-1:157568067690:table/newtable123/backup/01663846203118-f405802d |
action_result.data.\*.TableDescription.RestoreSummary.SourceTableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/newtable123 |
action_result.data.\*.TableDescription.SSEDescription.KMSMasterKeyArn | string | `aws dynamodb kms master key id` | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.data.\*.TableDescription.SSEDescription.SSEType | string | | KMS |
action_result.data.\*.TableDescription.SSEDescription.Status | string | | ENABLED |
action_result.data.\*.TableDescription.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/retorenewtable123 |
action_result.data.\*.TableDescription.TableId | string | | 67ede490-028f-40ca-b286-2e320f2295c4 |
action_result.data.\*.TableDescription.TableName | string | `aws dynamodb table name` | retorenewtable123 |
action_result.data.\*.TableDescription.TableSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.TableStatus | string | | CREATING |
action_result.summary | string | | |
action_result.message | string | | Restored table from backup successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list tables'

List all the tables present in the database

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_items** | optional | Maximum number of tables to fetch | numeric | |
**exclusive_start_table_name** | optional | List table after specific given table name | string | `aws dynamodb table name` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.exclusive_start_table_name | string | `aws dynamodb table name` | cars2 |
action_result.parameter.max_items | numeric | | 5 |
action_result.data | string | | |
action_result.data.\*.TableNames | string | `aws dynamodb table name` | room_test_1 |
action_result.summary | string | | |
action_result.message | string | | Fetched list of table successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete table'

Delete a table from the database

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of table to delete | string | `aws dynamodb table name` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.table_name | string | `aws dynamodb table name` | testdata |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 310 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Wed, 21 Sep 2022 18:29:19 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 3710880937 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | KMO2UQHBJ1L4DL15K1RN4HVGD7VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | KMO2UQHBJ1L4DL15K1RN4HVGD7VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.TableDescription.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.LatestStreamArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook/stream/2023-02-16T10:13:02.238 |
action_result.data.\*.TableDescription.LatestStreamLabel | string | | 2023-02-16T10:13:02.238 |
action_result.data.\*.TableDescription.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 0 |
action_result.data.\*.TableDescription.ProvisionedThroughput.ReadCapacityUnits | numeric | | 5 |
action_result.data.\*.TableDescription.ProvisionedThroughput.WriteCapacityUnits | numeric | | 5 |
action_result.data.\*.TableDescription.SSEDescription.KMSMasterKeyArn | string | | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.data.\*.TableDescription.SSEDescription.SSEType | string | | KMS |
action_result.data.\*.TableDescription.SSEDescription.Status | string | | ENABLED |
action_result.data.\*.TableDescription.StreamSpecification.StreamEnabled | boolean | | True False |
action_result.data.\*.TableDescription.StreamSpecification.StreamViewType | string | `aws dynamodb stream view type` | NEW_AND_OLD_IMAGES |
action_result.data.\*.TableDescription.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/testdata |
action_result.data.\*.TableDescription.TableId | string | | 78197d82-7d17-49ad-b622-fb5a619832dd |
action_result.data.\*.TableDescription.TableName | string | | testdata |
action_result.data.\*.TableDescription.TableSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.TableStatus | string | | DELETING |
action_result.data.\*.TableNames | string | | |
action_result.summary | string | | |
action_result.message | string | | Deleted Table Successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create table'

Create a table in the database

Type: **generic** <br>
Read only: **False**

<ul> <li> <strong> Partition and Sort Key </strong> <div> <p> Each table has a Primary Key to identify items uniquely. The Primary Key in DynamoDB is made up of a Partition Key and a Sort Key. The Sort Key is optional, but once the table is created you cannot add/update the Sort Key. </p> <p> All Partition and Sort Keys in Dynamodb have only three supported datatypes: String, Number and Binary</p> </div> </li> <li> <strong> Billing Mode </strong> <div> <p>The Billing mode defines how you will be charged for read and write throughput and how capacity is managed. This setting can be changed later.</p> <p>Billing Mode has two values, by default it will be set to <strong>PROVISIONED</strong>.</p> <ul> <li>PROVISIONED: Sets the billing mode to Provisioned Mode</li> <li>PAY PER REQUEST: Sets the billing mode to On-Demand Mode</li> </ul> <p> When the billing mode is Provisioned, read and write capacity become required parameters. The values for read and write capacity units are set to 5 by default. Also, auto-scaling is disabled. </p> </div> </li> <li> <strong> Secondary Indexes </strong> <div> <p> For creating Local Secondary Indexes (LSI) and Global Secondary Indexes (GSI), please refer the documentation above. </p> <p> Once a table is created, Local Secondary Indexes cannot be added/updated, but Global Secondary Indexes can be created. </p> </div> </li> <li> <strong> Enable Stream </strong> <div> <p> A DynamoDB stream is an ordered flow of information about changes to items in a DynamoDB table. When you enable a stream on a table, DynamoDB captures information about every modification to data items in the table. To enable streams for table, set enable_stream to true. </p> <p>If streams are enabled you need to select a stream view type. There are four options you could select from: </p> <ul> <li> KEYS ONLY: Only the key attributes of the modified item are written to the stream. </li> <li> NEW IMAGE: The entire item, as it appears after it was modified, is written to the stream. </li> <li> OLD IMAGE: The entire item, as it appeared before it was modified, is written to the stream. </li> <li> NEW AND OLD IMAGES: Both the new and the old item images of the item are written to the stream. </li> </ul> </div> </li> <li> <strong>SSE</strong> <div> <p> To use the SSE set the SSE to true. </p> <p>If enabled (true), server-side encryption type is set to KMS and an Amazon Web Services managed key is used (KMS charges apply). If disabled (false) or not specified, server-side encryption is set to Amazon Web Services owned key.</p><p>If SSE is enable and KMS master key is provided, then that key will be used for encryption.</p> </div> </li> <li> <strong>KMS Master Key</strong> <p> The KMS key that should be used for the KMS encryption. To specify a key, use its key ID, Amazon Resource Name (ARN), alias name, or alias ARN. Note that you should only provide this parameter if the key is different from the default DynamoDB key alias/aws/dynamodb </p> </li> <li> <strong>Tags</strong> <div> <p> To add tags to your table, follow the steps given below: </p> <ul> <li> For single-value tags, pass a JSON object. The JSON object should contain the "Key" and "Value" keys, which are both required. <p> { "Key" : "key_data", "Value" : "value_data" } </p> </li> <li> For multiple values in tags, pass a list of JSON object. <p> [ { "Key" : "key_data1", "Value" : "value_data1" }, { "Key" : "key_data2", "Value" : "value_data2" } ] </p> </li> </ul> </div> </li> </ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of table to be created | string | `aws dynamodb table name` |
**billing_mode** | optional | Billing mode to be used for table | string | `aws dynamodb billing mode` |
**partition_key_name** | required | Name of partition key of table | string | `aws dynamodb partition key name` `aws dynamodb attribute name` |
**partition_key_datatype** | required | Datatype of partition key of table | string | |
**sort_key_name** | optional | Name of sort key of table | string | `aws dynamodb sort key name` `aws dynamodb attribute name` |
**sort_key_datatype** | optional | Datatype of sort key of table | string | |
**read_capacity_units** | optional | Read capacity units for provisioned mode | numeric | `aws dynamodb read capacity` |
**write_capacity_units** | optional | Write capacity units for provisioned mode | numeric | `aws dynamodb write capacity` |
**local_secondary_index** | optional | JSON input for creating local secondary index | string | |
**global_secondary_index** | optional | JSON input for creating global secondary index | string | |
**enable_stream** | optional | Enable DynamoDB streams for the table | boolean | |
**stream_view_type** | optional | View type of DynamoDB streams | string | `aws dynamodb stream view type` |
**sse** | required | Settings used to enable server-side encryption | string | |
**kms_master_key_id** | optional | The KMS key that should be used for the KMS encryption | string | `aws dynamodb kms master key id` |
**tags** | optional | JSON list of tags to add to table | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.billing_mode | string | `aws dynamodb billing mode` | PROVISIONED |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.enable_stream | boolean | | True |
action_result.parameter.global_secondary_index | string | | {<br> "attribute_projection": "INCLUDE",<br> "partition_key_name": "newid",<br> "partition_key_datatype": "string",<br> "sort_key_name": "newname",<br> "sort_key_datatype": "string",<br> "NonKeyAttributes": ["num1","num2"]<br>} |
action_result.parameter.kms_master_key_id | string | `aws dynamodb kms master key id` | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.parameter.local_secondary_index | string | | {"attribute_projection": "ALL",<br> "sort_key_name": "testdatast",<br> "sort_key_datatype": "string"} |
action_result.parameter.partition_key_datatype | string | | Number |
action_result.parameter.partition_key_name | string | `aws dynamodb partition key name` `aws dynamodb attribute name` | ID |
action_result.parameter.read_capacity_units | numeric | `aws dynamodb read capacity` | 4 |
action_result.parameter.sort_key_datatype | string | | String |
action_result.parameter.sort_key_name | string | `aws dynamodb sort key name` `aws dynamodb attribute name` | name |
action_result.parameter.sse | string | | False |
action_result.parameter.stream_view_type | string | `aws dynamodb stream view type` | NEW_IMAGE |
action_result.parameter.table_name | string | `aws dynamodb table name` | newtable123 |
action_result.parameter.tags | string | | events |
action_result.parameter.write_capacity_units | numeric | `aws dynamodb write capacity` | 4 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 1680 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 06:07:34 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 2160627733 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | J0GO5QSIRQPP2O7RAMOAHO1MKVVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | J0GO5QSIRQPP2O7RAMOAHO1MKVVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.TableDescription | string | | |
action_result.data.\*.TableDescription.AttributeDefinitions.\*.AttributeName | string | `aws dynamodb attribute name` | ID |
action_result.data.\*.TableDescription.AttributeDefinitions.\*.AttributeType | string | | N |
action_result.data.\*.TableDescription.CreationDateTime | string | | 2022-09-22 06:07:34.858000+00:00 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/newtable123/index/newid-newname-index |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexName | string | `aws dynamodb index name` | newid-newname-index |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.IndexStatus | string | | CREATING |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | newid |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.Projection.NonKeyAttributes | string | | num1 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.Projection.ProjectionType | string | | INCLUDE |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 0 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ProvisionedThroughput.ReadCapacityUnits | numeric | `aws dynamodb read capacity` | 4 |
action_result.data.\*.TableDescription.GlobalSecondaryIndexes.\*.ProvisionedThroughput.WriteCapacityUnits | numeric | `aws dynamodb write capacity` | 4 |
action_result.data.\*.TableDescription.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | ID |
action_result.data.\*.TableDescription.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.TableDescription.LatestStreamArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/test_playbook/stream/2023-02-16T10:13:02.238 |
action_result.data.\*.TableDescription.LatestStreamLabel | string | | 2023-02-16T10:13:02.238 |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.IndexArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/newtable123/index/testdatast-index |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.IndexName | string | | testdatast-index |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.IndexSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.ItemCount | numeric | | 0 |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.KeySchema.\*.AttributeName | string | `aws dynamodb attribute name` | ID |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.KeySchema.\*.KeyType | string | | HASH |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.Projection.NonKeyAttributes | string | | test_attr |
action_result.data.\*.TableDescription.LocalSecondaryIndexes.\*.Projection.ProjectionType | string | | ALL |
action_result.data.\*.TableDescription.ProvisionedThroughput.NumberOfDecreasesToday | numeric | | 0 |
action_result.data.\*.TableDescription.ProvisionedThroughput.ReadCapacityUnits | numeric | `aws dynamodb read capacity` | 4 |
action_result.data.\*.TableDescription.ProvisionedThroughput.WriteCapacityUnits | numeric | `aws dynamodb write capacity` | 4 |
action_result.data.\*.TableDescription.SSEDescription.KMSMasterKeyArn | string | `aws dynamodb kms master key id` | arn:aws:kms:us-east-1:157568067690:key/1651022c-3833-4ab4-a782-df260339eb0c |
action_result.data.\*.TableDescription.SSEDescription.SSEType | string | | KMS |
action_result.data.\*.TableDescription.SSEDescription.Status | string | | ENABLED |
action_result.data.\*.TableDescription.StreamSpecification.StreamEnabled | boolean | | True False |
action_result.data.\*.TableDescription.StreamSpecification.StreamViewType | string | `aws dynamodb stream view type` | NEW_AND_OLD_IMAGES |
action_result.data.\*.TableDescription.TableArn | string | | arn:aws:dynamodb:us-east-1:157568067690:table/newtable123 |
action_result.data.\*.TableDescription.TableId | string | | f250b7a4-20e6-49cd-afed-20de7a883fef |
action_result.data.\*.TableDescription.TableName | string | `aws dynamodb table name` | newtable123 |
action_result.data.\*.TableDescription.TableSizeBytes | numeric | | 0 |
action_result.data.\*.TableDescription.TableStatus | string | | CREATING |
action_result.summary | string | | |
action_result.message | string | | Created Table successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete item'

Delete an item from the table

Type: **generic** <br>
Read only: **False**

Please refer app documentation to use the expression parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Table name to delete item from | string | `aws dynamodb table name` |
**condition_expression** | optional | Condition to be checked before deleting an item | string | |
**partition_key_name** | required | Name of partition key of table | string | `aws dynamodb partition key name` `aws dynamodb attribute name` |
**sort_key_name** | optional | Name of sort key of table | string | `aws dynamodb sort key name` `aws dynamodb attribute name` |
**partition_key_value** | required | Partition key value of item to delete | string | |
**sort_key_value** | optional | Sort key value of item to delete | string | |
**partition_key_datatype** | required | Datatype of partition key of table | string | |
**sort_key_datatype** | optional | Datatype of sort key of table | string | |
**expression_attribute_names** | optional | Attribute names json | string | |
**expression_attribute_values** | optional | Attribute values json | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.condition_expression | string | | #age \<> :age |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.expression_attribute_names | string | | {"#age":"age"} |
action_result.parameter.expression_attribute_values | string | | {":age":{"N":"12"}} |
action_result.parameter.partition_key_datatype | string | | String |
action_result.parameter.partition_key_name | string | `aws dynamodb partition key name` `aws dynamodb attribute name` | firstname |
action_result.parameter.partition_key_value | string | | testdata |
action_result.parameter.sort_key_datatype | string | | String |
action_result.parameter.sort_key_name | string | `aws dynamodb sort key name` `aws dynamodb attribute name` | lastname |
action_result.parameter.sort_key_value | string | | sort_key_test |
action_result.parameter.table_name | string | `aws dynamodb table name` | test_query |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 2 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Wed, 21 Sep 2022 18:17:41 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 2745614147 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 91PHHJD3LHOFKAJ7PNM1UF77UBVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 91PHHJD3LHOFKAJ7PNM1UF77UBVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.TableNames | string | | |
action_result.summary | string | | |
action_result.message | string | | Item deleted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'put item'

Add an item to the table

Type: **generic** <br>
Read only: **False**

Please refer app documentation to use the expression parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Table name to add item in | string | `aws dynamodb table name` |
**item_json** | required | JSON of item to be added in the table | string | |
**condition_expression** | optional | Condition to be checked before inserting an item | string | |
**expression_attribute_names** | optional | Attribute names json | string | |
**expression_attribute_values** | optional | Attribute values json | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.condition_expression | string | | #age \<> :age |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.expression_attribute_names | string | | {"#age":"age"} |
action_result.parameter.expression_attribute_values | string | | {":age":{"N":"12"}} |
action_result.parameter.item_json | string | | {"testing1":{"S":"32"},"age":{"N":"12"}} |
action_result.parameter.table_name | string | `aws dynamodb table name` | test_dev_table |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 2 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 10:24:42 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 2745614147 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | 469DQNHNGBMPVBCFVEUIMJQ5FFVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | 469DQNHNGBMPVBCFVEUIMJQ5FFVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.TableNames | string | | |
action_result.summary | string | | |
action_result.message | string | | Inserted item successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update item'

Update an item in the table

Type: **generic** <br>
Read only: **False**

Please refer app documentation to use the expression parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Table name to update item in | string | `aws dynamodb table name` |
**update_expression** | optional | Expression to update the item | string | |
**partition_key_name** | required | Name of partition key of table | string | `aws dynamodb partition key name` `aws dynamodb attribute name` |
**sort_key_name** | optional | Name of sort key of table | string | `aws dynamodb sort key name` `aws dynamodb attribute name` |
**partition_key_value** | required | Partition key value of item to update | string | |
**sort_key_value** | optional | Sort key value of item to update | string | |
**partition_key_datatype** | required | Datatype of partition key of table | string | |
**sort_key_datatype** | optional | Datatype of sort key of table | string | |
**expression_attribute_names** | optional | Attribute names json | string | |
**expression_attribute_values** | optional | Attribute values json | string | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.expression_attribute_names | string | | {"#age" : "age"} |
action_result.parameter.expression_attribute_values | string | | {":age":{"N":"24"}} |
action_result.parameter.partition_key_datatype | string | | String |
action_result.parameter.partition_key_name | string | `aws dynamodb partition key name` `aws dynamodb attribute name` | testing1 |
action_result.parameter.partition_key_value | string | | 2 |
action_result.parameter.sort_key_datatype | string | | String |
action_result.parameter.sort_key_name | string | `aws dynamodb sort key name` `aws dynamodb attribute name` | name |
action_result.parameter.sort_key_value | string | | sort_key_test |
action_result.parameter.table_name | string | `aws dynamodb table name` | test_dev_table |
action_result.parameter.update_expression | string | | set #age = :age |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 2 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 10:01:09 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 2745614147 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | FE7CQFQDIO70P8CT6LHSH1J8NBVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | FE7CQFQDIO70P8CT6LHSH1J8NBVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.data.\*.TableNames | string | | |
action_result.summary | string | | |
action_result.message | string | | Updated item successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get item'

Get an item from the table

Type: **investigate** <br>
Read only: **True**

The parameter values do not need to be in Binary encoded format, if the key datatype is Binary.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Table name to fetch the item from | string | `aws dynamodb table name` |
**partition_key_name** | required | Name of partition key of table | string | `aws dynamodb partition key name` `aws dynamodb attribute name` |
**sort_key_name** | optional | Name of sort key of table | string | `aws dynamodb sort key name` `aws dynamodb attribute name` |
**partition_key_value** | required | Partition key value of item to fetch | string | |
**sort_key_value** | optional | Sort key value of item to fetch | string | |
**partition_key_datatype** | required | Datatype of partition key of table | string | |
**sort_key_datatype** | optional | Datatype of sort key of table | string | |
**attributes_to_get** | optional | To fetch specific attributes from the item(accepts comma seperated attributes) | string | `aws dynamodb attribute name` |
**reserved_keyword_attributes** | optional | To fetch attributes from items whose names are same as reserved keywords(accepts comma seperated attributes) | string | `aws dynamodb attribute name` |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attributes_to_get | string | `aws dynamodb attribute name` | name |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.partition_key_datatype | string | | String |
action_result.parameter.partition_key_name | string | `aws dynamodb partition key name` `aws dynamodb attribute name` | testing1 |
action_result.parameter.partition_key_value | string | | 2 |
action_result.parameter.reserved_keyword_attributes | string | `aws dynamodb attribute name` | ADD,ARRAY |
action_result.parameter.sort_key_datatype | string | | String |
action_result.parameter.sort_key_name | string | `aws dynamodb sort key name` `aws dynamodb attribute name` | name |
action_result.parameter.sort_key_value | string | | sort_key_test |
action_result.parameter.table_name | string | `aws dynamodb table name` | test_dev_table |
action_result.data.\*.Item | string | | |
action_result.data.\*.Item.primary.S | string | | test done |
action_result.data.\*.Item.secondary.S | string | | testing |
action_result.data.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 106 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.date | string | | Thu, 22 Sep 2022 05:59:54 GMT |
action_result.data.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 4263225874 |
action_result.data.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | EITIHSOAI9VTL2VPB08G059K63VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.ResponseMetadata.RequestId | string | | EITIHSOAI9VTL2VPB08G059K63VV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.ResponseMetadata.RetryAttempts | numeric | | 0 |
action_result.summary | string | | |
action_result.message | string | | Fetched Item Data Successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query data'

Query data from database

Type: **investigate** <br>
Read only: **True**

<ul> <li>Select Parameter<ul> <li>The Select parameter defines what attributes are supposed to be fetched. The options are as follows :</li> <ul> <li>ALL_ATTRIBUTES : Returns all of the item attributes from the specified table or index. If you query a local secondary index, then for each matching item in the index, DynamoDB fetches the entire item from the parent table. If the index is configured to project all item attributes, then all of the data can be obtained from the local secondary index, and no fetching is required.</li> <li>ALL_PROJECTED_ATTRIBUTES : Allowed only when querying an index. Retrieves all attributes that have been projected into the index. If the index is configured to project all attributes, this return value is equivalent to specifying ALL_ATTRIBUTES</li> <li>COUNT : Returns the number of matching items, rather than the matching items themselves</li> <li>SPECIFIC_ATTRIBUTES : Returns only the attributes listed in ProjectionExpression. This return value is equivalent to specifying ProjectionExpression without specifying any value for Select</li> </ul> <li>If you use the <b>ProjectionExpression</b> parameter, then the value for Select can only be SPECIFIC_ATTRIBUTES. Any other value for Select will return an error.</li> </ul> </li> <li>Return Consumed Capacity Parameter<ul> <li>Determines the level of detail about either provisioned or on-demand throughput consumption that is returned in the response. There options are as follows :</li> <ul> <li>INDEXES : The response includes the aggregate ConsumedCapacity for the operation, together withConsumedCapacity for each table and secondary index that was accessed.</li> <li>TOTAL - The response includes only the aggregate ConsumedCapacity for the operation.</li> <li>NONE - No ConsumedCapacity details are included in the response.</li> </ul> </ul> </li> <li>KeyConditionExpression Parameter <ul> <li> To specify the search criteria, we use a key condition expression which is a string that determines the items to be read from the table or index. </li> <li> You must specify the partition key name and value as an equality condition. You cannot use a non-key attribute in a Key Condition Expression. </li> <li> You can optionally provide a second condition for the sort key (if present). The sort key condition must use one of the following comparison operators: <ul> <li> a = b — true if the attribute a is equal to the value b </li> <li> a < b — true if a is less than b </li> <li> a <= b — true if a is less than or equal to b </li> <li> a > b — true if a is greater than b </li> <li> a >= b — true if a is greater than or equal to b </li> <li> a BETWEEN b AND c — true if a is greater than or equal to b, and less than or equal to c.</li></ul></li></ul></li><li>FilterExpression Parameter<ul><li>If you need to further refine the Query results, you can optionally provide a filter expression. A filter expression determines which items within the Query results should be returned to you. All of the other results are discarded.</li><li>A filter expression cannot contain partition key or sort key attributes. You need to specify those attributes in the key condition expression, not the filter expression.</li><li>The syntax for a filter expression is similar to that of a key condition expression. Filter expressions can use the same comparators, functions, and logical operators as a key condition expression. In addition, filter expressions can use the not-equals operator (<>), the OR operator, the CONTAINS operator, the IN operator, the BEGINS_WITH operator, the BETWEEN operator, the EXISTS operator, and the SIZE operator.</li></ul></li><li>ProjectionExpression Parameter<ul><li>A projection expression is a string that identifies the attributes that you want. To retrieve a single attribute, specify its name. For multiple attributes, the names must be comma-separated.</li></ul></li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**table_name** | required | Name of Table to perform query on | string | `aws dynamodb table name` |
**index_name** | optional | Name of index to be used for the query | string | `aws dynamodb index name` |
**expression_attribute_names** | optional | Attribute names json | string | |
**expression_attribute_values** | optional | Attribute values json | string | |
**key_condition_expression** | required | Expression to apply conditions on partition key and sort key to fetch data accordingly from the table or index | string | |
**filter_expression** | optional | Expression to filter data from table.A FilterExpression does not allow key attributes. You cannot define a filter expression based on a partition key or a sort key | string | |
**projection_expression** | optional | Defines the attributes to be included in the result. If this expression is provided SELECT value is set to SPECIFIC_ATTRIBUTES. The attributes in the expression must be separated by commas | string | `aws dynamodb attribute name` |
**select** | optional | Retrieve all item attributes, specific item attributes, the count of matching items, or in the case of an index, some or all of the attributes projected into the index | string | |
**return_consumed_capacity** | optional | Determines the level of detail about either provisioned or on-demand throughput consumption that is returned in the response | string | |
**max_items** | optional | Maximum number of items to process | numeric | |
**sort_descending** | optional | By default, the sort order for query data is ascending. To reverse the order, set the sort_descending parameter to true | boolean | |
**consistent_read** | optional | Determines the read consistency model: If set to true, then the operation uses strongly consistent reads; otherwise, the operation uses eventually consistent reads | boolean | |
**credentials** | optional | Assumed role credentials | string | `aws credentials` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.consistent_read | boolean | | False |
action_result.parameter.credentials | string | `aws credentials` | {'AccessKeyId': 'ASIASJL6ZZZZZ3M7QC2J', 'Expiration': '2021-06-07 22:28:04', 'SecretAccessKey': 'ZZZZZAmvLPictcVBPvjJx0d7MRezOuxiLCMZZZZZ', 'SessionToken': 'ZZZZZXIvYXdzEN///////////wEaDFRU0s4AVrw0k0oYICK4ATAzOqzAkg9bHY29lYmP59UvVOHjLufOy4s7SnAzOxGqGIXnukLis4TWNhrJl5R5nYyimrm6K/9d0Cw2SW9gO0ZRjEJHWJ+yY5Qk2QpWctS2BGn4n+G8cD6zEweCCMj+ScI5p8n7YI4wOdvXvOsVMmjV6F09Ujqr1w+NwoKXlglznXGs/7Q1kNZOMiioEhGUyoiHbQb37GCKslDK+oqe0KNaUKQ96YCepaLgMbMquDgdAM8I0TTxUO0o5ILF/gUyLT04R7QlOfktkdh6Qt0atTS+xeKi1hirKRizpJ8jjnxGQIikPRToL2v3ZZZZZZ=='} |
action_result.parameter.expression_attribute_names | string | | { "#fn" : "firstname"} |
action_result.parameter.expression_attribute_values | string | | {":fn" : { "S" : "testdata"}} |
action_result.parameter.filter_expression | string | | #v >= :num |
action_result.parameter.index_name | string | `aws dynamodb index name` | primary_index |
action_result.parameter.key_condition_expression | string | | #fn = :fn |
action_result.parameter.max_items | numeric | | 2 |
action_result.parameter.projection_expression | string | `aws dynamodb attribute name` | name,age |
action_result.parameter.return_consumed_capacity | string | | TOTAL |
action_result.parameter.select | string | | ALL_ATTRIBUTES |
action_result.parameter.sort_descending | boolean | | False |
action_result.parameter.table_name | string | `aws dynamodb table name` | test_query |
action_result.data.\*.QueryData | string | | |
action_result.data.\*.QueryData.\*.Count | numeric | | 1 |
action_result.data.\*.QueryData.\*.Items.\*.lsi_one.S | string | | local-index-test |
action_result.data.\*.QueryData.\*.Items.\*.primary.S | string | | test |
action_result.data.\*.QueryData.\*.Items.\*.secondary.S | string | | testing |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.connection | string | | keep-alive |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.content-length | string | | 126 |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.content-type | string | | application/x-amz-json-1.0 |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.date | string | | Tue, 07 Mar 2023 14:40:35 GMT |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.server | string | | Server |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.x-amz-crc32 | string | | 2439917427 |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPHeaders.x-amzn-requestid | string | | P6IEQOQPJ1H55CTB83O3M2OV9VVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.QueryData.\*.ResponseMetadata.HTTPStatusCode | numeric | | 200 |
action_result.data.\*.QueryData.\*.ResponseMetadata.RequestId | string | | P6IEQOQPJ1H55CTB83O3M2OV9VVV4KQNSO5AEMVJF66Q9ASUAAJG |
action_result.data.\*.QueryData.\*.ResponseMetadata.RetryAttempts | numeric | | |
action_result.data.\*.QueryData.\*.ScannedCount | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Fetched data successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

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
