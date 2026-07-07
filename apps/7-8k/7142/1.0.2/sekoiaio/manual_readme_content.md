# Sekoia.io actions

## Purpose

Develop a Splunk SOAR App that interact with [SEKOIA.IO](http://SEKOIA.IO) CTI.

## Authentication

To interact with the [SEKOIA.IO](http://SEKOIA.IO) API, use an API key.

see [this documentation](https://docs.sekoia.io/cti/features/integrations/api/) for more information

## Actions

The App should implement the following actions

### Get indicator

This action allow the user to get an indicator according to some criteria

### Get indicator Context

Create an action that allow the user to get the context of an indicator

### Get Observable

Create an action that allow the user to get an observable according to some criteria

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Sekoiaio api. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http | tcp | 80 |
|         https | tcp | 443 |
