# AWS Phantom App

A Phantom app that facilitates interaction with the AWS API.

### Install dependencies (as root)
    phenv pip2.7 install boto3

### Installing from command line (as phantom user)
    su phantom
    phenv python2.7 /opt/phantom/bin/compile_app.pyc -i

### Currently supported AWS Services
- EC2
- IAM
- Lambda
