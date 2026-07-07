With Vcontrol you can put Splunk elements such as dashboards, 
savedsearches, views, etc. under subversion control.

Vcontrol provides GUIs that allow endusers to commit their changes to a
subversion repository, browse their local app directory, compare
diffs and browse revisions.

=== Configure ===
configure your svn settings in $APP_HOME/local/svn.conf
see an example file in $APP_HOME/default/svn.conf.example

=== Troubleshoot ===
enable python logging with DEBUG level for svn in your log-local.cfg file:

  #> cat $SPLUNK_HOME/etc/log-local.cfg
  [python]
  splunk.svn = DEBUG

and see the logs in $SPLUNK_HOME/var/log/splunk/svn.log


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

