Add-on for JIRA
======================

This is an Add-on for JIRA.

* Download from https://www.github.com/firebus/splunk-jira
* Upgoat at http://apps.splunk.com/app/1438/

## Commands

### jirarest (REST API)

#### Syntax

```
| jirarest MODE OPTIONS
```

#### Modes

* List favorite filters of the configured user

  ```
  | jirarest filters
  ```

* Run a specific filter and return Issues

  ```
  | jirarest issues FILTER_ID
  ```

* Run a JQL search and return Issues.

  ```
  | jirarest jqlsearch JQL_QUERY
  ```

* Run a JQL search and return the all Changes for all matching Issues.
  
  ```
  | jirarest changelog JQL_QUERY
  ```

* List rapidboards or sprints (Greenhopper REST API)

  ```
  | jirarest rapidboards list|all|(RAPIDBOARD_ID [detail sprints|issues])
  ```
  * list will list all scrum boards. This is the default behavior when no argument is provided.
  * all will list all sprints in all scrum boards.
  * RAPIDBOARD_ID will list all sprints in one specific scrum board.
    * "sprints" gives details on the active sprints in the rapidboard.
    * "issues" gives details on the active issues in the board including swimlanes and groupings.
    * Hint: to get issues in a sprint use jqlquery "sprint=sprint_id" after you have found the desired sprint id here with rapidboards.

* Pipe search results into a jqlsearch

  ```
  | search ... | eval foo="WTF-1,WTF-2,WTF-3" | makemv delim=, foo | map search="|jirarest batch JQL_QUERY $foo$"
  ```

  * The JQL_QUERY in the batch command is a partial query that ends with the IN keyword, e.g. "key in"
  * Results piped in from the preceding search will populate the IN clause.
  * Results piped in can be comma- or space- separated
  * This is a little ungainly, but quite powerful if you want to pull a list of JIRA keys from an external source and then get all the Issues from JIRA

#### Options

* show_comments 
  * Shows comments for all Issues returned by main option.
  * Compatible with issues, jqlquery, and batch commands.

* use_internal_field_names
  * By default, pretty names for fields are show. use_internal_field_names outputs internal field names instead.
  * Compatible with issues, jqlquery and batch commands.

* time_field TIME_FIELD
   * Sets _time to the chosen field. If field does not contain a valid, returns 0 Epoch time
   * _time defaults to created if time_field is not set
   * Compatible with issues, jqlquery, and batch commands.

#### Notes

* The rest command can also be called with | jira. 


## Deployment

1. Place the app into $SPLUNK_HOME/etc/apps/jira
2. Create a folder named local, copy default/jira.conf into local, and update with configuration specific to your instance.
3. Copy config.ini.sample to config.ini and update with your authentication credentials

Configure which keys to display in the table with the keys, time_keys, and custom_keys fields.


## Acknowledgements

* App maintained by Russell Uman
* jirarest command written by Fred de Boer
* jirasoap command written by Fred de Boer
* jiraxml command written by Stephen Sorkin and Jeffrey Isenberg
* The Splunk MySQL app was used as a model, and lots of snippets here were stolen from its commands

## Support

Please open an issue on github if you have any trouble with the app, or contact the maintainer through github.
Please feel free to fork and make pull requests if you find a bug that you can fix or have an enhancement to add.