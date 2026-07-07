# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.1.2] - 2020-07-08

### Bug Fixes

- Python2 compatibility issues

## [3.1.1] - 2020-06-15

### Added

- Showing license as a password field
- Sonar Splunk Service address and port fields validation
- Removing the scheme from the address before requesting Sonar Splunk

## [3.1.0] - 2020-05-26

### Bug Fixes

- Fix compatibility issues when running the app on Splunk 7.x

## [3.0.1] - 2020-05-14

### Bug Fixes

- Sonar Actions - Fixed index pattern ID

## [3.0.0] - 2020-04-30

### Added

- Added workflow actions to run sonar actions
- Added parameter `disable_count` to increase performance when dealing with collections that contain a large amount of data

## [2.0.0] - 2020-02-12

### Added

- Cancel the request when user stops the search job

### Removed

- Using the local machine's certificate authority

## [1.0.2] - 2020-01-27

### Added

- License field in "Configuration" page

### Removed

- Client Certificate and Private Key fields in "Configuration" page

### Modified

- Certified Authority Certificate field is now expecting the content of a certificate instead of its path 


## [1.0.1] - 2020-01-22

### Added

- Search query parser using ANTLR v4
- Limit configuration in "Configuration" page


## [1.0.0] - 2019-12-11

### Added
- Custom generating command to query Sonarw data. (Generating command communicates with splunk-sonar service.)
- Configuration view has been added.


## [0.2.0] - 2019-11

### Removed
- Features to connect splunk-sonar service through virtual index(es). The splunk-sonar service does **not** support virtual index anymore.


## [0.1.0] - 2019

### Added
- Features to connect splunk-sonar service through virtual index(es).