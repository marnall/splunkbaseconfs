from splunklib.binding import HTTPError

# Get configuration stanza accessor to manipulate configuration file resources using Splunk Python SDK
def getConfStanzaAccessor(confAccessor, filename, stanza):
        configuration_file_accessor = confAccessor.create(filename)
        stanza_exists = configuration_file_accessor.__contains__(stanza)
        if stanza_exists:
            configuration_stanza_accessor = configuration_file_accessor.__getitem__(
                stanza)
        else:
            configuration_stanza_accessor = configuration_file_accessor.create(
                stanza)
        return configuration_stanza_accessor

# Update stanza based on value
def updateStanza(confAccessor, filename, stanza, field, value):
    config_stanza_accessor = getConfStanzaAccessor(confAccessor, filename, stanza)
    config_stanza_accessor.update(
                    **{field: value})

# Get value from given stanza
def getStanzaValue(confAccessor, filename, stanza, field):
    config_stanza_accessor = getConfStanzaAccessor(confAccessor, filename, stanza)
    try:
        value = config_stanza_accessor.__getitem__(field)
        return value
    except KeyError as e:
        raise e(field + " field in [" + stanza + "] stanza of " + filename + ".conf not found. Please redo your setup and review your conf files.")
    except HTTPError as e:
        raise e

