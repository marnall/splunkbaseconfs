# To store application's custom configurations.
# This file stores multiple settings under "[configuration]" stanza.Following are the settings and it's description:
    
[configuration]
zscore = <integer>
* Integer value should be between 1 and 6.
* zscore is the standard deviation of the activities performed by users.The standard meaning of zscore is: 
* A zscore (aka, a standard score) indicates how many standard deviations an element is from the mean. A zscore can be calculated from the following formula.
*
*        z = (X - μ) / σ
*
*        where z is the zscore, X is the value of the element, μ is the population mean, and σ is the standard deviation.
* Default: 3
threshold = <integer>
* Define threshold on individual user's risk score.
* Default: 50