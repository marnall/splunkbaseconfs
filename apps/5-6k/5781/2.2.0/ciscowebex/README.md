# Cisco Webex

Publisher: Splunk <br>
Connector Version: 2.2.0 <br>
Product Vendor: Cisco <br>
Product Name: Cisco Webex <br>
Minimum Product Version: 6.3.0

This app integrates with Cisco Webex to implement investigative and genric actions

## Authentication

This app supports two types of authentication:

### 1. Personal Access Token

- Use your **[Webex Personal Access Token](https://developer.webex.com/docs/getting-your-personal-access-token)**.
- Personal access tokens are valid for **12 hours** after logging into the Developer Portal.

### 2. OAuth

- Use your **Client ID**, **Client Secret**, and required **Scopes**.

#### Steps:

1. **Create a Webex App** at [https://developer.webex.com/my-apps](https://developer.webex.com/my-apps)
1. Choose the app type: **Integration**
1. Set **redirect URI** (for OAuth):
   - You can find it while run the test connectivity. e.g.`https://<your-splunk-soar-url>/rest/handler/ciscowebex_34624d1a-f0ae-47d6-a731-8499d5617cf7/<asset_name>/result`
1. Provide default required scopes to run all actions: `spark:people_read spark:rooms_read spark:messages_write spark:rooms_write spark:memberships_write spark:messages_read meeting:participants_read meeting:schedules_read meeting:recordings_read meeting:schedules_write`.
1. Collect:
   - **Client ID**
   - **Client Secret**
   - Required **Scopes**
1. In Splunk SOAR, create a new asset and provide credentials as per the method selected.

- Webex Developer Portal: [https://developer.webex.com](https://developer.webex.com)
- Webex Scopes: [https://developer.webex.com/docs/integrations](https://developer.webex.com/docs/integrations)

**OAuth Required Scopes per Action are listed below.**

## Supported Actions and Required Scopes

| Action | Description | Required Scopes |
|-----------------------------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| **Test Connectivity** | Verifies the app configuration and connectivity to the Webex API | `spark:people_read`, `spark:rooms_read`, `spark:messages_write`, `spark:rooms_write`, `spark:memberships_write`, `spark:messages_read`, `meeting:participants_read`, `meeting:schedules_read`, `meeting:recordings_read`, and `meeting:schedules_write` |
| **List Rooms** | List Webex rooms (spaces) | `spark:rooms_read`|
| **Get User** | Get user ID from email address | `spark:people_read`, for admin (`spark-admin:people_read`) |
| **Send Message** | Send a message to a user or room | `spark:messages_write`, `spark:rooms_read` (if room name lookup is used) |
| **Create a Room** | Create a new Webex room (space) | `spark:rooms_write` |
| **Add People** | Add a person to a Webex room (as member or moderator) | `spark:memberships_write`, for admin (`spark-admin:people_read`)|
| **Schedule Meeting** | Schedule a Webex meeting with details and invitees | `meeting:schedules_write`, for admin(`meeting:admin_schedule_write`) |
| **Retrieve Meeting Participants** | Retrieve participants in an in-progress or ended Webex meeting | `meeting:participants_read`, for admin(`meeting:admin_participants_read`) |
| **List Messages** | Retrieve a list of messages from a Webex room or 1:1 conversation | `spark:messages_read`, for admin (`spark-admin:messages_read`) |
| **Get Message Details** | Retrieve the details of a specific Webex message by message ID | `spark:messages_read`, for admin (`spark-admin:messages_read`) |
| **Get Meeting Details** | Retrieve details of a specific meeting using meeting ID or meeting number | `meeting:schedules_read`, for admin (`meeting:admin_schedule_read`) |
| **List Users** | List users in your Webex org using filters like email, name, ID, etc. | `spark:people_read`, for admin (`spark-admin:people_read`) to retrieve other user details |
| **Get Recording Details** | Retrieve details of a Webex meeting recording using its recording ID | `meeting:recordings_read`, for admin (`spark-admin:recordings_read`) |
| **AI Meeting Summary** | Retrieve AI-Generated meeting summary and actions items using its recording ID and site url | `meeting:recordings_read`, for admin (`spark-admin:recordings_read`) |

______________________________________________________________________

### If You Have a Free Webex Account

Some features and settings are **not available** for free accounts:

- **Create Room:** You cannot use `isAnnouncementOnly`, `isPublic`, `isLocked`, or `classificationId`.
- **Add People:** You can’t set `isModerator`.
- **List Users:** You may not be able to use `roles` or `orgId`.
- **Schedule Meeting:** The following won’t work: `host`, `adhoc`, `roomId`, `enabledJoinBeforeHost`, `joinBeforeHostMinutes`, `recording`, `publicMeeting` (needs admin), and `sessionTypeId` (webinars only).
- **AI Meeting Summary:** You can't perform this action.

If you want these features, you will need to upgrade to a paid [Webex plan](https://pricing.webex.com/us/en/hybrid-work/meetings/).

### Configuration variables

This table lists the configuration variables required to operate Cisco Webex. These variables are specified when configuring a Cisco Webex asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**authorization_key** | optional | password | Personal Access Token |
**client_id** | optional | string | Client ID |
**client_secret** | optional | password | Client Secret |
**scope** | optional | string | Scopes (Append extra space-seperated scopes which are added during app creation from webex portal) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list rooms](#action-list-rooms) - List webex rooms <br>
[get user](#action-get-user) - Get user ID from e-mail address <br>
[send message](#action-send-message) - Send message to user or room <br>
[create a room](#action-create-a-room) - Create a new Webex room (space) <br>
[add people](#action-add-people) - Add a people to a Webex room (space) as a member or moderator <br>
[schedule meeting](#action-schedule-meeting) - Allows users to schedule a Webex meeting, webinar, or ad-hoc meeting <br>
[retrieve meeting participants](#action-retrieve-meeting-participants) - Retrieve all participants in an in-progress or ended Webex meeting <br>
[list messages](#action-list-messages) - Retrieve a list of messages from a Webex room or 1:1 conversation <br>
[get message details](#action-get-message-details) - Retrieve the details of a specific Webex message by message ID <br>
[get meeting details](#action-get-meeting-details) - Retrieve details of a specific Webex meeting using meeting ID or meeting number <br>
[list users](#action-list-users) - List users in your Webex organization using filters like email, name, ID, roles, or location <br>
[get recording details](#action-get-recording-details) - Retrieve details of a Webex meeting recording using its recording ID <br>
[ai meeting summary](#action-ai-meeting-summary) - Retrieve AI-Generated meeting summary and actions items using its recording ID and site url <br>
[update a room](#action-update-a-room) - Updates details for a room by ID

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list rooms'

List webex rooms

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.created | string | | 2018-01-05T02:43:33.032Z |
action_result.data.\*.creatorId | string | `creater id` | L2lzY69zcBFyazoxL3VzL1BFT1BMRS9iMmMwZjIwMS03NGQyLTRkYTEtYWM0Yi1mNzcEXAMPLE |
action_result.data.\*.id | string | `webex room id` | L2lzY69zcGFylsdovL3VzL1JPT00vMzg2NzFhODAtZjFjMi0xMWU3LTg1OWUtNDMzYWYEXAMPLE |
action_result.data.\*.isLocked | boolean | | True False |
action_result.data.\*.lastActivity | string | | 2018-01-08T21:26:38.851Z 2018-01-16T18:37:12.037Z |
action_result.data.\*.ownerId | string | | |
action_result.data.\*.title | string | | Test Alert Space |
action_result.data.\*.type | string | | group |
action_result.summary.total_rooms | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get user'

Get user ID from e-mail address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email_address** | required | User webex e-mail address | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.email_address | string | `email` | examplemail@test.com |
action_result.data.\*.created | string | | |
action_result.data.\*.created | string | | 2018-01-04T20:46:30.734Z |
action_result.data.\*.displayName | string | | Test User |
action_result.data.\*.emails | string | `email` | examplemail@test.com |
action_result.data.\*.firstName | string | | |
action_result.data.\*.id | string | `webex user id` | L2lzY29zcAByazovL3VzL1690T1BMRS9hMzMGQ4Mi01ZWE0LTQ3OTktOWM3Zi00M2E0MTEXAMPLE |
action_result.data.\*.lastActivity | string | | 2018-01-05T21:04:53.424Z |
action_result.data.\*.lastModified | string | | |
action_result.data.\*.lastName | string | | |
action_result.data.\*.nickName | string | | Test User |
action_result.data.\*.orgId | string | | L2lzY29zcABCazovL3VzL09SR0FOSVpBVElPTi9jb2TEST |
action_result.data.\*.status | string | | inactive |
action_result.data.\*.type | string | | person |
action_result.summary.found_user | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'send message'

Send message to user or room

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint_id** | required | User or Room ID | string | `webex user id` `webex room id` |
**destination_type** | required | Destination Type | string | |
**message** | optional | Message | string | |
**card** | optional | AdaptiveCard format card | string | |
**vault_id** | optional | Vault ID to send file to webex | string | |
**is_markdown** | optional | Is the message Markdown formatted | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.destination_type | string | | room |
action_result.parameter.endpoint_id | string | `webex user id` `webex room id` | L2szY29zcGFyazovLABCVzL1JLT00vODliODk1ZWYtYjk2YS0zMTk0LTlhNDQtNDAxTEST5EXAMPLE |
action_result.parameter.is_markdown | boolean | | True False |
action_result.parameter.message | string | | Compile Test hello room |
action_result.data.\*.created | string | | 2018-01-08T21:27:31.755Z 2018-03-30T18:36:01.210Z |
action_result.data.\*.id | string | `webex message id` | testzcGFyazovLABCVzL1JLT00vODliODk1ZWYtYjk2YS0zMTk0LTlhNDQtNDATEST4MzEXAMPLE |
action_result.data.\*.personEmail | string | `email` | examplemail@test.com |
action_result.data.\*.personId | string | | L2szY29zcGFyazovLABCVzL1JLT00vODliODk1ZWYtYjk2YS0zMTk0TESTNDQtNDAxZTk4MzEXAMPLE |
action_result.data.\*.roomId | string | | L2szY29zcGFyazovLABCVzL1JLT00vODliODk1ZWYtYjk2YS0zMTESTTlhNDQtNDAxZTk4MzEXAMPLE |
action_result.data.\*.roomType | string | | direct group |
action_result.data.\*.text | string | | Compile Test hello room |
action_result.data.\*.toPersonId | string | | L2lzY1zcAByazovL3VzL1HNT1BMRS9hMzllMGQ4Mi01ZWE0LTQ3OTESTWM3Zi00M2E0MTI4MjEXAMPLE |
action_result.summary.message | string | | Message sent successfully |
action_result.message | string | | Message sent successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.card | string | | |
action_result.parameter.vault_id | string | | |

## action: 'create a room'

Create a new Webex room (space)

Type: **generic** <br>
Read only: **False**

<ul><li>Public rooms require a description.</li><li>Announcement mode requires the room to be locked.</li><li>Team rooms cannot be locked.</li><li>Requires permission: <code>spark:rooms_write</code>.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**title** | required | A user-friendly name for the room | string | |
**description** | optional | The description of the space | string | |
**team_id** | optional | The ID for the team with which this room is associated | string | |
**classification_id** | optional | The classification_id for the room | string | |
**is_locked** | optional | Set the space as locked/moderated; creator becomes a moderator | boolean | |
**is_public** | optional | If true, the room is discoverable by anyone in the org; description must be provided | boolean | |
**is_announcement_only** | optional | Sets the space into announcement-only mode | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.classification_id | string | | |
action_result.parameter.description | string | | |
action_result.parameter.is_announcement_only | boolean | | |
action_result.parameter.is_locked | boolean | | |
action_result.parameter.is_public | boolean | | |
action_result.parameter.team_id | string | | |
action_result.parameter.title | string | | |
action_result.data.\*.created | string | | 2025-05-09T09:57:17.803Z |
action_result.data.\*.creatorId | string | | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.description | string | | test |
action_result.data.\*.id | string | `webex room id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.isAnnouncementOnly | boolean | | True False |
action_result.data.\*.isLocked | boolean | | True False |
action_result.data.\*.isPublic | boolean | | True False |
action_result.data.\*.lastActivity | string | | 2025-05-09T09:57:17.803Z |
action_result.data.\*.madePublic | string | | 2025-05-23T04:53:54.268Z |
action_result.data.\*.ownerId | string | `webex user id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.teamId | string | | testzcGFyazovL3VzL1RFQU0vMDM3ZWZlZTAtMtestzc5My0xMWYwLWFhY2EtODM2Mjg3test |
action_result.data.\*.title | string | | test room |
action_result.data.\*.type | string | | group |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'add people'

Add a people to a Webex room (space) as a member or moderator

Type: **generic** <br>
Read only: **False**

Adds a person to a Webex room using their ID or email. You can optionally assign them as a moderator. Requires `spark:memberships_write` scope. Compliance officers cannot add users to empty team spaces.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**room_id** | required | The ID of the room to add the person to | string | `webex room id` |
**person_id** | optional | The ID of the person to add (use either person_id or person_email) | string | `webex user id` |
**person_email** | optional | The email address of the person to add (use either person_email or person_id) | string | `email` |
**is_moderator** | optional | Set to true to make the person a room moderator | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.is_moderator | boolean | | |
action_result.parameter.person_email | string | `email` | |
action_result.parameter.person_id | string | `webex user id` | |
action_result.parameter.room_id | string | `webex room id` | |
action_result.data.\*.created | string | | 2025-05-09T09:58:50.433Z |
action_result.data.\*.id | string | | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.isModerator | boolean | | True False |
action_result.data.\*.isMonitor | boolean | | True False |
action_result.data.\*.isRoomHidden | boolean | | True False |
action_result.data.\*.personDisplayName | string | | TEST USER |
action_result.data.\*.personEmail | string | `email` | example@example.com |
action_result.data.\*.personId | string | `webex user id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.personOrgId | string | `webex org id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.roomId | string | `webex room id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.roomType | string | | group |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'schedule meeting'

Allows users to schedule a Webex meeting, webinar, or ad-hoc meeting

Type: **generic** <br>
Read only: **False**

<ul><li>To create a <strong>public meeting</strong> (<code>public_meeting=true</code>), your Webex admin must turn on this feature. If not, it will show an error.</li><li><strong>OAuth Scopes</strong>: <code>meeting:schedules_write</code>, <code>meeting:admin_schedule_write</code>. Also, make sure the user has the right access (for example, a webinar license if you're creating webinars). <a href="https://developer.webex.com/docs/integrations#scopes" target="_blank">Check required scopes</a></li><li>Use standard time zone names like <code>America/New_York</code> or <code>Asia/Kolkata</code>. This sets the correct time zone for your meeting. If you don’t set it, Webex will use the host’s time zone. <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones" target="_blank">See full list of time zones</a></li><li>If you want the meeting to repeat (daily, weekly, etc.), use the <code>recurrence</code> field. You must write it in a special format called <strong>RFC 5545</strong>.<br />Example: <code>FREQ=WEEKLY;BYDAY=MO,WE,FR</code> (means every Monday, Wednesday, and Friday)<br /><a href="https://developer.webex.com/docs/api/v1/meetings/create-a-meeting" target="_blank">More about recurrence rules</a></li><li>If you're creating an ad-hoc meeting (<code>adhoc=true</code>), you must give a <code>roomId</code> (Webex space ID).<br />In this case, <code>hostEmail</code> will be ignored — the meeting will use the Webex space owner as host.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**title** | required | Title of the meeting (max 128 chars) | string | |
**start** | required | Meeting start time (ISO 8601 format) | string | |
**end** | required | Meeting end time (ISO 8601 format) | string | |
**timezone** | optional | IANA time zone for the meeting (e.g., America/Los_Angeles) | string | |
**description** | optional | Meeting description (max 1300 chars) | string | |
**invitees** | optional | List of emails to invite (comma‑separated) | string | |
**password** | optional | Password to join the meeting | string | |
**send_email** | optional | Whether to email host & invitees | boolean | |
**host_email** | optional | Host email (admin scopes required) | string | |
**scheduled_type** | optional | Type of meeting: meeting, webinar, or personal_room_meeting | string | |
**adhoc** | optional | Create an ad‑hoc (instant) meeting in a room | boolean | |
**room_id** | optional | Room (space) ID for ad‑hoc meeting | string | `webex room id` |
**recurrence** | optional | Meeting series rule (RFC‑2445, e.g. FREQ=DAILY;INTERVAL=1) | string | |
**session_type_id** | optional | Session type ID (required for webinars) | numeric | |
**enabled_auto_record_meeting** | optional | Automatically record when meeting starts | boolean | |
**allow_any_user_to_be_co_host** | optional | Allow any qualified user to be cohost | boolean | |
**enabled_join_before_host** | optional | Allow attendees to join before host | boolean | |
**join_before_host_minutes** | optional | Minutes attendees can join before host (0,5,10,15) | numeric | |
**enable_connect_audio_before_host** | optional | Allow audio connect before host | boolean | |
**enable_automatic_lock** | optional | Automatically lock the meeting after start | boolean | |
**automatic_lock_minutes** | optional | Minutes after start to auto‑lock | numeric | |
**public_meeting** | optional | List on public calendar | boolean | |
**reminder_time** | optional | Minutes before start to send host reminder | numeric | |
**unlocked_meeting_join_security** | optional | How non‑invitees join: allowJoin, allowJoinWithLobby, blockFromJoin | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.adhoc | boolean | | |
action_result.parameter.allow_any_user_to_be_co_host | boolean | | |
action_result.parameter.automatic_lock_minutes | numeric | | |
action_result.parameter.description | string | | |
action_result.parameter.enable_automatic_lock | boolean | | |
action_result.parameter.enable_connect_audio_before_host | boolean | | |
action_result.parameter.enabled_auto_record_meeting | boolean | | |
action_result.parameter.enabled_join_before_host | boolean | | |
action_result.parameter.end | string | | |
action_result.parameter.host_email | string | | |
action_result.parameter.invitees | string | | |
action_result.parameter.join_before_host_minutes | numeric | | |
action_result.parameter.password | string | | |
action_result.parameter.public_meeting | boolean | | |
action_result.parameter.recurrence | string | | |
action_result.parameter.reminder_time | numeric | | |
action_result.parameter.room_id | string | `webex room id` | |
action_result.parameter.scheduled_type | string | | |
action_result.parameter.send_email | boolean | | |
action_result.parameter.session_type_id | numeric | | |
action_result.parameter.start | string | | |
action_result.parameter.timezone | string | | |
action_result.parameter.title | string | | |
action_result.parameter.unlocked_meeting_join_security | string | | |
action_result.data.\*.agenda | string | | 漢字©¬ɸѠ֍۞ਊ௵൬༃ဤᄨᇗኖᏌᔠᛯᜠឦᡤᢻᤐᦪᨃᩔ᪸᭒ᮈᯡᰦ᳀ᴞᵆᵝḈὒ⁇ℰ⅏ⅷ∰⋐⏻サイバーセキュリティインシデント日本標準時⛰⛱⛲⛳⛵✔❤ﬗ╬⎋⌚ ⅍ⅎ€ ₭⁂ᾧ҈₮₯⅏⌛ ⎎☆Ḃ平仮名, ひらがな~ |
action_result.data.\*.allowAnyUserToBeCoHost | boolean | | True False |
action_result.data.\*.allowAuthenticatedDevices | boolean | | True False |
action_result.data.\*.allowFirstUserToBeCoHost | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledAnnotate | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledChatHost | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledChatOtherParticipants | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledChatPresenter | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledContactOperatorPrivately | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledPrintDocument | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledRemoteControl | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledSaveDocument | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledShareContent | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewAnyDocument | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewAnyPage | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewParticipantList | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewThumbnails | boolean | | True False |
action_result.data.\*.audioConnectionOptions.allowAttendeeToUnmuteSelf | boolean | | True False |
action_result.data.\*.audioConnectionOptions.allowHostToUnmuteParticipants | boolean | | True False |
action_result.data.\*.audioConnectionOptions.audioConnectionType | string | | webexAudio |
action_result.data.\*.audioConnectionOptions.enabledAudienceCallBack | boolean | | True False |
action_result.data.\*.audioConnectionOptions.enabledGlobalCallIn | boolean | | True False |
action_result.data.\*.audioConnectionOptions.enabledTollFreeCallIn | boolean | | True False |
action_result.data.\*.audioConnectionOptions.entryAndExitTone | string | | noTone |
action_result.data.\*.audioConnectionOptions.muteAttendeeUponEntry | boolean | | True False |
action_result.data.\*.automaticLockMinutes | numeric | | 20 |
action_result.data.\*.dialInIpAddress | string | | 173.243.2.68 |
action_result.data.\*.enableAutomaticLock | boolean | | True False |
action_result.data.\*.enableConnectAudioBeforeHost | boolean | | True False |
action_result.data.\*.enabledAutoRecordMeeting | boolean | | True False |
action_result.data.\*.enabledBreakoutSessions | boolean | | True False |
action_result.data.\*.enabledJoinBeforeHost | boolean | | True False |
action_result.data.\*.enabledLiveStream | boolean | | True False |
action_result.data.\*.enabledVisualWatermark | boolean | | True False |
action_result.data.\*.enabledWebcastView | boolean | | True False |
action_result.data.\*.end | string | | 2025-05-10T14:24:00Z |
action_result.data.\*.excludePassword | boolean | | True False |
action_result.data.\*.hostDisplayName | string | | test user |
action_result.data.\*.hostEmail | string | | ishans@example.com |
action_result.data.\*.hostKey | string | | 210605 |
action_result.data.\*.hostUserId | string | | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.id | string | `webex meeting id` | test92d8997b4d36bc3ac1893c7ftest8 |
action_result.data.\*.joinBeforeHostMinutes | numeric | | 5 |
action_result.data.\*.maxWebinarAttendeeCapacity | numeric | | 50000 |
action_result.data.\*.meetingNumber | string | | 26600002133 |
action_result.data.\*.meetingOptions.enabledChat | boolean | | True False |
action_result.data.\*.meetingOptions.enabledFileTransfer | boolean | | True False |
action_result.data.\*.meetingOptions.enabledVideo | boolean | | True False |
action_result.data.\*.meetingType | string | | meetingSeries |
action_result.data.\*.panelistPassword | string | | hhQcajkb562 |
action_result.data.\*.password | string | | testdpXhe326 |
action_result.data.\*.phoneAndVideoSystemPanelistPassword | string | | 44722552 |
action_result.data.\*.phoneAndVideoSystemPassword | string | | 97237943 |
action_result.data.\*.publicMeeting | boolean | | True False |
action_result.data.\*.reminderTime | numeric | | 10 |
action_result.data.\*.requireAttendeeLogin | boolean | | True False |
action_result.data.\*.restrictToInvitees | boolean | | True False |
action_result.data.\*.scheduledType | string | | meeting |
action_result.data.\*.sessionTypeId | numeric | | 159 |
action_result.data.\*.simultaneousInterpretation.enabled | boolean | | True False |
action_result.data.\*.sipAddress | string | | 2660000000133@webex.com |
action_result.data.\*.siteUrl | string | | example.webex.com |
action_result.data.\*.start | string | | 2025-05-10T13:24:00Z |
action_result.data.\*.state | string | | active |
action_result.data.\*.telephony.accessCode | string | | 26636572133 |
action_result.data.\*.telephony.callInNumbers.\*.callInNumber | string | | +1-000-525-6800 |
action_result.data.\*.telephony.callInNumbers.\*.label | string | | Call-in toll number (US/Canada) |
action_result.data.\*.telephony.callInNumbers.\*.tollType | string | | toll |
action_result.data.\*.telephony.links.\*.href | string | | /v1/meetings/atest92d8997b4d36bc3ac1893c7ftest/globalCallinNumbers |
action_result.data.\*.telephony.links.\*.method | string | | GET |
action_result.data.\*.telephony.links.\*.rel | string | | globalCallinNumbers |
action_result.data.\*.timezone | string | | UTC |
action_result.data.\*.title | string | | test meeting |
action_result.data.\*.unlockedMeetingJoinSecurity | string | | allowJoin |
action_result.data.\*.webLink | string | | https://example.webex.com/example/j.php?MTID=m6325e89c172b9167381372a0b862a995 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'retrieve meeting participants'

Retrieve all participants in an in-progress or ended Webex meeting

Type: **investigate** <br>
Read only: **True**

Retrieve a list of participants from a specific Webex meeting instance or series

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**meeting_id** | required | Unique identifier of the meeting (not personal room meeting) | string | `webex meeting id` |
**breakout_session_id** | optional | Unique ID of a breakout session in an ended meeting | string | |
**meeting_start_time_from** | optional | Start time to filter meetings (ISO 8601 format) | string | |
**meeting_start_time_to** | optional | End time to filter meetings (ISO 8601 format) | string | |
**host_email** | optional | Email address of the meeting host (admin-only use) | string | `email` |
**join_time_from** | optional | Start of participant join time range (ISO 8601 format) | string | |
**join_time_to** | optional | End of participant join time range (ISO 8601 format) | string | |
**limit** | optional | Max number of participants to return (1–100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.breakout_session_id | string | | |
action_result.parameter.host_email | string | `email` | |
action_result.parameter.join_time_from | string | | |
action_result.parameter.join_time_to | string | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.meeting_id | string | `webex meeting id` | |
action_result.parameter.meeting_start_time_from | string | | |
action_result.parameter.meeting_start_time_to | string | | |
action_result.data.\*.coHost | boolean | | True False |
action_result.data.\*.devices.\*.correlationId | string | | test927a-496a-4678-ac62-bcbdaadctest |
action_result.data.\*.devices.\*.deviceType | string | | mac |
action_result.data.\*.devices.\*.durationSecond | numeric | | 6 |
action_result.data.\*.devices.\*.joinedTime | string | | 2025-05-08T12:40:49Z |
action_result.data.\*.devices.\*.leftTime | string | | 2025-05-08T12:40:55Z |
action_result.data.\*.displayName | string | | test user |
action_result.data.\*.email | string | `email` | example@example.com |
action_result.data.\*.host | boolean | | True False |
action_result.data.\*.hostEmail | string | | example@example.com |
action_result.data.\*.id | string | `webex user id` | testef03e1a49be883320fe35fde314_I_65220test54323715_3118cefb-81e7-492d-8223-1fe0a353test |
action_result.data.\*.invitee | boolean | | True False |
action_result.data.\*.joinedTime | string | | 2025-05-08T12:40:49Z |
action_result.data.\*.leftTime | string | | 2025-05-08T12:40:55Z |
action_result.data.\*.meetingId | string | `webex meeting id` | test2ef03e1a49be883320fe35fde314_I_65220661465432test |
action_result.data.\*.meetingStartTime | string | | 2025-05-08T12:40:49Z |
action_result.data.\*.muted | boolean | | True False |
action_result.data.\*.siteUrl | string | | example.webex.com |
action_result.data.\*.spaceModerator | boolean | | True False |
action_result.data.\*.state | string | | end |
action_result.summary.message | string | | Participants retrieved successfully |
action_result.summary.total_participants | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list messages'

Retrieve a list of messages from a Webex room or 1:1 conversation

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**room_id** | required | The ID of the room to list messages from | string | `webex room id` |
**parent_id** | optional | List messages in a thread by parent message ID | string | `webex message id` |
**before** | optional | List messages sent before a specific date/time (ISO 8601 format) | string | |
**before_message** | optional | List messages sent before a specific message ID | string | |
**limit** | optional | The maximum number of messages to return (default 50, max 100) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.before | string | | |
action_result.parameter.before_message | string | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.parent_id | string | `webex message id` | |
action_result.parameter.room_id | string | `webex room id` | |
action_result.data.\*.created | string | | 2025-05-09T05:37:36.687Z |
action_result.data.\*.html | string | | hello <spark-mention data-object-type="person" data-object-id="TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST">test</spark-mention> |
action_result.data.\*.id | string | `webex message id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.meetingId | string | `webex meeting id` | 9testf03e1a49be883320fe35fde314_I_6522066146543test |
action_result.data.\*.parentId | string | `webex message id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.personEmail | string | `email` | example@example.com |
action_result.data.\*.personId | string | `webex user id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.roomId | string | `webex room id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.roomType | string | | group |
action_result.data.\*.text | string | | hello test |
action_result.summary.message | string | | Messages retrieved successfully |
action_result.summary.total_messages | numeric | | 10 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get message details'

Retrieve the details of a specific Webex message by message ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**message_id** | required | The unique identifier of the message to retrieve | string | `webex message id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.message_id | string | `webex message id` | |
action_result.data.\*.created | string | | 2025-05-09T05:37:36.687Z |
action_result.data.\*.html | string | | hello <spark-mention data-object-type="person" data-object-id="TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST">test</spark-mention> |
action_result.data.\*.id | string | `webex message id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.personEmail | string | `email` | example@example.com |
action_result.data.\*.personId | string | `webex user id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.roomId | string | `webex room id` | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.roomType | string | | group |
action_result.data.\*.text | string | | hello test |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get meeting details'

Retrieve details of a specific Webex meeting using meeting ID or meeting number

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**meeting_id** | required | The unique identifier of the meeting being requested (UUID format) | string | `webex meeting id` |
**host_email** | optional | Email address of the meeting host (for admin-level access) | string | `email` |
**current** | optional | Whether to retrieve only the current scheduled meeting of the series (true or false) | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.current | boolean | | |
action_result.parameter.host_email | string | `email` | |
action_result.parameter.meeting_id | string | `webex meeting id` | |
action_result.data.\*.agenda | string | | |
action_result.data.\*.allowAnyUserToBeCoHost | boolean | | True False |
action_result.data.\*.allowAuthenticatedDevices | boolean | | True False |
action_result.data.\*.allowFirstUserToBeCoHost | boolean | | True False |
action_result.data.\*.attendeeDidJoin | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledAnnotate | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledChatHost | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledChatOtherParticipants | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledChatPresenter | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledContactOperatorPrivately | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledPrintDocument | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledRemoteControl | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledSaveDocument | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledShareContent | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewAnyDocument | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewAnyPage | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewParticipantList | boolean | | True False |
action_result.data.\*.attendeePrivileges.enabledViewThumbnails | boolean | | True False |
action_result.data.\*.audioConnectionOptions.allowAttendeeToUnmuteSelf | boolean | | True False |
action_result.data.\*.audioConnectionOptions.allowHostToUnmuteParticipants | boolean | | True False |
action_result.data.\*.audioConnectionOptions.audioConnectionType | string | | webexAudio |
action_result.data.\*.audioConnectionOptions.enabledAudienceCallBack | boolean | | True False |
action_result.data.\*.audioConnectionOptions.enabledGlobalCallIn | boolean | | True False |
action_result.data.\*.audioConnectionOptions.enabledTollFreeCallIn | boolean | | True False |
action_result.data.\*.audioConnectionOptions.entryAndExitTone | string | | noTone |
action_result.data.\*.audioConnectionOptions.muteAttendeeUponEntry | boolean | | True False |
action_result.data.\*.dialInIpAddress | string | | 103.xx.xx.68 |
action_result.data.\*.enableAutomaticLock | boolean | | True False |
action_result.data.\*.enableConnectAudioBeforeHost | boolean | | True False |
action_result.data.\*.enabledAutoRecordMeeting | boolean | | True False |
action_result.data.\*.enabledBreakoutSessions | boolean | | True False |
action_result.data.\*.enabledJoinBeforeHost | boolean | | True False |
action_result.data.\*.enabledLiveStream | boolean | | True False |
action_result.data.\*.enabledVisualWatermark | boolean | | True False |
action_result.data.\*.end | string | | 2025-05-09T13:20:00Z |
action_result.data.\*.excludePassword | boolean | | True False |
action_result.data.\*.hasChat | boolean | | True False |
action_result.data.\*.hasClosedCaption | boolean | | True False |
action_result.data.\*.hasPolls | boolean | | True False |
action_result.data.\*.hasQA | boolean | | True False |
action_result.data.\*.hasRecording | boolean | | True False |
action_result.data.\*.hasRegistrants | boolean | | True False |
action_result.data.\*.hasRegistration | boolean | | True False |
action_result.data.\*.hasSlido | boolean | | True False |
action_result.data.\*.hasTranscription | boolean | | True False |
action_result.data.\*.hostDidJoin | boolean | | True False |
action_result.data.\*.hostDisplayName | string | | test user |
action_result.data.\*.hostEmail | string | | example@example.com |
action_result.data.\*.hostKey | string | | 889047 |
action_result.data.\*.hostUserId | string | | TESTY29zcGFyazovL3VzL1JPT00vZmRkYmMzYjAtMmNTESTxMWYwLTgwZWItMjllNWE1OTTEST |
action_result.data.\*.id | string | `webex meeting id` | ctest706b64041559c664a83e6bfcf60_20250509Ttest0Z |
action_result.data.\*.isModified | boolean | | True False |
action_result.data.\*.joinBeforeHostMinutes | numeric | | 5 |
action_result.data.\*.meetingNumber | string | | 26620031238 |
action_result.data.\*.meetingOptions.enabledChat | boolean | | True False |
action_result.data.\*.meetingOptions.enabledFileTransfer | boolean | | True False |
action_result.data.\*.meetingOptions.enabledVideo | boolean | | True False |
action_result.data.\*.meetingSeriesId | string | | testa706b64041559c664a83e6btest |
action_result.data.\*.meetingType | string | | scheduledMeeting |
action_result.data.\*.password | string | | 72Xjx9PyYKA |
action_result.data.\*.phoneAndVideoSystemPassword | string | | 72959979 |
action_result.data.\*.publicMeeting | boolean | | True False |
action_result.data.\*.reminderTime | numeric | | 15 |
action_result.data.\*.scheduledMeetingId | string | | 937f2ef03e1a49be883320fe35fde314_20250508T140000Z |
action_result.data.\*.scheduledType | string | | meeting |
action_result.data.\*.sessionTypeId | numeric | | 159 |
action_result.data.\*.simultaneousInterpretation.enabled | boolean | | True False |
action_result.data.\*.sipAddress | string | | 26000031238@webex.com |
action_result.data.\*.siteUrl | string | | example.webex.com |
action_result.data.\*.start | string | | 2025-05-09T12:20:00Z |
action_result.data.\*.state | string | | ready |
action_result.data.\*.telephony.accessCode | string | | 26620031238 |
action_result.data.\*.telephony.callInNumbers.\*.callInNumber | string | | +1-000-025-6800 |
action_result.data.\*.telephony.callInNumbers.\*.label | string | | Call-in toll number (US/Canada) |
action_result.data.\*.telephony.callInNumbers.\*.tollType | string | | toll |
action_result.data.\*.telephony.links.\*.href | string | | /v1/meetings/testa706b64041559c664a83e6btest/globalCallinNumbers |
action_result.data.\*.telephony.links.\*.method | string | | GET |
action_result.data.\*.telephony.links.\*.rel | string | | globalCallinNumbers |
action_result.data.\*.timezone | string | | UTC |
action_result.data.\*.title | string | | Test meeting |
action_result.data.\*.unlockedMeetingJoinSecurity | string | | allowJoin |
action_result.data.\*.webLink | string | | https://example.webex.com/example/j.php?MTID=me0a791a45ee400f06576ed07dd940d3e |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list users'

List users in your Webex organization using filters like email, name, ID, roles, or location

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**email** | optional | Filter people by email address | string | `email` |
**display_name** | optional | Filter people whose name starts with this string | string | |
**id** | optional | Comma-separated list of person IDs to retrieve (max 85) | string | `webex user id` |
**org_id** | optional | List users in this organization (admin only) | string | |
**roles** | optional | Comma-separated list of role IDs to filter by (admin only) | string | |
**calling_data** | optional | Whether to include Webex Calling data (admin only) | boolean | |
**location_id** | optional | List users present in this location (admin only) | string | |
**limit** | optional | Maximum number of people to return (default 100, max varies based on flags) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.calling_data | boolean | | |
action_result.parameter.display_name | string | | |
action_result.parameter.email | string | `email` | |
action_result.parameter.id | string | `webex user id` | |
action_result.parameter.limit | numeric | | |
action_result.parameter.location_id | string | | |
action_result.parameter.org_id | string | | |
action_result.parameter.roles | string | | |
action_result.data.\*.addresses.\*.country | string | | US |
action_result.data.\*.addresses.\*.locality | string | | SAN JOSE |
action_result.data.\*.addresses.\*.postalCode | string | | 95128 |
action_result.data.\*.addresses.\*.region | string | | CALIFORNIA |
action_result.data.\*.addresses.\*.streetAddress | string | | 3098 Test Drive |
action_result.data.\*.addresses.\*.type | string | | work |
action_result.data.\*.avatar | string | | https://test-prod-us-east-2.webexcontent.com/Avtr~V1~1ebtest43-417f-9974-ad72catest/V1~test8f27546e523b2945ea2f7ff36tst141b3544e232718885c17cad0d1~test0570bbc40b193112b2c957test~1600 |
action_result.data.\*.created | string | | 2024-11-08T10:16:05.408Z |
action_result.data.\*.department | string | | 020122475 |
action_result.data.\*.displayName | string | | |
action_result.data.\*.emails | string | `email` | |
action_result.data.\*.extension | string | | 3432432 |
action_result.data.\*.firstName | string | | User |
action_result.data.\*.id | string | `webex user id` | |
action_result.data.\*.invitePending | boolean | | True False |
action_result.data.\*.lastActivity | string | | 2025-05-22T08:00:26.197Z |
action_result.data.\*.lastModified | string | | 2025-04-15T01:50:15.733Z |
action_result.data.\*.lastName | string | | Test |
action_result.data.\*.locationId | string | | Y2lzY29zcGFyazovL3VzL0xPQ0FUSU9OL2YzYjJkYmI3LWQ3MTQtNGM5YS05OTkyLWVmMjA0NWNkMmQwZA |
action_result.data.\*.loginEnabled | boolean | | True False |
action_result.data.\*.manager | string | | Test User |
action_result.data.\*.managerId | string | | test29zcGFyazovL3VzL1BFT1BMRS8wMDI3MjIrtestTJjLTQzM2QtODA5Yy05YWJmNWZiNDtest |
action_result.data.\*.nickName | string | | User |
action_result.data.\*.orgId | string | `webex org id` | |
action_result.data.\*.phoneNumbers.\*.primary | boolean | | True False |
action_result.data.\*.phoneNumbers.\*.type | string | | work |
action_result.data.\*.phoneNumbers.\*.value | string | | +1 000-895-000 |
action_result.data.\*.pronouns.value | string | | He/Him/His |
action_result.data.\*.pronouns.visibility | string | | Internal |
action_result.data.\*.roles | string | | |
action_result.data.\*.sipAddresses.\*.primary | boolean | | True False |
action_result.data.\*.sipAddresses.\*.type | string | | personal-room |
action_result.data.\*.sipAddresses.\*.value | string | | 4229032891@sademo2ci.dmz.webex.com |
action_result.data.\*.status | string | | |
action_result.data.\*.timeZone | string | | Asia/Shanghai |
action_result.data.\*.title | string | | Software Engineer [C] |
action_result.data.\*.type | string | | person |
action_result.data.\*.userName | string | | example@example.com |
action_result.summary.message | string | | |
action_result.summary.total_people | numeric | | 1 |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get recording details'

Retrieve details of a Webex meeting recording using its recording ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**recording_id** | optional | Unique identifier of the Webex recording. | string | `webex recording id` |
**meeting_id** | optional | Unique identifier of the Webex meeting. | string | `webex meeting id` |
**host_email** | optional | Email address of the meeting host (admin only). | string | `email` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success |
action_result.parameter.host_email | string | `email` | |
action_result.parameter.meeting_id | string | `webex meeting id` | |
action_result.parameter.recording_id | string | `webex recording id` | test06506faa48c790592a4198c3test |
action_result.data.\*.createTime | string | | 2025-05-22T08:31:19Z |
action_result.data.\*.downloadUrl | string | | https://company.webex.com/siteurl/lsr.php?RCID=1a417c966testaef288e9043adatest |
action_result.data.\*.durationSeconds | numeric | | 219 |
action_result.data.\*.format | string | | MP4 |
action_result.data.\*.hostEmail | string | | example@example.com |
action_result.data.\*.id | string | `webex recording id` | test06506faa48c790592a4198c3test |
action_result.data.\*.meetingId | string | | test5560719471599d7test2a4c1b72_I_6547053376test |
action_result.data.\*.meetingSeriesId | string | | test5560719471599d76418test |
action_result.data.\*.password | string | | testpass |
action_result.data.\*.playbackUrl | string | `url` | https://company.webex.com/siteurl/ldr.php?RCID=testcc66c2ee8536aabdd0ec607test |
action_result.data.\*.scheduledMeetingId | string | | test60719471599d764182a4c1b7test250522T150000Z |
action_result.data.\*.serviceType | string | | MeetingCenter |
action_result.data.\*.shareToMe | boolean | | False |
action_result.data.\*.siteUrl | string | | company.webex.com |
action_result.data.\*.sizeBytes | numeric | | 1067115 |
action_result.data.\*.status | string | | available |
action_result.data.\*.temporaryDirectDownloadLinks.audioDownloadLink | string | | https://company.dmz.webex.com/nbr/MultiThreadDownloadServlet/audio.mp3?siteid=00240&recordid=197000062& |
action_result.data.\*.temporaryDirectDownloadLinks.expiration | string | | 2025-05-22T13:44:50Z |
action_result.data.\*.temporaryDirectDownloadLinks.recordingDownloadLink | string | `url` | https://company.dmz.webex.com/nbr/MultiThreadDownloadServlet?siteid=00240&recordid=197000062 |
action_result.data.\*.temporaryDirectDownloadLinks.transcriptDownloadLink | string | `url` | https://company.dmz.webex.com/nbr/MultiThreadDownloadServlet/transcript.txt?siteid=00240&recordid=197000062&confid=6547000000000001771&from=MBS |
action_result.data.\*.timeRecorded | string | | 2025-05-22T08:23:05Z |
action_result.data.\*.topic | string | | soar test-20250522 0829-1 |
action_result.summary.message | string | | Recording details retrieved successfully |
action_result.message | string | | Message: Recording details retrieved successfully, Status code: False |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'ai meeting summary'

Retrieve AI-Generated meeting summary and actions items using its recording ID and site url

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**recording_id** | required | Unique identifier of the Webex recording. | string | `webex recording id` |
**site_url** | required | Unique identifier of the Webex recording.eg: company.webex.com | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | |
action_result.parameter.recording_id | string | `webex recording id` | |
action_result.parameter.site_url | string | | |
action_result.data.\*.actionItems | string | `webex meeting actions items` | AI-Generated actions items retrieved successfully |
action_result.data.\*.actions_items | string | | AI-Generated actions items retrieved successfully |
action_result.data.\*.recordingId | string | `webex recording id` | test06506faa48c790592a4198c3test |
action_result.data.\*.recordingName | string | | test recording |
action_result.data.\*.suggestedNote | string | `webex meeting notes` | AI-Generated meeting summary and actions items retrieved successfully |
action_result.data.\*.summary | string | | AI-Generated meeting summary and actions items retrieved successfully |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update a room'

Updates details for a room by ID

Type: **generic** <br>
Read only: **False**

Specify the room ID in the room_id parameter in the URI.
A space can only be put into announcement mode when it is locked.
Any space participant or compliance officer can convert a space from public to private. Only a compliance officer can convert a space from private to public and only if the space is classified with the lowest category (usually public), and the space has a description.
To remove a description please use a space character by itself.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**room_id** | required | The unique identifier for the room. example = "Y2lzY29zcGFyazovL3VzL1JPT00vYmJjZWIxYWQtNDNmMS0zYjU4LTkxNDctZjE0YmIwYzRkMTU0" | string | |
**title** | required | A user-friendly name for the room. | string | |
**description** | optional | The description of the space. | string | |
**team_id** | optional | The teamId to which this space should be assigned. Only unowned spaces can be assigned to a team. Assignment between teams is unsupported. | string | |
**classification_id** | optional | The classification_id for the room | string | |
**is_announcement_only** | optional | Sets the space into announcement-only mode. The room must be locked to be set to announcement-only mode. | string | |
**is_locked** | optional | Set the space as locked/moderated and the creator becomes a moderator | string | |
**is_public** | optional | The room is public and therefore discoverable within the org. Anyone can find and join that room. When true the description must be filled in. | string | |
**is_read_only** | optional | A compliance officer can set a direct room as read-only, which will disallow any new information exchanges in this space, while maintaing historical data. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.room_id | string | | |
action_result.parameter.description | string | | |
action_result.parameter.team_id | string | | |
action_result.parameter.title | string | | |
action_result.parameter.is_locked | string | | |
action_result.parameter.is_public | string | | |
action_result.parameter.is_read_only | string | | |
action_result.parameter.is_announcement_only | string | | |
action_result.parameter.classification_id | string | | |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.\*.data.\*.id | string | | |
action_result.data.\*.\*.data.\*.type | string | | |
action_result.data.\*.\*.data.\*.title | string | | |
action_result.data.\*.\*.data.\*.created | string | | |
action_result.data.\*.\*.data.\*.ownerId | string | | |
action_result.data.\*.\*.data.\*.isLocked | boolean | | |
action_result.data.\*.\*.data.\*.isPublic | boolean | | |
action_result.data.\*.\*.data.\*.creatorId | string | | |
action_result.data.\*.\*.data.\*.isReadOnly | boolean | | |
action_result.data.\*.\*.data.\*.description | string | | |
action_result.data.\*.\*.data.\*.lastActivity | string | | |
action_result.data.\*.\*.status | string | | |
action_result.data.\*.\*.message | string | | |
action_result.data.\*.\*.parameter.title | string | | |
action_result.data.\*.\*.parameter.context.guid | string | | |
action_result.data.\*.\*.parameter.context.artifact_id | numeric | | |
action_result.data.\*.\*.parameter.room_id | string | | |
action_result.data.\*.\*.parameter.is_locked | boolean | | |
action_result.data.\*.\*.parameter.is_public | boolean | | |
action_result.data.\*.\*.parameter.description | string | | |
action_result.data.\*.\*.parameter.is_read_only | boolean | | |
action_result.parameter.classification_id | string | | |
action_result.parameter.is_announcement_only | string | | |

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
