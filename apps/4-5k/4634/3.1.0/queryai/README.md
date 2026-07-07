# Query Federated Search for Splunk

Supercharge your Splunk experience with Query Federated Search. This Splunk app unlocks access to cybersecurity data wherever it is stored, regardless of the vendor or technology, directly from your Splunk console.

## Features

- **Federated Search:** Use `Query` directly from Splunk's search bar to execute a search of security-relevant data stored outside of Splunk. Results are returned in the Splunk interface and can be included in SPL searches, reporting, and dashboards without having to ingest & store that data in Splunk.

- **Easy Integration:** `Query` can be connected to additional data sources in minutes using pre-built API connections, bringing additional data into Splunk's powerful security observability capabilities.

## Usage Example

For example, you can run a federated search to fetch events, associated devices, and user information for an IP you are investigating:

```spl
| queryai search="ip = 8.8.8.8"
```

## Getting Started

To get started with Query Federated Search for Splunk, visit our [website](https://query.ai/query-federated-search-for-splunk/).

## Developed By

Query Federated Search for Splunk is developed by [Query](https://query.ai).

## Support

For support, please email us at [support@query.ai](mailto:support@query.ai).