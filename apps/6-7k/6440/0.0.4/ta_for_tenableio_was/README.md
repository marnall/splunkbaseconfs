# TA for tenable.io WAS

Author: Greg Ford

## Update History

| Version | Date         | Comments      |
| ------- | ------------ | ------------- |
| 0.0.1   | May 17, 2022 | First version |
| 0.0.4   | Sep 12, 2024 | splunklib SDK update |

## Using this TA

1. Install the TA
2. Setup an API key using the configuration page
3. Create a modular input
4. Search the resulting data

## Notes

The API key should be in the form `accessKey=abc123...;secretKey=xyz987...` i.e. a single key=value string with two key=value pairs separated by semicolon.

The TA will ingest all reports with a finalized_at date in the last x hours. It makes no attempt to dedupe results or handle checkpoints in any way.

If you have more than 200 scans configured, only the first 200 will be considered. This may be addressed in a future release by adding support for paging when querying `was/v2/configs/search`.

## Troubleshooting

Search `index=_internal source=*ta_for_tenableio_was.log`.

Enable debug logging in tenableio_was_input.py if required. This is not yet exposed as a UI-configurable option.
