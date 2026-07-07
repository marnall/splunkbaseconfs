## User Roles

Make sure you have assigned proper roles to a user you are using to perform various actions on
Splunk ITSI. Refer to this Splunk
[Documentation](https://docs.splunk.com/Documentation/ITSI/4.13.0/Configure/UsersRoles) for more
details on configuring users and roles in Splunk ITSI.

## Playbook Backward Compatibility

- The parameters have been modified in the below-existing action. Hence, it is requested to update
  existing playbooks created in the earlier versions of the app by re-inserting | modifying |
  deleting the corresponding action blocks.

  - Close Episode - Below parameters have been removed. It is advised to use the 'break episode'
    action to break the episode by closing it.

    - break_episode
    - itsi_policy_id

  - Add Episode Ticket - Below parameter have been modified.

    - The parameter 'custom_ticketing_system_name' has been added
    - A new value 'New Custom Ticketing System' has been added in the 'ticket_system'
      parameter to create tickets in the custom ticketing system

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Splunk ITSI server. Below are the
default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |
