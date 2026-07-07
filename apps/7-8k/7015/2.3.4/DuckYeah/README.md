# DuckYeah
![Duck Yeah!](https://nthdegree.io/wp-content/uploads/2023/08/duckyeah-email-logo.png)
## What?
Duck Yeah! is Splunk App Packaging-as-a-Service. The Duck Yeah! frontend renders through a Splunk dashboard, communicates with an API, and even uses Splunk on the backend. Depending on the configuration, a fully-built, fully-vetted package can be built with *three clicks and a tab.*

Duck Yeah! allows Splunk developers to develop wherever they are comfortable - through the CLI, through the GUI, or directly on the filesystem. When you're ready to package up a feature or a release, just give Duck Yeah! some light instructions. When finished, you'll have a .tgz ready for distribution - on Splunkbase, in Splunk Cloud, or local/internal.
## Why?
Anyone who has spent any time building Splunk apps knows that they can be finicky. Munging can be a complete pain in the ass and is highly error-prone. Apps must pass AppInspect to be available for Splunk Cloud ACS self-service. It's easy to miss things.

AppInspect and other CLI/API interfaces to help require programmatic interaction. In short, there's plenty of tools out there that can get 80% of the way there, but they're disjointed, prone to error, and require knowledge of their existence, configuration, usage, and quirks.

With Duck Yeah!, you take a process that requires several minutes or hours depending on the scope of your change, and distill it to **60 seconds or less.**

Duck Yeah! was once called *the packaging scripts* at a customer site, then AppPack when the functionality was later recreated. Upon hearing that first customer wanted to license it, we thought, *duck yeah!* and we turned it into an API service.
## How
Duck Yeah! has two primary dashboards - the Duck Yeah! dashboard and the Setup dashboard. Just register with the service on the Setup dashboard, and get to packaging on the Duck Yeah! dashboard. It's that simple.

To perform a build, you must initialize or clone a git repository into `$APP_HOME`. We recommend a commit after every build.

Duck Yeah! also offers other functionality like:
* Splunk-user-specific seure API key storage
* Splunk-user-specific default settings
* App-specific local exclusions down to the parameter level
* Automatic AppInspect vetting and a summary of warnings or failures
* Alphebetizing files that can be safely alphabetized for an easier time seeing changes in source control
* Integrated payments through Stripe for *Individual* mode
* Subscriptions for *Enterprise* or *Company* mode
* A selector to clear or keep `$APP_HOME/local` after each package
* Scans for and warnings on any private artifacts relative to the app
* Proper construction of app.manifest for Splunk Cloud

## Where
Duck Yeah! is available for download through Splunkbase and serviced through nth degree.

## Warnings
Duck Yeah! is a powerful tool, when used properly. With great power comes great responsibility. Duck Yeah! is not designed for use **on** Splunk Cloud, but can build **for** Splunk Cloud. Duck Yeah! is not designed to replace source control or change control; rather, enhance and augment these processes. We recommend using git and git flow. Duck Yeah! is not designed to be used in production.

### THIS IS A DEVELOPER TOOL. USE WISELY. USE CAUTIOUSLY
Always, always, always - commit your changes.

Always.
