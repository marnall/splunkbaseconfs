Documentation

Overview

	Basic parser for Imperva Incapsula and Attack Analytics
	In your inputs.conf, you should set
		sourcetype=incapsula
	Install this App on the Index/HF tier as well as SH where knowledge objects are required
		Incapsula WAF data should get detected as incapsula:cef
			This data has been normalized to IDS, Network_Traffic, and Web Data Models
		Attack Analytics should get detected as imperva:aa:cef
			This data has been normalized to the Alerts DM
License

        Copyright 2020 nhdpotter

        Licensed under the Apache License, Version 2.0 (the "License");
        you may not use this file except in compliance with the License.
        You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

        Unless required by applicable law or agreed to in writing, software
        distributed under the License is distributed on an "AS IS" BASIS,
        WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
        See the License for the specific language governing permissions and
        limitations under the License.

Support

	This app is not supported. It follows common practices for Splunk parsing

Documentation
	See splunk docs for assistance with props transforms eventtypes tags
