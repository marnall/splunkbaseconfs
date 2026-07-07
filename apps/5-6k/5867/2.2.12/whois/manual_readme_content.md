The app uses the tldextract python module while executing the 'whois domain' action. This module
uses the tld list from publicsuffix.org. The app ships with a tld list, however, it will try to
update the list the first time it runs and then tries to update it at a regular interval. The
interval is set in the app config.

This app will ignore the HTTP_PROXY and HTTPS_PROXY environment variables.

The user is requested to use CONFIGURE NEW ASSET option to configure a new asset.

## WHOIS Ports Requirements (Based on Standard Guidelines of [IANA ORG](https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml) )

- WHOIS(service) TCP(transport protocol) - 43
- WHOIS(service) UDP(transport protocol) - 43

## ipwhois

This app uses the python-ipwhois module, which is licensed under the BSD License, Copyright (c)
2013-2019 Philip Hane.

## pythonwhois-alt

This app uses the pythonwhois module, which is licensed under the WTFPL License, Copyright (c) Yuriy
Zemskov.

## tldextract

This app uses the python tldextract module, which is licensed under the BSD License, Copyright (c)
John Kurkowski.

## dnspython

This app uses the python dnspython module, which is licensed under the ISC License, Copyright (c)
Bob Halley.

## requests-file

This app uses the python requests-file module, which is licensed under the Apache 2.0 License,
Copyright (c) David Shea.

## charset-normalizer

This app uses the python charset-normalizer module, which is licensed under the MIT License,
Copyright (c) 2025 TAHRI Ahmed R.
