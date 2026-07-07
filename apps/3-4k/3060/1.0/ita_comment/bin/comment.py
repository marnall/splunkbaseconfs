import splunk.Intersplunk


# Get the previous search results from the pipeline
results, unused1, unused2 = splunk.Intersplunk.getOrganizedResults()

# Do nothing...

# Output the same results to the pipeline
splunk.Intersplunk.outputResults(results)
