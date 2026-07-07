The Secure Application connector supports only the cloud-based version of Secure Application. On-prem deployments are not supported.

Introduction

The Secure Application connector is designed to support the saas-based version of Secure Application, a component of AppDynamics SaaS. Please note that on-premises deployments are not supported.

Prerequisites

Before setting up the Secure Application connector, ensure you meet the following prerequisites:
• API Client Registration: Register an API client in your AppDynamics Controller tenant with the necessary permissions to execute the public APIs for Secure Application triggered from the SOAR platform.
• Credentials: Gather the required credentials from your Secure Application console:
• Client Name: A unique identifier for the API client.
• Client Secret: A secret string used for authentication.

Procedure
Asset Configuration

To configure the asset, provide the following information:
1\. API Key: Enter the client ID of your AppDynamics API client.
Example: soar_app_test
2\. API Key Secret: Input the secret associated with the API client.
Example: 89hsooo768890!
3\. Base URL: Specify the full URL of your AppDynamics Controller instance.
Example: https://secureapp-master.cisco.com/
4\. Account ID: State the account name, which is the first part of the Base URL hostname.
Example: secureapp-master

OAuth 2.0 Access Token

The SOAR connector for Secure Application uses the provided API key and secret to obtain an OAuth 2.0 access token from the AppDynamics Controller. This token is used for all authenticated API requests and is automatically refreshed upon expiration.

Testing and Saving Configuration
1\. Test Connectivity: Click "Test Connectivity" to authenticate with the controller and confirm access to Secure Application.
2\. Save Configuration: Click "Save" to store the configuration.

Reference

Secure Application API Docs for Reference:
https://help.splunk.com/en/appdynamics-saas/extend-splunk-appdynamics/25.7.0/extend-splunk-appdynamics/splunk-appdynamics-apis/cisco-secure-application-apis

Version: 25.7.0
