# Splunk WLM Resource Protection App



## HeavySearchesTerminator

Designed to monitor the resource consumption of active search jobs by analyzing the `_introspection` index. The metrics calculated are used to identify and "terminate" searches that exceed predefined thresholds for CPU and memory usage.

## Total Metrics

#### 1. total_vcpu_sec (Total vCPU Seconds)

###### Description
The cumulative amount of CPU time consumed by the search process across the whole environment.
###### Calculations
It takes the CPU percentage (pct_cpu) from `_introspection` index, converts it to a CPU time and multiplies it by the collection interval (by default it's 10 seconds).

#### 2. total_mem_gib_sec (Total Memory GiB-Seconds)

###### Description
A measure of "memory occupancy" over time across the whole environment. It accounts for both how much RAM was used and for how long.
###### Calculations
It takes the memory usage (mem_used) from `_introspection` index, converts it to GiB and multiplies it by the collection interval (by default it's 10 seconds).

## Search Head Metrics

#### 1. shs_vcpu_sec (Search Head vCPU Seconds)

###### Description
The cumulative amount of CPU time consumed by the search process on all Search Heads.
###### Calculations
It takes the CPU percentage (pct_cpu) from `_introspection` index converts it to a CPU time , and multiplies it by the collection interval (by default it's 10 seconds).

#### 2. shs_mem_gib_sec (Search Head Memory GiB-Seconds)

###### Description
A measure of "memory occupancy" over time across by the search process on all Search Heads.
###### Calculations
It takes the memory usage (mem_used) from `_introspection` index, converts it to GiB and multiplies it by the collection interval (by default it's 10 seconds).

#### 3. max_shs_vcpu_sec (Maximum Search Head vCPU Seconds)

###### Description
The peak (highest) instantaneous cpu usage recorded for the search on the Search Head during its lifetime.
###### Calculations
It takes the highest cpu usage from `_introspection` from all Search Heads

#### 4. max_shs_mem_usage (Maximum Search Head Memory Usage)

###### Description
The peak (highest) instantaneous memory usage recorded for the search on the Search Head during its lifetime.
###### Calculations
It takes the highest memory usage (mem_used) from `_introspection` from all Search Heads and converts it to GiB.

## Indexer Head Metrics

#### 1. idxs_vcpu_sec (Indexer vCPU Seconds)

###### Description
The cumulative amount of CPU time consumed by the search process on all Indexers.
###### Calculations
It takes the CPU percentage (pct_cpu) from `_introspection` index, converts it to a CPU time and multiplies it by the collection interval (by default it's 10 seconds).

#### 2. idxs_mem_gib_sec (Indexer Memory GiB-Seconds)

###### Description
A measure of "memory occupancy" over time by the search process on all Indexers.
###### Calculations
It takes the memory usage (mem_used) from `_introspection` index, converts it to GiB and multiplies it by the collection interval (by default it's 10 seconds).

#### 3. max_idxs_vcpu_sec (Maximum Search Head vCPU Seconds)

###### Description
The peak (highest) instantaneous cpu usage recorded for the search on the Indexer during its lifetime.
###### Calculations
It takes the highest cpu usage from `_introspection` from all Indexers

#### 4. max_idxs_mem_usage (Maximum Indexer Memory Usage)

###### Description
The peak (highest) instantaneous memory usage recorded for the search on the Indexer during its lifetime.
###### Calculations
It takes the highest memory usage (mem_used) from `_introspection` from all Indexers and converts it to GiB.

## Thresholds

Thresholds are stored in `wlm_resource_protection.conf` under the `[thresholds]` stanza.

```
total_vcpu_sec      -> total_vcpu_sec_th
total_mem_gib_sec.  -> total_mem_gib_sec_th
shs_vcpu_sec        -> shs_vcpu_sec_th
shs_mem_gib_sec     -> shs_mem_gib_sec_th
idxs_vcpu_sec       -> idxs_vcpu_sec_th
idxs_mem_gib_sec    -> idxs_mem_gib_sec_th
max_shs_vcpu_sec    -> max_shs_vcpu_sec_th
max_idxs_vcpu_sec   -> max_idxs_vcpu_sec_th
max_shs_mem_usage   -> max_shs_mem_usage_th
max_idxs_mem_usage  -> max_idxs_mem_usage_th
```

#### Example
```
[thresholds]
total_vcpu_sec_th=1000
```

### Splunk UI

Admins can now update these values from the Splunk UI through the app setup screen:

`Apps > Manage Apps > Splunk WLM Resource Protection App > Set up`

The setup form writes the values into `local/wlm_resource_protection.conf`.

## SavedSearch

The saved search is defined in `savedsearches.conf`.

Admins can manage the saved-search status, `cron_schedule`, and `dispatch.earliest_time` from the same setup screen:

`Apps > Manage Apps > Splunk WLM Resource Protection App > Set up`

The terminator only evaluates searches owned by users who have the `wlm_terminator_monitored` role.
This role is packaged by the app in `default/authorize.conf`, but admins still need to assign it to
the users whose searches should be monitored. If no users have that role, enabling the saved search
will not terminate any searches.
