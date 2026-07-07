## Port Details

The app uses HTTPS protocol for communicating with Snowflake. Below are the default ports used by
the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| https | tcp | 443 |

## Roles

Roles are used by Snowflake to **control access to objects** within the organization and allow users
to perform actions against those objects. Users can have several roles granted to them, and can also
have a default role assigned. Since a user is allowed to switch roles during a session in order to
have the appropriate permissions to perform certain actions, the Snowflake app accomodates this by
having an optional 'role' parameter in each of the actions. If this parameter is left blank, the
default role assigned to the user will be used.
