[agent_management_versioned_app_retrieval_add_on://configuration]
python.version = <string>
* Python version used by TA.
* Default: python3.9

repository_type = <string>
* Type of repository configured by this input.
* Supported values: jfrog, github, gitlab, nexus.

extract_path = <string>
* Path where downloaded artifact should be extracted.
* Typically, it should be 'repositoryLocation' path,
* either global or serverclass-specific.
* Example: $SPLUNK_HOME/etc/deployment-apps

extension = <string>
* Artifact extension. Supported values:
* .tar.gz, .zip

auth_header_type = <string>
* Authorization header authentication scheme that will be used
* for user agent identity authentication
* Example: Basic, Bearer

secrets_storage_username = <string>
* Username associated with a password in storage.
* Password configuration is a prerequisite
* if you need to authenticate to versioned app source.

max_file_size = <positive integer>
* Maximum size of file that will be downloaded from specified source (in MB).
* Default: 500

timeout = <positive integer>
* Request timeout in seconds for external API calls.
* Default: 60

max_retries = <unsigned integer>
* Maximum number of retry attempts for failed requests.
* Default: 3

address = <string>
* Base address to versioned app repository. Required for all repositories.
* In case of GitHub public instance https://api.github.com should be specified as address.
* Example: https://nexus.example.com

project_id = <string>
* ID of project. 
* Applies only to GitLab repository type.

owner = <string>
* Owner of repository.
* Applies only to GitHub repository type.

branch = <string>
* Branch or tag which should be looked for
* to download artifact from versioned app source.
* If not specified, main branch will be used.
* Applies only to GitHub and GitLab repository type.
* Default: main

repository_name = <string>
* Name of the repository.
* Applies only to GitHub, Sonatype Nexus Repository and JFrog Artifactory repository type.

path = <string>
* Path to the artifact/file in the repository.
* Applies only to Sonatype Nexus Repository and JFrog Artifactory repository type.
* Default: / for Sonatype Nexus Repository, . for JFrog Artifactory.

artifact_name = <string>
* Artifact name (file name without extension).
* Applies only to Sonatype Nexus Repository and JFrog Artifactory repository type.

