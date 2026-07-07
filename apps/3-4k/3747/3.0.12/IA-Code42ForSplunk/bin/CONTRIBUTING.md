# CONTRIBUTING.md

## Testing

This project uses the [pytest](https://docs.pytest.org/) test framework.

### Installing

```shell
cd <repo_root>/Code42ForSplunk
pip install -e splunk-stubs/
pip install -e bin/
```

### Running tests

From the root of the repo (or `bin`), run:

```shell
pytest
```

_If the tests fail due to a `fixture 'mocker' not found` error and you are using a virtualenv environment, try
deactivating and reactivating the environment._

### Code analysis

The `tools/pylint-runner.sh` script checks for [pylint](https://www.pylint.org) errors against the python source files 
at the root of the bin directory. (We need something like this script because we don't have an official package of 
source files, so we can't simply run `pylint -E bin`.)