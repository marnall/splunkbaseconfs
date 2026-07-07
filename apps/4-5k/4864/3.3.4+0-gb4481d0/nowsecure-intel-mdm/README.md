## Intel MDM Splunk App

This is the MDM Splunk app

## Publishing

0. Download the .tar.gz file from the releases tab in GitLab
1. Login to https://splunkbase.splunk.com using the `nowsecure` account. (available in 1password)
2. Visit https://splunkbase.splunk.com/app/4864/edit/#/hosting
3. Click New Version
4. Upload it to Splunk Base
5. Splunk will validate the package automatically.
6. Select Splunk Compatibilities 8.0, 7.3, 7.2, 7.1, 7.0
7. Click Publish
8. Back on the Versions page, change the default to the latest.

## Development

### Setup

* Pull down the latest splunk enterprise
  * docker pull splunk/splunk
* Start the splunk docker container
  * Example cmd: `docker run -d -e SPLUNK_START_ARGS=--accept-license -e SPLUNK_PASSWORD=password  -e DEBUG=true -p 8000:8000 splunk/splunk`
* Once you have logged in, go to Settings >> Add Data
  * Add all the mdm_x.log files in the [_sampledata] directory
  * Click the Upload option on the bottom left.
  * Select the file
  * Select nowsecure-intel-mdm sourcetype
  * Continue through to finish

## Testing

1. Start Splunk `docker run -d -e SPLUNK_START_ARGS=--accept-license -e SPLUNK_PASSWORD=password  -e DEBUG=true -p 8000:8000 splunk/splunk`
2. Download the .tar.gz you want to test.
   * This can be sourced from a GitLab CI artifact
   * Release artifact
   * Branch in the GitLab via the Download Source Button
3. Extract .tar.gz locally on your system
4. Open http://localhost:8000
5. Navigate to http://localhost:8000/en-US/manager/appinstall/_upload
6. Choose the .tar.gz that you downloaded
7. Click Upload
8. Navigate to Settings > Add Data
9. Click Upload files from my computer
10. Select a file from the [_sampledata] directory
11. Click Next
12. Select Source type as `nowsecure-intel-mdm`
13. Click Next until complete
14. Repeat steps 10-13 for all files in [_sampledata].

## Building

Using GitLab CI and commits all commits are built automatically and show up in the GitLab CI under artifacts for the job.

If you'd like to manually build for upload into Splunk for testing, simple run the [.ci/build] script and the file will appear in the `release/` directory, which is excluded from git.

## Splunk App Structure

When using Splunk itself to make modifications to the app, all changes will go into the `local` folder. Those changes should be moved over to the `default` before committing to source control. This will allow any additional changes made by end users to not directly overwrite the defaults but suppliment them.

### Archive Structure

Splunk expects the .tar.gz to have a directory that contains the root of the application. 

```
- nowsecure-intel-mdm \
  - appserver
  - bin
  - default
  - local
  - metadata
```

## Releasing

To perform a release, simply run `bash .ci/tag-version X.Y.Z` for a release candidate `bash .ci/tag-version X.Y.Z-rcN` while on master.

**Note:** This does a couple things, first it validates the format is right, we only allow for SEMVER of MAJOR.MINOR.PATCH with an optional `-rcN` suffix. It then updates the VERSION file and makes a version commit and then pushes the master branch and the tags up to the remote.

If there are any release files the [gitlab-release tool](https://gitlab.com/ekristen/gitlab-release) can be used to stub a GitLab Release and upload any release files against the release.

### Release Candidates

Release candidates should be cut anytime there's a version that needs to be tested in staging or in QA before going to production. If the current version is 2.0.0 and the next one should be 2.1.0, then the first tag that should be cut is 2.1.0-rc1. Any changes should result in a rc2, rc3 and so forth. Once QA signs off on an rcN version, then tag without the `-rcN` suffix. For example if 2.1.0-rc4 was the last version, the same commit would then be tagged as 2.1.0

### Versioning

Versions are based on SEMVER MAJOR.MINOR.PATH with an optional -rcN suffix for release candidates. 

### Build Versions

Build Version is generated using [this script](.ci/version). It uses git, the value of [VERSION](VERSION), and any tags to generate a SEMVER compatible build version that follows the format of `LAST_TAG.NUM_OF_COMMITS_SINCE_LAST_TAG.gCOMMITTISH`. If the current commit has a tag and that matches the value in VERSION, which it should when using the `.ci/tag-version` script, the resulting version will just be the tag.