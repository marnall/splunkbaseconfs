URL
The url where the t-Triage backend is actually running (e.g. http://localhost:8088)

LOGS PATTERN
A conversion pattern is composed of literal text and format control expressions called conversion specifiers. Each conversion specifier starts with a percent sign '%' and is followed by optional format modifiers, a conversion word and optional parameters between braces. The conversion word controls the data field to convert, e.g. logger name, level, date or thread name. If you are using Logback, you can find this pattern between the <Pattern> and </Pattern> tags in the logback.xml file.

PACKAGE NAMES
These are the package names where you want to get the events from. If you want to inspect multiple package names, use a comma (,) to separate them. For example, 'com.clarolab,com.google'.

CLIENT ID and SECRET ID
The client ID and the secret ID are tokens generated in the backend to authenticate the requests.

---------------

When pushing a new version to Splunkbase:

1) Copy all the content of the repository in a directory called "ttriage_alert"
2) Delete the .git directory
3) Compress the directory into a .tar.gz file
4) Upload to Splunkbase