[import_maintenance_window]

param.title = <string>
* The title that the new maintenance window will received.

param.description = <string>
* The optional description for the maintenance window. 

param.start_time = <string>
* The start time epoch of the window.

param.end_time = <string>
* The end time epoch of the event

param.object_type = <string>
* Entity or Service. Only one mode at a time is supported, so make sure the objects are all in that category.

param.object_keys = <string>
* This should be an mvfield in the data that contains all the entity or service keys that should be in maintenance.