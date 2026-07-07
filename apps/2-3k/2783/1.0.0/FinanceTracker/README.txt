### Overview

#### About the ‘My Finance Tracker’

| Author | Khyati Majmudar |
| --- | --- |
| App Version | 1.0.0 |
| Vendor Products | None |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | Implements Data Model |

##### Unleash the Power of Splunk on Finances Management.

‘My Finance Tracker’ allows a Splunk® Enterprise administrator to monitor the Finances and Financial Transactions of the company or an individual.

Use Splunk to keep a track of you or your Enterprise’s Finances and make informed decisions!
You can automate input of your financial statements to gain insights. You can import the below documents to name a few:
1. Your Daily Expenses or Company Expenses
2. Income Details including Salary, Bonus, Interests, etc in case of Personal Use or Sale Details in case of Company
3. Credit Statements
4. Equity Investment Report 
5. Other Income / Expenditure Sheets

##### Scripts and binaries

None used

#### Release notes

##### About this release

Version 1.0.0: Import Expense Details to understand Income v/s Expenditure

Version 1.0.0 of the ‘My Finance Tracker’ is compatible with:

| Splunk Enterprise versions | Splunk Enterprise 6.0.x or later. |
| --- | --- |
| Platforms | Platform independent |
| Vendor Products | None |
| Lookup file changes | None Required |


##### Known issues

No Known Issues

##### Support and resources

**Questions and answers**

Please email us: khyati.ninad@gmail.com for any Questions or Support required.

**Support**

Please email us: khyati.ninad@gmail.com for any Questions or Support required. Expected resolution time is 2 days


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

‘My Finance Tracker’ supports all the server platforms in the versions supported by Splunk Enterprise.
 

#### Software requirements

No Extra Software are required.

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1. Click Download on this page. The my_finance_tracker.tar.gz installer file downloads to your computer.
2. Log into Splunk Web.
3. Click Apps > Manage Apps.
4. Click Install App from File.
5. Upload the my_finance_tracker.tar.gz installer file.
6. Restart Splunk.



## USER GUIDE

### Key concepts for ‘My Finance Tracker’


With the advances of technology and Big Data Analytics, it is now easy to keep a check on your finances. As easy as 1-2-3..!
1. Keep a track of you or your Company's Finances in an Excel or Take an Export from your Finance Reporting Tool.
2. Categorize them into Income / Expenditure.
3. Categorize Income into various Types:
o Salary - Your fixed Salary (in case of personal use) or Sale (in case of company)
o Interest - Any Interest which may or may not be a steady income source
o Bonus - Any Extra Income is always welcome!
o 
4. Also, further categorize Expenses into 3 Types:
o Category A - Which are inevitable
o Category B - Which may not be entirely avoidable. But can have a bit of discretion!
o Category C - Which can be avoided with reasonable discretion!
5. Provide Details on Amount Spent / Earned / Received.
6. Save the Excel as CSV and Load into Splunk as per the format with sourceType = ‘FinanceTracker’ or place them in the Directory which Splunk is monitoring.
7. You can also upload your other statements like Credit Card Statements, Equity Holdings and your other Financial Statements. Make sure that your Input have the below columns or are re-mapped in Splunk through Alias:
o Type - With data as Income/Expenditure
o Category - Category A / B / C for Expenses as explained above or Salary / Interest / Bonus for Income
o Details - Text Details of your Income / Expense
o Value - Monetary value of the transaction
8. Build up quick charts, pivots to analyse the finances and take control!

### Data types

This app provides the index-time and search-time knowledge for the following types of data:

**Financial Data**

Contains the entire financial data with below fields:
- Type: Income / Expenditure
- Category: High level Category of Income / Expenditure
- Details: Elaborated details of Income / Expenditure
- Value: Monetary Value of the Transaction

- File location: <filepath and and filename of lookup>


### Configure ‘My Finance Tracker’

By default, My Finance Tracker monitors the Folder for any Financial Documents to import. In order to add any more Folders,
1. Go to Settings > Data Inputs
2. Click on Files and Directories
3. You can add Directories to monitor where you can place your financial documents. Save it with SourceType = ‘FinanceTracker’



### Example Use Case ###
For personal use, user can import his daily expenses and incomes into this application to understand what are his income sources & spending buckets and based on that, he can determine where he stands each month financially.

By studying our expense patterns, we can gain insights on where we can put in cuts in order to save effectively as well. We can also understand what sort of Expenses can be curtailed, where we can increase our income sources & savings, etc.

Similarly, at an Enterprise level, the company can keep track of their day to day expenses and incomes and see how the company is performing every month, every year and so on.

