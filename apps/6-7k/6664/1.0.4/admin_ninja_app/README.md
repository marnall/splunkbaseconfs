# Overview
The Admin Ninja App is a Search Head App or Splunk, which is a companion-app to the [Admin Ninja TA](https://splunkbase.splunk.com/app/6665) - built by Splunk admins for Splunk admins - that will greatly assist any Splunk admin in managing, tracking & auditing their wide array of Splunk instances.

The TA pulls data from each Splunk instance you install it on about the Splunk instance itself. This data includes everything from configs and settings to users, messages and more. The reason this is needed is because Splunk doesn’t log **everything** about itself, and the \_audit index could use with more detailed auditing.  
All of this culminates in a Splunk admin wanting more trackability and information about the Splunk architecture that they manage, which becomes increasingly difficult as any environment gets larger and larger.

### What is the SH App used for?
The app is used to aggregate and organise the data ingested by the Admin Ninja TA on your environment’s Search Head. This is useful for keeping track of your entire environment from a glance - similar to a Monitoring Console, however this will account for additional info that isn’t covered by a regular Splunk install.

# Documentation
For documentation reference, please visit [our documentation page](https://avocado.com.au/resources/splunk-admin-ninja/documentation-splunk-admin-ninja/).

# License
Components Written by Avocado Consulting, Copyright (C) 2022 Avocado Consulting Pty. Ltd.

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.