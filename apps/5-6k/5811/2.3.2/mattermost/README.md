# Mattermost

Publisher: Splunk <br>
Connector Version: 2.3.2 <br>
Product Vendor: Mattermost <br>
Product Name: Mattermost <br>
Minimum Product Version: 6.3.0

This app integrates with Mattermost to support various investigative actions

### Configuration variables

This table lists the configuration variables required to operate Mattermost. These variables are specified when configuring a Mattermost asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server_url** | required | string | Server URL (e.g. http://10.10.10.10:8080) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**personal_token** | optional | password | Personal token |
**client_id** | optional | string | Client ID |
**client_secret** | optional | password | Client secret |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list users](#action-list-users) - List users of a team <br>
[upload file](#action-upload-file) - Upload file to a channel <br>
[send message](#action-send-message) - Send a message to a channel <br>
[list posts](#action-list-posts) - List posts of a channel <br>
[list channels](#action-list-channels) - List public and private channels of a team <br>
[list teams](#action-list-teams) - List teams

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list users'

List users of a team

Type: **investigate** <br>
Read only: **True**

While listing users from a specific team, the user should have created the team or be a member of that team.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team** | optional | ID or name of the team | string | `mattermost team` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.team | string | `mattermost team` | test-team |
action_result.data.\*.auth_data | string | | |
action_result.data.\*.auth_service | string | | |
action_result.data.\*.create_at | numeric | | 1535004134292 |
action_result.data.\*.delete_at | numeric | | 0 |
action_result.data.\*.email | string | `email` | test.user@mattermost.com |
action_result.data.\*.email_verified | boolean | | True False |
action_result.data.\*.failed_attempts | numeric | | 0 |
action_result.data.\*.first_name | string | | test |
action_result.data.\*.id | string | | pyx8sqe7zfn1dpmtd1s3qzqhfr |
action_result.data.\*.last_name | string | | user |
action_result.data.\*.last_password_update | numeric | | 0 |
action_result.data.\*.last_picture_update | numeric | | 0 |
action_result.data.\*.locale | string | | en |
action_result.data.\*.mfa_active | boolean | | True False |
action_result.data.\*.nickname | string | | test |
action_result.data.\*.notify_props | string | | |
action_result.data.\*.position | string | | |
action_result.data.\*.props | string | | |
action_result.data.\*.roles | string | | system_user system_user_access_token system_post_all |
action_result.data.\*.timezone.automaticTimezone | string | | |
action_result.data.\*.timezone.manualTimezone | string | | |
action_result.data.\*.timezone.useAutomaticTimezone | string | | true |
action_result.data.\*.update_at | numeric | | 1535105717458 |
action_result.data.\*.username | string | `user name` | test.user |
action_result.data.\*.disable_welcome_email | boolean | | |
action_result.summary.total_users | numeric | | 9 |
action_result.message | string | | Total users: 9 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'upload file'

Upload file to a channel

Type: **generic** <br>
Read only: **False**

User can upload files to only those channels which user has created or is a member of.<br><br>The default value for the <b>message</b> parameter is <b>Phantom file upload</b>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team** | required | ID or name of the team | string | `mattermost team` |
**channel** | required | ID or name of the channel | string | `mattermost channel` |
**vault_id** | required | Vault ID | string | `vault id` `sha1` |
**message** | optional | Message to send | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.channel | string | `mattermost channel` | town-square |
action_result.parameter.message | string | | hi |
action_result.parameter.team | string | `mattermost team` | test-team |
action_result.parameter.vault_id | string | `vault id` `sha1` | c8f39b293cbc5dfb9e61140a36a1685adea492e2 |
action_result.data.\*.channel_id | string | `mattermost channel` | ofond1t88jbr8e6cbwb7ogk98h |
action_result.data.\*.create_at | numeric | | 1535533720541 |
action_result.data.\*.delete_at | numeric | | 0 |
action_result.data.\*.edit_at | numeric | | 1535533798521 |
action_result.data.\*.file_ids | string | | 1ioo54wdtpnq7eddp9yc5jikhy |
action_result.data.\*.hashtags | string | | |
action_result.data.\*.id | string | | uinosfs9a3r9dgay15epdn39qy |
action_result.data.\*.is_pinned | boolean | | True False |
action_result.data.\*.message | string | | Upload file |
action_result.data.\*.original_id | string | | g9rit1zsx3ngzbs1srtx8tu5fe |
action_result.data.\*.parent_id | string | | uinosfs9a3r9dgay15epdn39qy |
action_result.data.\*.pending_post_id | string | | g9rit1zsx3ngzbs1srtx8tu5fe |
action_result.data.\*.root_id | string | | uinosfs9a3r9dgay15epdn39qy |
action_result.data.\*.type | string | | |
action_result.data.\*.update_at | numeric | | 1535533720541 |
action_result.data.\*.user_id | string | | nj9wemswb7f4zykdetw9egbwuo |
action_result.data.\*.metadata.files.\*.id | string | | |
action_result.data.\*.metadata.files.\*.name | string | | |
action_result.data.\*.metadata.files.\*.size | numeric | | |
action_result.data.\*.metadata.files.\*.width | numeric | | |
action_result.data.\*.metadata.files.\*.height | numeric | | |
action_result.data.\*.metadata.files.\*.post_id | string | | |
action_result.data.\*.metadata.files.\*.user_id | string | | |
action_result.data.\*.metadata.files.\*.create_at | numeric | | |
action_result.data.\*.metadata.files.\*.delete_at | numeric | | |
action_result.data.\*.metadata.files.\*.extension | string | | |
action_result.data.\*.metadata.files.\*.mime_type | string | | |
action_result.data.\*.metadata.files.\*.update_at | numeric | | |
action_result.data.\*.metadata.files.\*.channel_id | string | | |
action_result.data.\*.metadata.files.\*.mini_preview | string | | |
action_result.data.\*.metadata.files.\*.has_preview_image | boolean | | |
action_result.data.\*.reply_count | numeric | | |
action_result.data.\*.last_reply_at | numeric | | |
action_result.data.\*.metadata.files.\*.remote_id | string | | |
action_result.data.\*.participants | string | | |
action_result.summary | string | | |
action_result.message | string | | File uploaded successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'send message'

Send a message to a channel

Type: **generic** <br>
Read only: **False**

User can send message to only those channels which user has created or is a member of the team.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team** | required | ID or name of the team | string | `mattermost team` |
**channel** | required | ID or name of the channel | string | `mattermost channel` |
**message** | required | Message to send | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.channel | string | `mattermost channel` | test2-user-channel |
action_result.parameter.message | string | | Hey, guys how r u? |
action_result.parameter.team | string | `mattermost team` | privy-chantest |
action_result.data.\*.channel_id | string | `mattermost channel` | 9fm7epgq9b8x3ekb3frhid5kaw |
action_result.data.\*.create_at | numeric | | 1535458197064 |
action_result.data.\*.delete_at | numeric | | 0 |
action_result.data.\*.edit_at | numeric | | 1535458199241 |
action_result.data.\*.hashtags | string | | |
action_result.data.\*.id | string | | g9rit1zsx3ngzbs1srtx8tu5fe |
action_result.data.\*.is_pinned | boolean | | True False |
action_result.data.\*.message | string | | Hey, guys how r u? |
action_result.data.\*.original_id | string | | uinosfs9a3r9dgay15epdn39qy |
action_result.data.\*.parent_id | string | | g9rit1zsx3ngzbs1srtx8tu5fe |
action_result.data.\*.pending_post_id | string | | uinosfs9a3r9dgay15epdn39qy |
action_result.data.\*.root_id | string | | g9rit1zsx3ngzbs1srtx8tu5fe |
action_result.data.\*.type | string | | |
action_result.data.\*.update_at | numeric | | 1535458197064 |
action_result.data.\*.user_id | string | | hrfxwdb7gtdjzbzqscix7edyeh |
action_result.data.\*.reply_count | numeric | | |
action_result.data.\*.last_reply_at | numeric | | |
action_result.data.\*.participants | string | | |
action_result.summary | string | | |
action_result.message | string | | Message sent successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list posts'

List posts of a channel

Type: **investigate** <br>
Read only: **True**

Users can only list the posts of channels they have created or are members of.<br> If &quotstart_time&quot or &quotend_time&quot is specified, the action will also list the deleted post(s) within the specified time.<br>If only &quotstart_time&quot is given then the current time would be taken as &quotend_time&quot.<br>If only &quotend_time&quot is given then all the posts before that time would be displayed.<br>The timestamp should be entered in <b>YYYY-MM-DD</b> or a valid &quotISO 8601 timestamp&quot format.<br>Some examples of valid time formats are:<ul><li>2018-09-24</li><li>2018-09-23T14:40:44Z</li><li>2018-09-23T14:40:44+05:30</li><li>2020-08-30T01:45:36.123Z</li><li>2021-12-13T21:20:37.593194+05:30</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team** | required | ID or name of the team | string | `mattermost team` |
**channel** | required | ID or name of the channel | string | `mattermost channel` |
**start_time** | optional | Start time in formatted timestamp | string | |
**end_time** | optional | End time in formatted timestamp | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.channel | string | `mattermost channel` | test2-second-channel |
action_result.parameter.end_time | numeric | | 1535007904568 |
action_result.parameter.start_time | numeric | | 1535007703337 |
action_result.parameter.team | string | `mattermost team` | test-team |
action_result.data.\*.channel_id | string | `mattermost channel` | ectpw8kdeir4589wu61ijp77tc |
action_result.data.\*.create_at | numeric | | 1541079654322 |
action_result.data.\*.delete_at | numeric | | 0 |
action_result.data.\*.edit_at | numeric | | 1535007704567 |
action_result.data.\*.file_ids | string | | e4yq14jxd3ra5pmcsjeqjw3j7o |
action_result.data.\*.hashtags | string | | |
action_result.data.\*.id | string | | rb19t6ggfj81bk1txxtcw13kir |
action_result.data.\*.is_pinned | boolean | | True False |
action_result.data.\*.message | string | | Test |
action_result.data.\*.original_id | string | | uinosfs9a3r9dgay15epdn39qy |
action_result.data.\*.parent_id | string | | fsn1bn4nwjdwpmbuqch5fp9xnh |
action_result.data.\*.pending_post_id | string | | g9rit1zsx3ngzbs1srtx8tu5fe |
action_result.data.\*.props.addedUsername | string | `user name` | test-name |
action_result.data.\*.props.username | string | `user name` | admin |
action_result.data.\*.root_id | string | | fsn1bn4nwjdwpmbuqch5fp9xnh |
action_result.data.\*.type | string | | system_join_channel |
action_result.data.\*.update_at | numeric | | 1541079654322 |
action_result.data.\*.user_id | string | | zxutg6e6ibgyxjmpee7wjsmc5a |
action_result.data.\*.reply_count | numeric | | |
action_result.data.\*.last_reply_at | numeric | | |
action_result.data.\*.metadata.files.\*.id | string | | |
action_result.data.\*.metadata.files.\*.name | string | | |
action_result.data.\*.metadata.files.\*.size | numeric | | |
action_result.data.\*.metadata.files.\*.width | numeric | | |
action_result.data.\*.metadata.files.\*.height | numeric | | |
action_result.data.\*.metadata.files.\*.post_id | string | | |
action_result.data.\*.metadata.files.\*.user_id | string | | |
action_result.data.\*.metadata.files.\*.create_at | numeric | | |
action_result.data.\*.metadata.files.\*.delete_at | numeric | | |
action_result.data.\*.metadata.files.\*.extension | string | | |
action_result.data.\*.metadata.files.\*.mime_type | string | | |
action_result.data.\*.metadata.files.\*.update_at | numeric | | |
action_result.data.\*.metadata.files.\*.channel_id | string | | |
action_result.data.\*.metadata.files.\*.mini_preview | string | | |
action_result.data.\*.metadata.files.\*.has_preview_image | boolean | | |
action_result.data.\*.participants | string | | |
action_result.data.\*.metadata.files.\*.remote_id | string | | |
action_result.summary.total_posts | numeric | | 5 |
action_result.message | string | | Total posts: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list channels'

List public and private channels of a team

Type: **investigate** <br>
Read only: **True**

A user can view only those channels of a team which he is a member of.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**team** | required | ID or name of the team | string | `mattermost team` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.team | string | `mattermost team` | privy-chantest |
action_result.data.\*.create_at | numeric | | 1535370158299 |
action_result.data.\*.creator_id | string | | |
action_result.data.\*.delete_at | numeric | | 0 |
action_result.data.\*.display_name | string | | Off-Topic |
action_result.data.\*.extra_update_at | numeric | | 0 |
action_result.data.\*.header | string | | |
action_result.data.\*.id | string | `mattermost channel` | bm5dwbhditgxxxd5z4qkawgxha |
action_result.data.\*.last_post_at | numeric | | 1535370232524 |
action_result.data.\*.name | string | `mattermost channel` | off-topic |
action_result.data.\*.props | string | | |
action_result.data.\*.purpose | string | | |
action_result.data.\*.scheme_id | string | | |
action_result.data.\*.team_id | string | `mattermost team` | suico8q897yyiraqdekxspfjma |
action_result.data.\*.total_msg_count | numeric | | 0 |
action_result.data.\*.type | string | | O |
action_result.data.\*.update_at | numeric | | 1535370158299 |
action_result.data.\*.total_msg_count_root | numeric | | |
action_result.data.\*.team_name | string | | |
action_result.data.\*.team_update_at | numeric | | |
action_result.data.\*.team_display_name | string | | |
action_result.data.\*.shared | string | | |
action_result.data.\*.policy_id | string | | |
action_result.data.\*.group_constrained | string | | |
action_result.summary.total_channels | numeric | | 6 |
action_result.message | string | | Total channels: 6 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list teams'

List teams

Type: **investigate** <br>
Read only: **True**

While creating a team, the user should have set &quotAllow any user with an account on this server to join this team&quot under <b>Team Settings</b> to <b>YES</b> to allow the team to be displayed for all users.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.allow_open_invite | boolean | | True False |
action_result.data.\*.allowed_domains | string | `domain` | example.com |
action_result.data.\*.company_name | string | | |
action_result.data.\*.create_at | numeric | | 1534856540543 |
action_result.data.\*.delete_at | numeric | | 0 |
action_result.data.\*.description | string | | |
action_result.data.\*.display_name | string | | test2 sample |
action_result.data.\*.email | string | `email` | sampleteam@mattermost.com |
action_result.data.\*.id | string | `mattermost team` | 396afxwqzbgruxdkft7d8wo5qw |
action_result.data.\*.invite_id | string | | xo3gnntbfbg5bnirx7zi1uqujc |
action_result.data.\*.name | string | `mattermost team` | test2-sample |
action_result.data.\*.scheme_id | string | | |
action_result.data.\*.type | string | | O |
action_result.data.\*.update_at | numeric | | 1534918716675 |
action_result.data.\*.policy_id | string | | |
action_result.data.\*.group_constrained | string | | |
action_result.summary.total_teams | numeric | | 7 |
action_result.message | string | | Total teams: 7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
