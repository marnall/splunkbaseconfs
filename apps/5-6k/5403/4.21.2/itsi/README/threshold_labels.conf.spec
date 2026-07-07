# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved. 
#
# This file contains all possible attribute/value pairs for configuring settings
# for severity-level thresholds. Use this file to configure
# threshold names and color mappings.
#
# To map threshold names and colors, place a threshold_label.conf in 
# $SPLUNK_HOME/etc/apps/itsi/local/. For examples, see threshold_label.conf.example.
#
# To learn more about configuration files (including precedence) see the documentation 
# located at http://www.splunk.com/base/Documentation/latest/Admin/Aboutconfigurationfiles
#
# CAUTION: You can drastically affect your Splunk installation by changing any settings in
# this file other than the colors. Consult technical support (http://www.splunk.com/page/submit_issue)
# if you are not sure how to configure this file.

[<name>]
color = <string>
* A valid color code.
* Required.

lightcolor = <string>
* A valid color code to display for Episode Review "prominent mode". 
* When you view Episode Review in prominent mode, the entire row is colored
  rather than just the colored band on the side. 
* Required.

threshold_level = <integer>
* A threshold level that is used to create an ordered list of the labels.
* For example, if you set the 'Normal' threshold level to "1", it appears 
  first when the levels are listed in the UI. 
* Optional.

health_weight = <integer>
* The weight or importance of this status. 
* This value should be between 0 and 1. 
* In general, regular levels like Normal and Critical have a weight of "1", while 
  less important levels like Maintenance and Info have a weight of "0".
* Required.

health_min = <integer>
* The minimum threshold value. 
* This value must be a number between 0 and 100. 0 and 100 are inclusive but 
  the minimum threshold value is exclusive.
* Required.

health_max = <integer>
* Themaximum threshold value.
* This value must be a number between 0 and 100. 0 and 100 are inclusive but 
  the maximum threshold value is exclusive.
* Required.

score_contribution = <integer>
* The number, traditionally from 0 to 100, that this particular level will
  contribute towards health score calculations.
* Required.
