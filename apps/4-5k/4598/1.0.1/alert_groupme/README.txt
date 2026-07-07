# Groupme Alert Action


## Introduction


The Groupme Alert Action allows Splunk to send alerts to Groupme groups and chats through the use of a Groupme Bot.



## Installation and configuration


To install the Groupme Alert Action, follow the instructions in the [Splunk Add-ons](http://docs.splunk.com/Documentation/AddOns/latest/Overview/Installingadd-ons) 

##Usage

##Create an existing alert with the Groupme alert action

1.) In the **Search & Reporting** app, run a search for your string.
2.) Confirm that the search results look as you expect.
3.) Click the **Save As** dropdown link above the right side of the search box, then select Alert from the menu that appears.
4.) Enter a title for your alert, along with a description if desired, and configure the standard alert fields related to permissions, scheduling, and trigger conditions according to your needs.
5.) Under **Trigger Actions**, click **+ Add Actions**, then select **Groupme Alert**.
6.) Enter the **Message** and select the **Severity** that you want Groupme to send when the alert is triggered.
7.) Enter the **Bot ID** that you will be sending the Alert, Message, and Result link to, then click **Save**.

##Add a Groupme action to an existing alert

1.) In the **Search & Reporting app**, navigate to the **Alerts** tab and locate the existing alert.
2.) Click **Edit**, then select **Edit Actions**.
3.) Click **+ Add Actions**, then select **Groupme Alert**.
4.) Enter the **Message** and select the **Severity** that you want Groupme to send when the alert is triggered.
5.) Enter the **Bot ID** that you will be sending the Alert, Message, and Result link to, then click **Save**.
For more information on the Groupme Bot API visit the [Groupme Bot Tutorial](https://dev.groupme.com/tutorials/bots) website.

