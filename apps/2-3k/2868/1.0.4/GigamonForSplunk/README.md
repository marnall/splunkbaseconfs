


# Table of Contents

## OVERVIEW

- About Gigamon Visibility App For Splunk
- Release notes
- Performance benchmarks
- Support and resources

## INSTALLATION

- Hardware and software requirements
- Installation steps 
- Deploy to single server instance
- Deploy to distributed deployment
- Deploy to distributed deployment with Search Head Clustering
- Deploy to Splunk Cloud 


## USER GUIDE

- Key concepts
- Data types
- Lookups
- Configure Gigamon Visibility App For Splunk
- Troubleshooting

## Third Party Libraries

---
## OVERVIEW

### About Gigamon Visibility App For Splunk


|||
|---|---|
| Author | Gigamon, Inc |
| App Version | 1.0.3 |
| Vendor Products | Gigamon FM  |
| Has index-time operations | true |
| Create an index | false |
| Implements summarization | true:  summary index, Data Model with acceleration |


Gigamon Visibility App For Splunk allows a Splunk® Enterprise administrator to collect, store, visualize, and analyse Gigamon Visibility Fabric related data. By allowing Gigamon Visibility App For Splunk app access to the Visibility Fabrics, a Gigamon administrator can have full visibility and reporting across the entire Gigamon environment. Automated searches collect and store aggregated network statistics data from ports and maps within the environment. The map explorer helps the Gigamon Administrator to visualize the relationships within their environment.

#### Scripts

Gigamon Visibility App For Splunk comes with a modular input and the associated classes required to connect and consume the Gigamon API data. These files are located within the __bin__ folder of the App.

#### Release notes

##### About this release

Version 1.0.3 of Gigamon Visibility App For Splunk is compatible with:

|||
|---|---|
| Splunk Enterprise | 6.2 |
| CIM | 4.2 |
| Platforms | Platform Independent |
| Vendor Products | Gigamon FM Version Supported:  3.1, 3.2, 3.3, 3.4, 3.5, 5.0 |
| Lookup file changes | This App utilizes KVStore for many lookups, including: fms, clusters, maps, cards, and ports.  |

##### New features

Gigamon For Splunk includes the following new features:

- Connect and Consume Gigamon FM API data
- Map Explorer - Visually represent your Gigamon Maps
- Visualize Map and port statistics over time


##### Support and resources

**Questions and answers**

Access questions and answers specific to Gigamon Visibility App For Splunk at answers.splunk.com

**Support**

Support for Gigamon Visibility App For Splunk is available Monday thru Friday, 8 AM - 5 PM PST by emailing App.Splunk@gigamon.com.

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

Yes, Hardware is required. H Family Gigamon equipment as well as GigaVue FM.

#### Software requirements

To function properly, Gigamon For Splunk requires the following software:

- Splunk, v6.2 and up
- Supported GigamonFM version: 3.1, 3.2, 3.3, 3.4, 3.5, 5.0

#### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download Gigamon Visibility App For Splunk at https://splunkbase.splunk.com .

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Download the SPL package from Splunkbase.
1. Install the App onto the Search head tier, according to Splunk Documentation.
1. Install the included TA-GigamonForSplunk on the Indexer tiers in your environment, according to Splunk Documentation.
1. Configure the App to communicate with Gigamon FMs. You will find the configuration page at "Administration" -> "Configuration" -> "GigaVUE-FM".
Note:For adding FM3.3 or FM3.4 select FM version as "3.3.X" at the above configuration page

##### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1. Install the App according to the documentation for the version you are using.
1. Configure the App to communicate with the Gigamon FMs using the GigaVUE-FM view.

##### Deploy to distributed deployment

**Install to search head**

1. Install the App in one of 3 supported methods
1. Configure the App to communicate with the Gigamon FMs.

**Install to indexers**

1. Install the TA-gigamon Add-On (included in the appserver/addons folder) onto the Indexer using your technology of choice (Deployment Server / Master Node)

**Install to universal forwarders**

1. This App does not support installation to a Universal Forwarder.


