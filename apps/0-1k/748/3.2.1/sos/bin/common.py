# Shared python code between python search commands in this folder.
import socket
import subprocess
import re
from splunk import getReleaseVersion


def run_btool(*args):
    """ Execute the 'btool' command line utility, and return groups of lines
    broken down into stanzas.  This function returns an iterable, which in the form
        (app, stanza, [ lines ])
    """

    # We need to determine the Splunk major version number to find out if it's
    # safe to use "--no-log" as an argument when invoking btool
    splunk_version = getReleaseVersion()
    splunk_major_version = int(splunk_version.split(".",1)[0])
    if splunk_major_version >= 5:
      args = args + ("--no-log",)
    else:
      args = args
    cmd = ("btool",) + args
    pseudohandle = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)
    stdout, stderr = pseudohandle.communicate()
    # Q:  Do we care about the stuff written to stderr?  (Ignoring it for now)
    
    # Split apart the output from btool into separate stanzas.  A new stanza
    # starts with a "[stanza]" line (or "APPNAME [stanza]" line) depending on
    # "list" vs "list-debug" modes
    if splunk_major_version >= 5:
      stanza_breaker_re = re.compile(r'^.*?[\\/]etc(?:[\\/](?:slave-)?apps)?[\\/]([^\\/]*?)[\\/](?:default|local)[\\/].*?\.conf\s+\[(.*)\]$')
    else:
      stanza_breaker_re = re.compile(r'^(?:(\S+)\s+)?\[(.*)\]$')
    
    app = None
    stanza = "default"
    content = []
    
    for line in stdout.splitlines():
        stanza_match = stanza_breaker_re.match(line)
        if stanza_match:
            # A stanza match means (1) the current stanza is done and (2) a new one is starting
            if content:
                yield (app, stanza, content)
            # Start the new stanza group
            app = stanza_match.group(1)
            stanza = stanza_match.group(2)
            content = [ line ]
        else:
            # Keep collecting lines for the current stanza
            content.append(line)
    
    # Return final stanza group
    if content:
        yield (app, stanza, content)


def get_btool_internal_host():
    """ Return the "host" as assigned to the monitor of splunk's  internal logs.
    If host is not found, None will be returned. """
    for (app, stanza, lines) in run_btool("inputs", "list-debug", "monitor"):
        if re.match(r"^monitor://(\w:)?[/\\].*[/\\]var[/\\]log[/\\]splunk$", stanza):
            for line in lines:
                hostMatch = re.search(r"[^_]host\s*=\s*([^\s\v]+)$", line)
                if hostMatch and len(hostMatch.group(1))>0 and hostMatch.group(1)!="$decideOnStartup":
                    return hostMatch.group(1)
    return None


def get_os_hostname():
    """ Return the hostname of this server as reported by the OS. """
    # A FQDN version of this would be:   socket.getfqdn(socket.gethostname())
    return socket.gethostname()


def get_sos_server():
    """ Get the host name of the SOS server using btool or host name. """
    btoolHost = get_btool_internal_host()
    if btoolHost:
        return btoolHost
    else:
        # Fallback to simply getting the OS assigned hostname
        return get_os_hostname()
