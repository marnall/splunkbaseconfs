# Microsoft Entra ID Group Lookup Add-on for Splunk

This Splunk Cloud compatible add-on provides an external lookup named `entra_id_group_membership`. Given a user principal name or Microsoft Entra object ID in the `entra_user` field, it returns all Microsoft Entra ID groups that user belongs to.

By default the lookup uses Microsoft Graph `transitiveMemberOf` so nested group membership is included. Set `membership_type = direct` to use `memberOf` instead.

## Requirements

- Splunk Cloud Platform or Splunk Enterprise with Python 3 external lookup support.
- A Microsoft Entra app registration using client credentials.
- Microsoft Graph application permission `User.Read.All`.
- Microsoft Graph application permission `GroupMember.Read.All` or `Directory.Read.All` for complete group membership data.
- Admin consent granted for the Microsoft Graph application permission.

## Configure

Open the app setup page in Splunk Web and enter:

- Tenant ID
- Client ID
- Client secret
- Membership type
- Authority and Graph hosts

The setup page stores non-secret settings in `local/entra_id_lookup.conf` and stores the client secret with Splunk native secret management through the `storage/passwords` REST endpoint. The secret is stored with:

- Realm: `TA-entra-id-group-lookup`
- Name: `client_secret`

Equivalent non-secret settings:

```ini
[graph]
tenant_id = <tenant-id>
client_id = <app-client-id>
secret_realm = TA-entra-id-group-lookup
secret_name = client_secret
membership_type = transitive
```

For Splunk Cloud, upload this add-on as a private app and complete setup through Splunk Web. Do not put client secrets in `.conf` files.

## Usage

Lookup a single user:

```spl
| makeresults
| eval entra_user="alice@example.com"
| lookup entra_id_group_membership entra_user
```

Lookup users from search results:

```spl
index=identity sourcetype=users
| lookup entra_id_group_membership entra_user OUTPUT group_id group_display_name group_mail group_security_enabled group_mail_enabled group_types group_membership_type error
```

Because `max_matches = 0`, the lookup can return multiple output rows for each input user.

## Output fields

- `entra_user`: input user principal name or object ID.
- `group_id`: Entra group object ID.
- `group_display_name`: Entra group display name.
- `group_mail`: group mail address when present.
- `group_security_enabled`: `true` or `false`.
- `group_mail_enabled`: `true` or `false`.
- `group_types`: semicolon-separated Graph `groupTypes` values.
- `group_membership_type`: `transitive` or `direct`.
- `error`: per-row error message if Graph lookup fails.

## Package

From the directory containing `TA-entra-id-group-lookup`:

```sh
tar --exclude='*/local/entra_id_lookup.conf' -czf TA-entra-id-group-lookup-1.0.0.tar.gz TA-entra-id-group-lookup
```

Do not include real secrets in source control or shared app archives.

## References

- Splunk external lookups require scripts to read incomplete CSV from `stdin` and write completed CSV to `stdout`: https://docs.splunk.com/Documentation/SplunkCloud/latest/Knowledge/DefineanexternallookupinSplunkWeb
- Splunk `transforms.conf` external lookup settings: https://docs.splunk.com/Documentation/Splunk/9.4.2/Admin/Transformsconf
- Splunk Cloud compatible setup pages: https://www.splunk.com/en_us/blog/tips-and-tricks/enable-first-run-app-configuration-with-setup-pages.html
- Microsoft Graph user transitive group membership endpoint: https://learn.microsoft.com/en-us/graph/api/user-list-transitivememberof
