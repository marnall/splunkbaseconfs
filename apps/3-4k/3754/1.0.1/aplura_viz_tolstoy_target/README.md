# Tolstoy Target Visualization Documentation

Visualize data using advanced graphing with the Tolstoy Target

## About Tolstoy Target Visualization

|                           |                                                |
|---------------------------|------------------------------------------------|
| Author                    | Aplura, LLC                                    |
| App Version               | 1.0.1                                          |
| App Build                 | 15                                             |
| Vendor Products           |                                                |
| Has index-time operations | false                                          |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

# Scripts and binaries

This App provides the following scripts:

|          |
|----------|
| Do This  |
| Add Here |

## About Tolstoy Target Visualization

### Example Search

1.  index=*introspection component=Hostwide \|stats avg(data.**) as avg*** max(data.**) as max\_** min(data.**) as min\_** by host \| `tolstoy_prep("host")`\| `tolstoy_keep("avg_cpu_idle_pct,avg_cpu_system_pct,avg_cpu_user_pct,avg_mem_used,avg_swap_used,avg_normalized_load_avg_1min")`\|`tolstoy_direction("avg_cpu_idle_pct")` \| `tolstoy_range("avg_mem_used","0,2000")`

### Example Search Support

Please ask a question on Answers. Tag it with "aplura_viz" to get noticed. Support URL: answers.splunk.com

# Getting Started

# Format Options

# Event Generator

Tolstoy Target Visualization does not include an event generator.

# Acceleration

- Summary Indexing: No

- Data Model Acceleration: No

- Report Acceleration: No

# Installation

To install, copy the downloaded tarball to the `$SPLUNK_HOME/etc/apps` directory and expand. Splunk will need to be restarted for the new application and configuration to take.

Tolstoy Target Visualization can also be installed in any Splunk compatible method.

# Support and Resources

# Questions and answers

Access questions and answers specific to Tolstoy Target Visualization at <https://answers.splunk.com/>. Be sure to tag your question with the App.

# Support

- Support Email: <customersupport@aplura.com>

- Support Offered: Splunk Answers

# Release notes

# Third Party

Version 1.0.1 of Tolstoy Target Visualization incorporates the following Third-party software or third-party services.

- jQuery

- underscore

- d3

- handlebars-loader

`jQuery` and `underscore` frameworks are utilized.

    This visualization also uses the `handlebars-loader` framework. Usage is provided by the MIT license. For more information, please see http://www.opensource.org/licenses/mit-license
