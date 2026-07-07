OVERVIEW
===========
Welcome to the Splunk Dev for All app! This app provides you with working snippets of content to make it easier to use SplunkJS, Splunk Python, and related capabilities such as some of the internals of Splunk. This app contains 30+ pre-packaged working code samples that you can put together to turn your Splunk dashboards into real applications with great user experience, more interactivity, and a richer feel. In addition, there are pointers to many places where you can learn more, or see the samples working in action.

This app pairs with a talk at .conf18 by David Veuve and Dave Herrald: DEV1545 - Go From Dashboards to Applications With Ease: SplunkJS And Splunk Python for Non-Developers -- catch us in Orlando!

# Installation
Installation of this app is recommended only in development environments, as it does ship with a scripted input (though with minimal data ingest). There are no known issues installing alongside other apps and all techniques in the app have been tested in broader scenarios, but none the less the app is intended for developers and shouldn't live alongside everything you expose to your entire user community.

# Contents
### Guidance
* Setting Up Your Development Environment: When you're getting started developing on Splunk, there are a few key things that you should know. Read through this for the benefit of the experience of many people to help you start building right!
* Powerful Third Party (and jQuery) Plug-Ins: Plugins can help you accomplish more, more quickly, and make your dashboard feel more like a real application. See what our favorites are, and pick up a few good tips regardless.
* Splunk Style Guidelines (and Icons and such): Splunk ships with a style guide include icons, working HTML for form elements, modals, and all kinds of other capabilities. If you've never looked at this, it will help you avoid lots of work and have consistency with the general Splunk feel.
* Logging and Debugging: Getting visibility into what's happening with your code is key for any kind of development. How have we done this?

### Basics
* Including a JS file: Hello World, SplunkJS Style
* Running a Search from Javascript: The foundation of all SplunkJS, running a search and then outputing the results into an HTML element. Also includes examples generating a SimpleXML Viz from a Javascript search, and a Javascript Output from a SimpleXML search.
* Reading JSON Files from appserver/static: This is built into some of these core concepts, but why not make it explicit!
* Dynamically Updating Search String: Dynamically set the search string for any existing search managers.
* Indexing Events from Javascript: It's possible you may with to ingest data via Javascript. Consider log events to show what happened, audit events to show what the user did, or even small JSON data sources you download from the internet!
* Automatically Running Javascript on Every Page: Sometimes you need to run a script on every page, every time. Or similarly for stylesheets. Fortunately, Splunk makes that easy with dashboard.css and dashboard.js.
* Tooltips and Popovers: Want to embed helpful descriptions? Fortunately Splunk makes it fairly easy to do so with Bootstrap's tooltip and popover.

### Intermediate
* Creating Modal Dialogs: Modal Dialogs allow you to warn users about problems, get input from users, and more. Javascript natively has ugly alerts.. but modals are pretty and great!
* Querying REST API from Javascript: How can you directly query elements of Splunk's REST API from Javascript (without launching a search with the | rest search command, which would be silly and we would never use that in published apps on Splunkbase.. 😐).
* Using kvstore Collections: Reading the Splunk kvstore directly from SplunkJS, or adding entries.
* Authenticated Custom Search Commands: A basic search command that will run Splunk searches on your behalf, or hit the Splunk REST API.
* Authenticated Scripted Input: A scripted input that runs as an authenticated user to accomplish periodic tasks.
* Creating Zip Files with third party Javascript Libraries: This isn't really SplunkJS, but it's fun! And it gives us an opportunity to show how we can use third party libraries in our Javascript.
* Instantiating SplunkJS Service Object: Many of Splunk's docs talk about using SplunkJS from other websites which requires a service object. This will instantiate one within a SimpleXML Dashboard.
* Combining JSON Files from kvstore: If you have a static configuration file that you want to override with locally, it may be easiest to load your static JSON and then pull custom entries from the kvstore.
* Using localStorage: Do you need to really, really easily maintain state and are okay with it being limited to a single browser window? Then you'll *love* localStorage.
* Hiding Admin Functions in Help Menu: Don't let your drive for a simple user experience prevent you from building easy admin functionality. Just hide it in the help menu!
* Stored Credentials: Do you need to store a username and password, but don't want to hardcode it unencrypted on the local file system? Stored credentials are here for you!
* Dynamically Adding Panels: Dynamically add new rows or panels to your dashboard, all from Javascript.

### Advanced
* Comparing Streaming SDK Methods: For streaming search commands, there are two primary methods for implementation. One uses the Python SDK, and one uses a new Chunked Encoding library. We walk through these.
* Posting to HEC via Javascript: Implement your own client-side tracking by sending beacons from a non-Splunk website to the HTTP Event Collector via Javascript.
* Editing .conf Files from Javascript: Sometimes you may with to add a new lookup, new props, new .. anything .. from Javascript. This is the only known end-to-end example of doing that.
* Javascript Diag: When you build out a lot of Javascript, you inevitably fear someone saying "it doesn't work" but it works on your system. Fortunately, you can get a diag, making it easier to troubleshoot!
* Javascript App Setup: Want to have a lightweight app setup that checks whether data exists? This may be just the way for you.
* Localizing Apps With jquery.i18n: Use Wikimedia's jquery.i18n to localize portions of your app.

# Third Party Licensing
Please consult LICENSE.txt in the app for all third party licenses.

