# File: README.txt
# Copyright (c) 2019-2020 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

All user documentation can be found in the Phantom platform in Documentation, Administration Manual, Data Sources, Splunk.
You may also visit https://my.phantom.us/docs/admin/splunk with your Phantom account.
Contact https://support.splunk.com for any support or installation issues. The only system requirement is a functional installation of the Phantom platform.

==================
Installation Notes
==================

See Phantom documentation for details at https://docs.splunk.com/Documentation/PhantomRemoteSearch/PhantomRemoteSearch/Overview

===========================
Version 1.0.17 Release notes
===========================
- Add index phantom_custom_function

===========================
Version 1.0.16 Release notes
===========================
- Add endpoint to add Phantom indexes

===========================
Version 1.0.14 Release notes
===========================
- Remove index phantom_docs since Phantom documentation is now hosted on Splunk docs

===========================
Version 1.0.12 Release notes
===========================
- Bug fix remove inputs.conf for Splunk Cloud support

===========================
Version 1.0.9 Release notes
===========================
- Add index phantom_note
- Remove default stanza config parameters

===========================
Version 1.0.7 Release notes
===========================
- Newly created phantomdelete user may not be visible on Splunk UI under some circumstances. In that case, go to Settings -> Access Controls -> Roles -> phantomdelete and de-select "delete_by_keyword" capability and save.  Then, the phantomdelete user will be visible.  Once the user is visible, please re-add the "delete_by_keword" capability back to the phantomdelete role.
