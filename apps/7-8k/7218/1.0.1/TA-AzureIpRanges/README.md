# TA-AzureIpRanges

This app adds a simple scripted input which, on a weekly basis downloads Microsoft's published list of (public Azure IP ranges)[https://www.microsoft.com/en-us/download/details.aspx?id=56519] and builds them into a lookup. The input should run when first installed, and then every 7 days from there. The lookup in question is called "azure_public_ip_ranges" and is configured to allow for CIDR matching on the "prefix" field. 

Sample usage:

```
|makeresults | eval ip="13.77.52.35" | lookup azure_public_ip_ranges prefix AS ip OUTPUT
```

# Binary File Declaration

A dependency of this app, BeautifulSoup, includes binary files in its tests. One such file is "lib/bs4/tests/fuzz/crash-ffbdfa8a2b26f13537b68d3794b0478a4090ee4a.testcase".