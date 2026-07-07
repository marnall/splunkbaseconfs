#!/bin/bash
script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export LD_LIBRARY_PATH=$script_dir
cd $script_dir
args='-h '$1' -n '$2' -p '$3' -o ../certs/'$4
cmd='./opsec-tools/opsec_pull_cert '$args
$cmd
