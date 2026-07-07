# splunk-custom-alert-jenkins-trigger

## Introduction

This Splunk custom alert action sends a remote job trigger for "Trigger builds remotely (e.g., from scripts)" Build trigger option in Jenkins.  This allows you to send custom parameters from the Splunk search result variables to a Jenkins job to be consumed. Requires Python 2.x and python modules: requests, json, sys.
No global configuration required, must be done in alert action.

## Example Jenkins Trigger config

Jenkins Job parameters: computehost=$result.host$&userName=$result.userName$

## Installation SPL File Method
SPL file install: on Splunk Webapp navigate to apps..manage apps. Click Install app from file.  Upload the spl file from this repo.

## Installation folder method
Drop the jenkins_trigger folder into the Splunk/etc/apps directory, restart Splunk.
