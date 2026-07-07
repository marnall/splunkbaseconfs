The Splunk App for Torq Log Insights is designed to help customers understand and maximize their investment in Torq. The app provides pre-built analytics to understand and interrogate Torq Audit and Activity logs that are forwarded to Splunk.

The Splunk App for Torq Log Insights is platform-independent, and should work fine on any modern version of Splunk (Enterprise or Cloud).

Steps to enable the Torq App:

On Splunk:
   1. Apps (Visualizations) used by this app: This app makes use of visualizations not installed by default. For an optimal experience, we recommend installing the below-listed visualizations. The app will operate without them, but some panels will not render.
        - Splunk Sankey Diagram - Custom Visualization
        - Force Directed App For Splunk
      We also suggest (though do not require) the following apps be present:
        - Splunk Common Information Model (CIM)
        - Splunk App for Lookup File Editing

   2. Indices (Indexes)
        - Configure an index for Torq Audit events
        - Configure an index for Torq Activity events
      Note: Both sourcetypes may reside in the same index

   3. Input
        - Configure an HTTP Event Collection (HEC) endpoint. Refer to Splunk Documentation for more information.
      NOTE: Be sure to allow all indexes to which you plan to receive Torq data, and save the HEC endpoint information for the Torq-side configuration

   4. Configure Lookups
        - Configure Index Lookup ($SPLUNK_HOME/apps/torqapp/lookups/indexes.csv)
          Each line in the lookup should contain one index and its corresponding role (audit or activity)

Torq's audit logs conform to the Authentication and Change CIM data models.

   5. (Optional) Update your CIM datamodel constraints to include the Torq audit index.

Torq
   Configure and publish the log export workflows. This app is designed to support the data structure as based on Torq published workflow template

### CHANGE LOG ###

1.6.0 28 January 2025
   * Updated Case Management dashboard queries, improving SPL and addressing edge case issues.  Thanks to Bridget Gururaj for input and feedback.

1.5.5 27 September 2024 
   * search improvements and optimizations
   * dashboard improvements
   * link updates
   * enhanced CIM compliance
   * CASE MANAGEMENT
