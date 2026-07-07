########################################################################################################################
# SSL Configuration details
########################################################################################################################

[sslConfig]
    * Configure SSL for communications with Active Directory directory services under this stanza name.
    * Follow this stanza name with any number of the following attribute/value pairs.
    * If you do not specify an entry for each attribute, SA-ldapsearch will use the value specified under the sslConfig
      stanza name in server.conf.

sslVersions = <versions_list>
    * Comma-separated list of SSL versions to support.
    * The specific versions available are "ssl2", "ssl3", and "tls1.0".
    * The special version "*" selects all supported versions.  The version "tls" selects all versions tls1.0 or newer.
    * If a version is prefixed with "-", it is removed from the list.
    * Defaults to tls.

sslVerifyServerCert = true|false
    * If this is set to true, you should make sure that the Active Directory server that is being connected to is a
      valid one (i.e., authenticated). Both the common name and the alternate name of the server are then checked for
      a match, if they are specified. A certificate is considered verified, if either is matched.
    * Default is false.

sslRootCAPath = <filename>
    * The path to the certificate authority (CA), or root
      certificate store.
    * The certificate store must be a file that contains one or more
      CA certificates that have been concatenated together.
      This setting expects a value that represents a file object,
      not a directory object.
    * The certificates in the certificate store file must be
      in privacy-enhanced mail (PEM) format.
    * If you run Splunk Enterprise in Common Criteria mode, then
      you must give this setting a value.
    * This setting is valid on Windows machines only if the
      'sslRootCAPathHonoredOnWindows' has a value of "true".
    * No default.
