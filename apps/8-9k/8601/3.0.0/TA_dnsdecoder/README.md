# DNS Decoder — Splunk Custom Search Command

Decodes Base64-encoded DNS wire-format messages in SPL.

## Test It

```spl
| makeresults
| eval dns_answer="6RmBgAABAAIAAQAAEmRpcmVjdG9yeS1zZWFyY2gtYQR3YngyA2NvbQAAQQABwAwABQABAAAAPAAQDXByb2QtYWNobS1jaTHAH8A5AAUAAQAAADwAQBh3eHQtY2ktaW5ncmVzc2dhdGV3YXktZHMTd3h0Y2ktcHJvZC1hY2htLWNpMQRwcm9kBWluZnJhBXdlYmV4wCTAggAGAAEAAABeAEUGbnMtODg4CWF3c2Rucy00NwNuZXQAEWF3c2Rucy1ob3N0bWFzdGVyBmFtYXpvbsAkAAAAAQAAHCAAAAOEABJ1AAABUYA="
| dnsdecode field=dns_answer
| table dns_query_name dns_query_type dns_rcode dns_answer_count dns_answers
```

## Usage in SPL

```spl
index=dns sourcetype=your_dns_logs
| dnsdecode field=dns_answer
| table _time dns_query_name dns_query_type dns_rcode dns_answer_count dns_answers
```