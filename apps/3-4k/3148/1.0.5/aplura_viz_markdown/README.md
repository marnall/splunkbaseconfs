# Markdown Renderer Visualization Documentation

Render Markdown in the browser.

## About Markdown Renderer Visualization

|                           |                                                |
|---------------------------|------------------------------------------------|
| Author                    | Aplura, LLC                                    |
| App Version               | 1.0.5                                          |
| App Build                 | 25                                             |
| Vendor Products           |                                                |
| Has index-time operations | false                                          |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

# Scripts and binaries

This App provides the following scripts:

- Diag.py

  - Provides customized Diag access.

- version.py

  - Provides the version and build for logging, if needed.

- app_properties.py

  - Provides properties of the app for any required Python.

## About Markdown Renderer Visualization

The Markdown Visualization allows you to specify a Markdown (`md`) or AsciiDoc (`adoc`) file to render within a panel on a Splunk dashboard.

This can be useful on a dashboard to describe what is being displayed, relevant external links about the dashboard, or other instructions.

# Getting Started

When creating a visualization, a search must be performed. As the exact search does not matter for this visualization we recommend utilizing the *\| makeresults* search. This is a simple search within Splunk which, when run without options, returns one result based on the `_time` field. Once the search has returned, the Markdown visualization may be selected.

1.  Click on the Visualization tab.

2.  From the Visualization tab, click the Visualizations drop-down and select the Markdown visualization from the *More* section.

3.  The README file is displayed by default.

4.  To customize the visualization, select the Format drop-down to open the configuration window.

# Format Options

The Markdown Visualization has a few configuration options after opening the format window. The tabs are listed on the left of the window as Render, Local File, and Debug.

## Render

The Render tab has three options in a drop-down menu; Maruku, Gruber, and Asciidoctor. The first two are dialects of Markdown and the latter is for processing Asciidoc markup.

Markdown files must end with an `.md` extension while the Asciidoc files must end with `.adoc`.

Select the option appropriate to the file being rendered.

The other option on this page is the Location. This determines where the visualization will look for the markdown source.

## Local File

The Local File tab has three options to configure; App Name, Path, and File Name.

### App Name

The App Name field is populated with the name of the Splunk app where the target file is located.

### Path

The Path field is used to add the path to the target file if it does not reside in the default `$APP_HOME/appserver/static` directory. This target file must be at or below `$APP_HOME/appserver/static` in the file structure. When entering the path information, omit any leading or trailing slashes.

### File Name

The File Name field is populated with the name of the file to be rendered without a file extension, though it must end with either `.md` or `.adoc` on the server.

## Debug

The Debug tab is used to enable (yes) or disable (no) the JavasScript Logging option for the app view.

## Event Generator

Markdown Renderer Visualization does not include an event generator.

## Acceleration

- Summary Indexing: No

- Data Model Acceleration: No

- Report Acceleration: No

# Installation

To install, copy the downloaded tarball to the `$SPLUNK_HOME/etc/apps` directory and expand. Splunk will need to be restarted for the new application and configuration to take.

Markdown Renderer Visualization can also be installed in any Splunk compatible method.

# Support and Resources

# Questions and answers

Access questions and answers specific to Markdown Renderer Visualization at <https://answers.splunk.com/>. Be sure to tag your question with the App.

# Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

# Release notes

## Version 1.0.5

- Reviewed and Certified for Splunk 10.

## Version 1.0.4

- Updated SplunkJS libraries for Splunk 9.X

- "Inline Search" now supports newline `\n` in the text, and renders correctly.

- Updated CSS to avoid Splunk Theme conflicts.

  - Can be overridden using the `aplura-viz-markdown` base class.

# Third Party

Version 1.0.5 of Markdown Renderer Visualization incorporates the following Third-party software or third-party services.

- TBD
