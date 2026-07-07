# Reworking Constants

app_name = "google_workspace_for_splunk"

global_scopes = {"admin_sdk_report": ["https://www.googleapis.com/auth/admin.reports.audit.readonly"],
                 "admin_user_sdk_report": ["https://www.googleapis.com/auth/admin.reports.audit.readonly",
                                           "https://www.googleapis.com/auth/admin.directory.user.readonly",
                                           "https://www.googleapis.com/auth/gmail.readonly",
                                           "https://www.googleapis.com/auth/drive.metadata.readonly"],
                 "admin_usage_report": ["https://www.googleapis.com/auth/admin.reports.usage.readonly"],
                 "analytics": ["https://www.googleapis.com/auth/analytics.readonly"],
                 "directory_user": ["https://www.googleapis.com/auth/admin.directory.user.readonly",
                                    "https://www.googleapis.com/auth/gmail.readonly"],
                 "chromeos_device": [
                     "https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly"],
                 "chrome_browswer": [
                     "https://www.googleapis.com/auth/admin.directory.device.chromebrowsers.readonly"
                 ],
                 "forms": [
                     "https://www.googleapis.com/auth/forms.body.readonly",
                     "https://www.googleapis.com/auth/forms.responses.readonly",
                     "https://www.googleapis.com/auth/drive.readonly"
                 ],
                 "google_drive_metadata": ["https://www.googleapis.com/auth/drive.metadata.readonly"],
                 "bigquery": ["https://www.googleapis.com/auth/bigquery"],
                 "gcp": ["https://www.googleapis.com/auth/cloud-platform"],
                 "gmail": ["https://www.googleapis.com/auth/gmail.send"],
                 "google_drive": ["https://www.googleapis.com/auth/drive.readonly"],
                 "spreadsheets": ["https://www.googleapis.com/auth/spreadsheets"],
                 "classroom": ["https://www.googleapis.com/auth/classroom.courses.readonly",
                               "https://www.googleapis.com/auth/classroom.courses.readonly",
                               "https://www.googleapis.com/auth/classroom.rosters.readonly",
                               "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
                               "https://www.googleapis.com/auth/classroom.announcements.readonly",
                               "https://www.googleapis.com/auth/classroom.guardianlinks.students.readonly"],
                 "alerts": ["https://www.googleapis.com/auth/apps.alerts"],
                 "pubsub": ["https://www.googleapis.com/auth/pubsub"],
                 "vault": ["https://www.googleapis.com/auth/ediscovery"],
                 "language": ["https://www.googleapis.com/auth/cloud-language"],
                 "resources": ["https://www.googleapis.com/auth/cloud-files"],
                 }
