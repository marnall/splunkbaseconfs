[![CI](https://github.com/splunk/splunk-add-on-for-ocsf-to-cim/actions/workflows/ci.yml/badge.svg)](https://github.com/splunk/splunk-add-on-for-ocsf-to-cim/actions/workflows/ci.yml)

# OCSF-CIM Add-On for Splunk

This add-on provides knowledge objects to make it easy to use OCSF data within Splunk, including CIM mappings. It assumes OCSF data is indexed in JSON format. This addon does not
handle the transformation of non-OCSF data formats to OCSF but provides CIM-compliance to data in OCSF format.

## Installation

This add-on needs to be installed wherever the Common Information Model add-on is installed in your environment. Refer to [About installing Splunk add-ons](https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons) for guidance specifically for your deployment topology.

## Approach

Just like any other data source format, OCSF can be mapped to the Common Information Model. The advantage of OCSF is that it's already a well-structured format
with defined fields. The TA defines event-class-specific mappings as described in [MAPPING](MAPPING.md). The mapping is defined in this repository and the
corresponding Splunk configuration files (eventtypes, props, tags) is auto-generated.

### Dealing with Multiple Versions

Because various data producers may publish data in a variety of OCSF Versions, the TA has multi-version support.
This means that if there is a defined mapping for a detected version, it will select the correct one. If the TA does not
contain a mapping for the detected version/event-class combination inside an event, it will simply pick the latest one.

### Completeness

Please refer to [MAPPING.md](MAPPING.md) to get an overview on the extend of the mapping.

### Limitations

-   Eventtypes are only tagged to be contained in the top-level data model. Datamodels lower in the hierarchy are not supported at this point.

## Prerequisites

-   Common Information Model (CIM) App

## Installation

-   Install the app on your Splunk Instance in the same places where the CIM App is installed.

## Setup

-   Configure the `ocsf_sourcetypes()` macro with a search string for all sourcetypes that are OCSF-formatted

Example:

```
(sourcetype=aws:asl OR sourcetype=ocsf)
```

## Development

This section is aimed at developers / data mappers that want to contribute to this repository

### Repository Structure

```
src/
├─ web/                                 <- React App (Configuration Page)
├─ package/                             <- Splunk App Sources
scripts/
├─ gen-props/
│  ├─ data_models.json                  <- Definitions of CIM data models and mapped fields
│  ├─ the_mapping.jsonnet               <- The Mapping file (important!)
│  ├─ transformations.jsonnet           <- Named transformations to enable reuse
│  ├─ gen_props.py
├─ gen_eventtypes.py
test/                                   <- Test scripts
```

### Setup

Create a virtual environment

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Development using Docker

Create an `.env` file in the repo root with a `SPLUNK_PASSWORD` variable.

```
cp .env.sample .env
nano .env   # change your password
```

With `docker-compose` installed, run

```
docker-compose up
```

After the provisioning is finished, log into `http://localhost:8000` using your password

### Defining Mappings

Mappings from CIM to OCSF are specified in a

### Generating Mappings

As described in the approach, lots of knowledge objects in this App are generated programatically.

Running

```
make build
```

will generate `props.conf`, `tags.conf` and `eventtypes.conf`. Review the `Makefile` for other targets if you need selective generation.

### Generating samples

Add a `SPLUNK_HEC_TOKEN` in your local env file. Next, run the `test/random_ocsf.py` script. Add the event class to generate as a positional argument.

```
python3 test/random_ocsf.py authentication -c 10 -s aws:asl
```

This will create 10 OCSF authentication events with the "aws:asl" sourcetype in your local test instance.

### Running the development server

If you're working on the UI, use the development server provided by webpack to auto-update the files on change. Note that this does not automatically regenerate the mappings.

```
make dev
```

### Packaging

To create a package from this repository

```
make package
```

## Contributing

### Adding a mapping

Mappings are defined in `scripts/gen-props/event_classes.libsonnet` in a JSON-like format.
