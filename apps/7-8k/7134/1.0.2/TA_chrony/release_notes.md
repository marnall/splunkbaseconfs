### v1.0.2

1. Changed chrony:measurements test field names to match RFC 5905 and chrony documentation 
names more predictably.
- _passed_validity_test_ is now ***passed_invalid_test***
- _passed_unsync_src_test_ is now ***passed_unsynchronized_test***
- _passed_maxdelay_test_ is now ***passed_max_delay_test***
- _passed_maxdelayratio_test_ is now ***passed_max_delay_ratio_test***
- _passed_maxdelaydevratio_test_ is now ***passed_max_delay_dev_ratio_test***

2. Changed chrony:statistics fields; 
old names are still aliased but will be removed in the next release.
- _differ_freq_ is now ***drift***
- _skew_ is now ***drift_err***
- _stress_ is now ***rate_err_ratio***

3. Changed the default index from _os_ to ***default*** for the log files default input.
