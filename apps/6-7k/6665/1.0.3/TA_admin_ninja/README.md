# Overview
The Admin Ninja TA is a Technical Add-on for Splunk & companion app for the [Admin Ninja App](https://splunkbase.splunk.com/app/6664) - built by Splunk admins for Splunk admins - that will greatly assist any Splunk admin in managing, tracking & auditing their wide array of Splunk instances.

TA pulls data from each Splunk instance you install it on about the Splunk instance itself. This data includes everything from configs and settings to users, messages and more. The reason this is needed is because Splunk doesn’t log **everything** about itself, and the _audit index could use with more detailed auditing.  
All of this culminates in a Splunk admin wanting more trackability and information about the Splunk architecture that they manage, which becomes increasingly difficult as any environment gets larger and larger.  
  
### How does the TA get this information?  
The TA retrieves information about the Splunk instance it’s running on by pinging the REST API of that instance (hence the title), and ingesting the results in JSON format.  
When used in a distributed manner, this provides extremely efficient tracking of key settings & provides auditability of what was changed and when.

# Documentation
For documentation reference, please visit [our documentation page](https://avocado.com.au/resources/splunk-admin-ninja/documentation-splunk-admin-ninja/).

# License
Components Written by Avocado Consulting, Copyright (C) 2022 Avocado Consulting Pty. Ltd.

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.