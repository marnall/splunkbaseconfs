Introduction
------------
This app provides field extractions and input caputuring for bash history files

Installation
------------
To install this app, extract the .spl file to $SPLUNK_HOME/etc/apps/


You will also want to add the following to /etc/bashrc

export HISTCONTROL=ignoreboth
shopt -s cmdhist
export HISTTIMEFORMAT='%Y-%m-%d,%H:%M:%S: '
shopt -s histappend
export HISTFILESIZE="500000"
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND ; }"'echo $$ $USER \ "$(history 1)" >> ~/.bash_permanent_history'
readonly HISTCONTROL
readonly HISTFILE
readonly PROMPT_COMMAND
