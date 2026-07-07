This app contains a custom command that can perform certain calculations on 
multi-value fields without resorting to mvexpand.  This can be handy when you
have several MV fields and the use of mvexpand might lose the relationships 
among them.

The command can do sum, average, min, max, and range (max - min).

USAGE
    | mvstats <function> <mv-field> as <result-field>
Where:
    <function> is one of:
        sum - add up the values in <mv-field>
        ave - compute the average of the values in <mv-field>
        min - return the lowest number in <mv-field>
        max - return the highest number in <mv-field>
        range - return the difference between the highest and lowest values
        stdev - compute the standard deviation of the values in <mv-field>
        median - return the middle value in <mv-field>
        mode - return the most common value in <mv-field>
    <mv-field> is a multi-value numeric field
    <result-field> is the name of a field to receive the results

    Notes:
    - If <mv-field> contains a non-numeric value then <result-field> is set to "NaN"
    - The mode function returns "NaN" if more than one value has the highest cardinality.
    - The mode function accepts non-numeric input.

EXAMPLE:
    ... | stats values(dest_port) as dest_port, values(count) as count by app
    | mvstats sum count as total

PREREQUISITES:
    None

INSTALLATION
    Install on all search heads in the normal way.  No configuration needed.

SUPPORT
    This app is developer-supported.

    Rich Galloway, Mainline RTP, LLC
    rich.galloway@mainlinertp.com

CREDIT
    This app builds upon the work of Jordan Brough and Ryan Thibodeaux at https://gist.github.com/jordan-brough/a7f498f84a98af002fcc.
    
ABOUT MAINLINE RTP
    Mainline RTP, with main offices in Paramus, NJ, is an information technology solutions firm who architects and delivers innovative IT solutions, including hybrid cloud offerings, on-premises infrastructure systems, software offerings and services. 

    Mainline RTP is a Splunk Elite partner that has delivered Splunk Services to many clients ranging from single server with a 10gb/day license, to multi-site clustered environments with >10TB / day license. Mainline RTP specializes in flexible and cost effective Professional Services engagements with both on-site and remote deployments.

    https://mainlinertp.com/