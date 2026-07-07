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