##### Deploy to Search Head Cluster
**Install to SHC***
1. Install the App using the SHC Deployer
2. Install the TA-GigamonForSplunk Add-On (included in the appserver/addons folder) to the Indexer Tier, according to your configuration.
3. Install the IA-GigamonForSplunk Add-On (included in the appserver/addons/folder) to a Heavy Forwarder. Configure the connection to your Gigamon FMs from the Heavy Forwarder interface.

##### Deploy to Splunk Cloud

1. Engage Splunk Support to have this App installed.


## USER GUIDE

### Data types

This app provides the index-time and search-time knowledge for the following types of data from Gigamon Visibility Fabrics:

**Port Information**
- sourcetype = gigamon:api:service:port

**Audit Event Information**
- sourcetype = gigamon:api:service:audit

**Licensing Information**
- sourcetype = gigamon:api:service:license

**Map Information**
- sourcetype = gigamon:api:service:maps

**Node Information**
- sourcetype = gigamon:api:service:node

**Stats Information**
- sourcetype = gigamon:api:service:stats

**User Information**
- sourcetype = gigamon:api:service:users

**Traffic Analyzer Data**
- sourcetype = gigamon:api:service:traffic

### Lookups

Gigamon Visibility App For Splunk contains several KV Stores.

The KV Stores are descriptive in what they contain:  __giga_clusters__, __giga_fms__, __giga_ports__, __giga_cards__, __giga_maps__.

### Configure Gigamon Visibility App For Splunk

The only configuration out of the box is to connect the App with your Gigamon FM. You can do this by accessing the __Credential Configuration__ page. It is located on the Menu under __Administration -> Configuration__ Menu Item as __GigaVUE-FM__.

To change the location of the data from the __main__ index, update the event type __giga_idx__ with the appropriate index name. You must also change the Modular Input configuration to point to the new index.

### Troubleshooting

If you find yourself in a situation where the Gigamon Visibility App For Splunk doesn't work properly, or display the information you thought would be there, here are some simple troubleshooting steps to follow.

1.Start with the Gigamon Visibility App Health dashboard. It is found under the __Administration__ section of the navigation.
1.Check the error sourcetype: sourcetype=GigamonForSplunk:error
1.Check the internal logs: index=_internal source=*gigamon*
1.Rebuild the lookups: Navigate to the __Generate Lookups__ view under __Administration -> Configuration__ navigation item.


### Credits

Developed by [Aplura, LLC](www.aplura.com) for [Gigamon, INC.](www.gigamon.com)


##**Third-Party Libraries**






### Cubism.js : http://square.github.io/cubism/

Copyright 2012 Square, Inc.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.





### d3 : https://github.com/mbostock/d3

Copyright (c) 2010-2015, Michael Bostock
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* The name Michael Bostock may not be used to endorse or promote products
  derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL MICHAEL BOSTOCK BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.




### SA-Eventgen: https://github.com/coccyx/eventgen

Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.




### Fontawesome: fortawesome.github.io/Font-Awesome/license

Font License

Applies to all desktop and webfont files in the following directory: font-awesome/fonts/.
License: SIL OFL 1.1
URL: http://scripts.sil.org/OFL


Code License

Applies to all CSS and LESS files in the following directories: font-awesome/css/, font-awesome/less/, and font-awesome/scss/.
License: MIT License
URL: http://opensource.org/licenses/mit-license.html





### JQueryUI : https://github.com/jquery/jquery-ui

Copyright jQuery Foundation and other contributors, https://jquery.org/

This software consists of voluntary contributions made by many
individuals. For exact contribution history, see the revision history
available at https://github.com/jquery/jquery-ui

The following license applies to all parts of this software except as
documented below:

====

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

====

Copyright and related rights for sample code are waived via CC0. Sample
code is defined as all source code contained within the demos directory.

CC0: http://creativecommons.org/publicdomain/zero/1.0/

====

All files located in the node_modules and external directories are
externally maintained libraries used by this software which have their
own licenses; we recommend you read them, as their terms may differ from
the terms above.




### markdown.js : https://github.com/evilstreak/markdown-js

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.




### Vollkorn Font : https://www.google.com/fonts/specimen/Vollkorn

SIL Open Font License, 1.1

http://scripts.sil.org/OFL


### Latest version for FM 

Recent FM versions 3.4,3.3,3.2 can now be configured with the Gigamon app and backward compatibility for FM version 3.1 is still present.


