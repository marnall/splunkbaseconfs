[generate_dashboards]
param.src_app = <list> Source app. It's a required parameter.
param.template_dashboard_id = <list> Template dashboard. It's a required parameter.
param.dest_app = <list> Destination app.
param.scheduled_view_template = <list> Scheduled view template.
param.permissions_template = <list> Permissions template.
param.del_prev = <list> Delete previous dashboards.
param.del_regex = <string> Delete dashboards with ID.
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
