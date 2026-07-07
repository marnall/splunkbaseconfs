# What is the IOC Search
## IOC Search

The IOC Search is designed help locate Indicators of Compromise (IPs, domains, email addresses, hashes).

In order to use this you should understand what you can and cannot search.

For example you can use this to search for individual search terms -- based on Minor Breakers and Major Breakers. You can only search terms which contain Minor Breakers. All terms are split with Major Breakers.

You can also use wildcards with the IOC Search. For example if you wanted to search IPs in this range 10.5.1.0/24 which could be searched with this 10.5.1.*

## Major breakers
Major breakers are a set of characters that are used to divide words, phrases, or terms in the event data into large tokens. Examples of major breakers are:

- A space
- A newline
- A tab
- Angle brackets < >
- Square brackets [ ]
- Parenthesis ( )
- Curly brackets { }
- An exclamation point !
- A question mark ?
- A semicolon ;
- A comma ,
- Single and double quotation marks ' "
- The ampersand sign &
- There are also multiple major breakers that use percent-encoding, primarily for reserved characters. These major breakers begin with a percent symbol followed by a code. For example, %21 is the code for the exclamation point ( ! ) character and %2526 is a double encoded ampersand ( && ).

## Minor breakers
Minor breakers are a set of characters that are used to further divide large tokens into smaller tokens. Examples of minor breakers are:

- A period .
- A forward slash /
- A double backslash \\
- A colon :
- The equal sign =
- The AT sign @
- The pound sign #
- The dollar sign $
- The percent sign %
- The underscore sign _
- To understand event segement and searching check out the search manual

To understand how the TERM command is used in this app check out the search manual

For a complete list of segmenters, see segmenters.conf file in the Splunk Enterprise Admin Manual.

Note: Segmenters can be customized so validate your configuration to ensure that this will work in your environment
