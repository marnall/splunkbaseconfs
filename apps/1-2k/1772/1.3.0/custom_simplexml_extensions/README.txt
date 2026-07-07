This App provides a few SimpleMXL extensions for Splunk

=== Release Notes ===
This release improves the javascript and html image loading. 
- All app specific code is now packed in 
  $APP_HOME/appserver/static/components/<feature>/
- The only javascript include statement in the xml view is the call of
  appserver.js. All other js files will be loaded automatically
- All static (ugly) calls to 'app_name' are removed

- Additionally, this release includes the new view "TableSorter".
  A javascript library for filtering and sorting html tables


=== Configure ===
no custom configs for this release

=== Troubleshoot ===
Tested with Chrome

== Professional Services and Support ==
their is no professional service and no committed support for this app

== Licence and Terms of Use ==
   Copyright 2014 by mathias herzog, <mathu at gmx dot ch>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

=== Feedback ===
please provide feedback to <mathu at gmx dot ch>

