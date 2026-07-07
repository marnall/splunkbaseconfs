This app will ignore the HTTP_PROXY and HTTPS_PROXY environment variables, as it does not use HTTP
to connect to the database.

### On Creating New Databases and Collections

When creating a new asset, you must specify something for the **database** parameter, which will be
the name of the database. If you specify one which does not currently exist, then the app will carry
on as normal (though there will be a warning in the test connectivity modal). After running a **post
data** action, then that database will be created. Similarly, by specifying a **collection** which
does not currently exist as a parameter to **post data** , you can create new collections.

### BSON Strings

Many parameters in this app, like **data** and **filter** expect a deserializable BSON string. In
respects to this app, BSON is a superset of JSON, so any valid JSON will be properly deserialized.
However, BSON can also deserialize many other types. For example, MongoDB uses an ObjectID type by
default for the "\_id" field. In order to use this, like to create a filter, the BSON string will
look like `     {"_id": {"$oid":"5a345190f059c57581d754f0"}}    ` . If you can install the
appropriate python modules (i.e. pymongo) then you can serialize python dictionaries to the
appropriate string in your playbook code. If that approach isn't possible, the result data from
**get data** will contain the appropriate representations, as well, which can be used as reference
for future actions.

## PyMongo

This app uses the PyMongo module, written by Bernie Hackett and is licensed under the Apache
Software License, Version 2.0, Copyright (2021) The Apache Software Foundation
(http://www.apache.org/).
