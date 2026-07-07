# This is not used by Splunk. This only exists to facilitate running unit tests from the command line. See
# CONTRIBUTING.md for more information on running tests.

from setuptools import find_packages, setup

setup(
    name="code42-for-splunk-modular-input",
    version="0.0.1",
    description="Code42 for Splunk Modular Input",
    packages=find_packages(),
    install_requires=["requests>=2.3",
                      "pytest==4.4.0",
                      "pytest-mock==1.10.3",
                      "splunk-stubs"]
)
