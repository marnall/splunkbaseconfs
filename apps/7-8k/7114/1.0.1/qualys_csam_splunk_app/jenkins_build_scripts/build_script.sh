#!/bin/bash
set -ex
source "${WORKSPACE}/jenkins_build_scripts/variables"
export JAVA_HOME=/opt/qualys/java/jdk8
/opt/qualys/maven/apache-maven-3.6.3/bin/mvn clean deploy -P rpm -U -Dmaven.test.skip=true

