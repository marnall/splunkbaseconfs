# Splunk Visualization - Encrypted Credentials
        The Encrypted Credentials visualization allows you to seamlessly interact with the Encrypted Credentials store within Splunk, right from a simple xml dashboard.
        
# NOTE - *THIS IS IMPORTANT*

  The use of this visualization requires a user to have the `encrypted_credentials` role, which is a custom role included within the visualization. This role grants the user access to the [`admin_all_objects`](http://docs.splunk.com/Documentation/Splunk/latest/Admin/Authorizeconf#.5Bcapability::admin_all_objects.5D) capability. This role was separated from the `admin` role as a way of differentiating who has access to the visualization. 
  `ONLY ASSIGN THIS ROLE TO THOSE USERS WHOM YOU TRUST WITH ADMIN PRIVILEGES.`
          
Configuration
-------------
The Encrypted Credentials visualization has very few options. 


1. Realm
    The realm setting is an optional field.

1. Username
    This is the username to be created for the credential set.

1. Password
    This is the password to be associated with the username being created. Ensure it aligns with the best practices established within your organization.
    NOTE: If the password contains a special character, then you MUST URI DECODE THE PASSWORD, before use in ANY other section of Splunk. 
    
## Visualization Format Options
### Debug

1. JavasScript Logging
    1. yes, no
    1. This controls if debug logging should be enabled for the view.

## The Only Search

1. | makeresults

To use this visualization the `| makeresults` search must be performed. Once you have results, then select the Encrypted Credentials visualization. That is all to do. 

## Support

Please ask a question on Answers. Tag it with "aplura_viz" to get noticed.
Support URL: answers.splunk.com

## Third-party software

 `jQuery` and `underscore` frameworks are utilized. Please refer to Splunk Documentation for Licensing of these frameworks.
 
 This visualization also uses the `handlebars-loader` framework. Usage is provided by the MIT license. For more information, please see http://www.opensource.org/licenses/mit-license

## Acceleration

Report Acceleration: None
Data Model Acceleration: None
Summary Indexing: None