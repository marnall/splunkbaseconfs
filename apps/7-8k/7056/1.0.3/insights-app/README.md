# Insights Platform

[]()

Micro Strategies' Insights App empowers businesses to harness the power of data for informed decision-making, enhanced customer engagement, and accelerated growth.
The app makes it easy to analyze data from diverse sources, providing a unified view for data exploration and the ability to draw valuable insights that drive strategic choices.
With the Insights App, you can:
** Provide data access to everyone across your organization, fostering a data culture
** Analyze data and share insights via an easy "drag and drop" interface

Version_Supported: Splunk 9+
Installation: This app is installed on Search Heads
Troubleshooting:
1. As Part of our Application we're writing files to three locations.
   These files can be found in #SPLUNK_HOME/apps/insights-app/local/ folder with the names "settings", "saved_analysis" and "configs" for saving the chosen indexes, analysis and join conditions respectively. If you experience any issue while saving indexes, analysis and join conditions make sure there is no permission issue. 

2. If you don't have access to any of the chosen indexes, the Insight Center will not show any fields. So make sure to choose the indexes you have access to by going to the Setup section.

3. In Organize section, make sure the first data set is the common data set between three or more joining data sources. e.g if we have three data sets namely CustomerInformation (CID, Customer_Name, Customer_Address), ProductInformation (PID, Product_Name, Product_Category) and OrderInformation (Cust_Id, Order_Id, Product_Id, Order_Date). CID from CustomerInformation and Cust_Id from OrderInformation are the joining fields. Product_Id from OrderInformation and PID from ProductInformation are the joining fields. So, OrderInformation which is common in above two would be the first data set selected in the config entries, to enable the joining between all these three tables.

Release 1.0.3

1)Fixed the Packaging Issue.

Release 1.0.2
With this release we have introduced few features which will make
 
1) We've made analysis even easier.  It's now called "Manage Analysis" and with it you can Retrieve, Delete, or Rename a saved analysis
 
2) We've transformed the process of engaging with analyses into something new – introducing "Manage Analysis." With this feature, you can effortlessly Retrieve, Delete, or Rename a saved analysis. Simplifying the management of your analyses has never been easier
 
3) The Aggregation list has a new entry the Quartile Analysis, which helps the user the understand the distribution of data.
 
4) New and improved aggregation option based on the field which is selected.
E.g., If a string is selected, the platform limits the option to apply only count or distinct count aggregation.
 
5) We have fixed some bugs that improves the user experience.



App Documentation Link: "https://micro-strategies.box.com/s/u0f3i9wvv19em2btg83kwt540ay0v3z0"
