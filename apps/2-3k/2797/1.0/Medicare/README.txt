App Name: "Medicare at a glance"

Description: This app provides valuable information on available medicare across USA using healthcare Open data. It's developed as a part of "Splunk aptitude app contest"
               in a quest to build better data app using open data and powerful Splunk data analytics in "Social Impact" category.

WHY the App?
   In USA, Health Care sector is a major target for public sector. Goveronment has made many important data set as "Open data" available at www.healthdata.gov
It contains many diversified data sets containing different set of data. Getting valuable insights like Hospitals or medicare available, types of facilities provided there,
average payment per services etc is difficult, so many people are being not aware of the facilities available in healthcare across country or in their region.

When people are given with the information in more appropriate visualizations, more interactive way, more "Open" way, they become more powerful and confident in making
decisions in their health area. They become more aware of facilities provided by goveronment, so it increases public transparency and collaboration towards more open, connected
and healthy society

What the App?

    Using many datasets available at http://data.gov/ as "Open data" , the app tries to draw major insights in following areas
                 
                 - General Hospital Information including hospital types,number of hospitals across states or Cities
                 - Detail Information about hospitals in particular area selected by user
                 - Facilities available in your city at hospitals
                 - Detailed information on outpatient services/procedures available across different region.
                 - Inpatient prospective Payment system Information in Diagnosis Related drup Groups (DRG) like average payment per drug type in a city
    Insightful visualizations, more user choice driven and interactive graphic demonstartion inside the Splunk app dashboards. 
 

How to use the app ?

   Installation:

   Download the app from Splunk base.
   Put the folder inside <SPLUNK_HOME>/etc/apps/<app_name>
   Sample data are located at <SPLUNK_HOME>/etc/apps/<app_name>/sample

   Create splunk index "healthcare" with these following source and sourcetypes
        
            source:
                    Hospital_General_Information.csv    - contains general information about Hospitals
                    Structural Measures - Hospital.csv	- contains information on various facilities offered in hospital
                    Outpatient Procedures - Volume.csv	- contains information on available volumes of outpatient procedures
                    Heart Attack Payment - Hospital.csv - contains information on payment across hospitals for heart attack
                    Payment_for_Top100_Drug_Groups.csv  - contains IPPS(Inpatient Payment Provider System) report on Diagnosis Related drug groups
           sourcetypes:
                    Payment_Top_Drug_Groups
                    heart_attack
                    Outpatient_procedure
                    structural_measures_hospital
                    Hospital_General_Information

  Usage:
        After app installation and index created, navigate through different dashboards listed on navigation bar.
        Select state and city to visualize information in depth
