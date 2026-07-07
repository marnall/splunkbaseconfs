Copyright 2018 Hurricane Labs

# Version Support #
7.1 - 6.0

# How does it work? #
- Hurricane Labs App for Shodan allows you to search Shodan for relevant information about your hosts.
- Use the generating command `| shodan net=<ip>`. This must be the first command in your search.

# Requirements #
You must purchase an API key from Shodan (https://www.shodanhq.com/) before using this app.

# Examples #
1. Search for one IP address:
`| shodan net=<ip>`

2. It is also possible to search over mutliple IP addresses like so:
`| shodan [| inputlookup ip_lookup.csv | fields net]`
In the above example we are using a lookup file called ip_lookup.csv that contains a field called net.
When expanded out this search becomes `| shodan net=<ip_1> OR net=<ip_2> OR net=<ip_3> OR ...`

3. Newly added, there is now a max_pages parameter if you wish to pull more than 100 results.
Use with CAUTION - see 'Release Notes':
`| shodan net=<ip> max_pages=2`


# Release Notes #
## v 2.2.0 ##
- Improved README. Added example usage for | shodan command.
- Tested on 7.1
- Added searchbnf.conf for contextual help in search.
- Added max_pages parameter. Set this in order to consume more than 100 results per query.
WARNING: For each page consumed past the first one, you will lose a query credit.
Use this option at your own risk!

## v 2.1.3 ##
- Removed Requests library. No longer necessary.


# For support #
- Send email to splunk@hurricanelabs.com
- Support is not guaranteed and will be provided on a best effort basis.