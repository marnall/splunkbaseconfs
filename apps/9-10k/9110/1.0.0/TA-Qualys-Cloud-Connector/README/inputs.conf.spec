[was://<name>]
account = Account to use for this input.
start_date = Optional RFC3339 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ). Used as initial collection start when no checkpoint exists.
index = (Default: main)
interval = Time interval of the data input, in seconds. (Default: 3600)
num_threads_for_was = Legacy setupentity: num_threads_for_was (Default: 2)
use_multi_threading_for_was = Legacy setupentity: use_multi_threading_for_was

[vmdr://<name>]
account = Account to use for this input.
start_date = Optional RFC3339 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ). Used as initial collection start when no checkpoint exists.
index = (Default: main)
interval = Time interval of the data input, in seconds. (Default: 3600)
num_threads = Legacy setupentity: num_threads (Default: 2)
use_multi_threading = Legacy setupentity: use_multi_threading
