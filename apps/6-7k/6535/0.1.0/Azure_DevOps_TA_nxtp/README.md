# Technical Add-On for Azure DevOps REST-API

[![image](https://img.shields.io/badge/Contact-NEXTPART-1abc9c.svg)](mailto:info@nextpart.io)

This extension for [Splunk®](https://www.splunk.com/) can help you keep track of what is going on in
your organizations in Azure DevOps. With the name of the organization and your PAT you can easily
extract and index the latest commits, pull requests, builds and their comments periodically to do
whatever you want with them later. Whether it's tracking down your time records, identifying commits
with lots of changes, finding pull requests where there's a lot of ongoing discussion, or whatever.
This is the technical add-on that allows you to do all that easily.

## Features

Currently there are three inputs that deal with the Git part of the service to fetch commits, pull
requests, Builds and comments from there.

In the future there will also be something for releases, but there is currently no use case for the
developer.

## Setup

In order to use the App you need a PAT from your Organization with the following Permissions:

- Build - Read
- Code - Read
- Graph - Read

## Hints

Get a time-sheet like report for all your commits:

```
index="*"  sourcetype="azure:devops:commit"
  title != "Merge*" AND title != "*git subrepo*" author_email = "michael*"
    | eval _time = creation_date
    | eval creation_epoch = strftime(creation_date, "%d.%m.%Y %H")
    | dedup commit_id
    | dedup creation_epoch title
    | stats avg(creation_date) as datetime , min(creation_date) as start , max(creation_date) as end , values(*) as * count by creation_epoch user_email project_name
    | sort - datetime
    | eval datetime = strftime(datetime, "%Y-%m-%d %H:%M:%S")
    | eval start = if(count == 1, null(), strftime(start, "%d.%m.%Y %H:%M:%S"))
    | eval end = strftime(end, "%d.%m.%Y %H:%M:%S")
    | table datetime project_name repository_name user_email user_name start end title
```

---

Copyright © 2022, Michael Bischof - Nextpart Security Intelligence GmbH
