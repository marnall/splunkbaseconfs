This custom alert action
send a customized message to a LINE talk room
based on a triggered alert action in Splunk.

Note - This alert action integrates against the LINE Notify incoming webhook api
https://notify-bot.line.me/

# Installation

App installation requires admin priviledges.

* Navigate to "Manage apps" and click "Install app from file"
* Upload the app bundle

# Configuration

## Set LINE Notify access token

You should get an access token for LINE Notify API.
See also

  * https://notify-bot.line.me/doc/
  * https://www.smilevision.co.jp/blog/tsukatte01/ (Japanese)

Navigate to "App" -> "LINE alert for Splunk"

On the Add-on Settings tab you'll want to supply an access token.
You can obtain this URL by configuring a custom integration for your LINE Notify developer site.

For more information see https://notify-bot.line.me/

And also, you can configure proxy and logging settings.

# LICENSE

[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)

