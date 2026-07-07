Compatibility:

THIS APP IS ONLY COMPATIBLE WITH LINUX OPERATIVE SYSTEMS.
Requires Python for Scientific Computing 3.0.2 app installed. https://splunkbase.splunk.com/app/2882/

Introduction:

The app consists in several dashboards that manages to visualize the data sent to the blockchain via BLOOCK. 

The main dashboard, called "Overview" serves as an overview and contains drilldowns that link to information dashboards in order to inspect the events that successed and failed.

The verification dashboard can be used for verificating multiple records.

At the Data Outputs dashboard, the user must configure the reports for the automation of the differentes processes.

For more information about Licenses visit https://splunk.bloock.com/signup.

Architecture:

	The app contains the following knowledge objects:

	Dashboards:

		Overview: App main dashboard, contains the main indicators and visualizations. All other dashboards are accesible from this view keeping the same filters as the main view.

		Events Insights: accesible through "Events Processed" indicator drilldown in the main view.

		Success Events Insights: accesible through "Success" indicator drilldown in the main view.

		Failed Events Insights: accesible through "Failed" indicator drilldown in the main view.

		Verification: Accessible through navigation bar.

		Licenses: Accessible through navigation bar.

		Data Outputs: Accessible through navigation bar.

		User Guide: Accessible through navigation bar.

    Nav:

        default: main navegation controls, contains links to the dashboards mentioned above.

    Custom Commands:

        sendrecords: this command sends the selected events to the Bloockchain via BLOOCK.
        
        verifyrecords: the verification records commands allows the user to check the events status.

		readcheckpoint: gets the last checkpoint value.

	Macros:

		bloock_audit_index: defines the audit index.


Installation and configuration:

	1. Install Python for Scientific Computing 3.0.2 app. https://splunkbase.splunk.com/app/2882/

	2. Bloock licenses. 
		Add the desired Bloock license at the Licenses Panel.
		Please provide a clear License Name and verify the information in order to avoid problems in the future.
    		To get more details about the license acquisition and pricing, please contact BLOOCK Staff.

	3. Audit index.
		Define the audit index for Bloock requests status in the macro 'bloock_audit_index'. It will contain the responses from the bloock requests.

	4. Send data to Bloock - Create a New Report
		At the Data Outputs dashboard, the user must create a report providing the license name generated at 1, select the index to collect the data from, and the frequency interval in minutes (maximum 60 minutes).


Common use cases:

    Review total events processed, total events with success statuts, total events with failed status. 

    Review licenses performance and utilization.

 
Changelog:
	1.0.4: Added binary file declarations and code maintenance
	1.0.3: Update Bloock SDK to v2.2.0
	1.0.2: Update Bloock SDK to v1.0.2
	1.0.1: Now uses Python for Scientific Computing as base python environment.
    1.0.0: Release version.

# Binary File Declaration
lib/bloock_lib/google/protobuf/internal/_api_implementation.cpython-38-x86_64-linux-gnu.so: this file does not require any source code
lib/bloock_lib/google/protobuf/pyext/_message.cpython-38-x86_64-linux-gnu.so: this file does not require any source code
lib/bloock_lib/google/_upb/_message.abi3.so: this file does not require any source code
lib/bloock_lib/grpc/_cython/cygrpc.cpython-38-x86_64-linux-gnu.so: this file does not require any source code
lib/bloock_lib/_bloock_bridge_lib.abi3.so: this file does not require any source code
lib/bloock_lib/_cffi_backend.cpython-38-x86_64-linux-gnu.so: this file does not require any source code