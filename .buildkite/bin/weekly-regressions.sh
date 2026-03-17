#!/bin/bash

HELP='

  DESCRIPTION generate yml steps for buildkite job that will run full
  config as multiple steps for use in doing something like

  --test  display commands necessary to run full config as separate chunks
  --verify <filename>   make sure all groups are represented in file "weekly.yml"
  --gen                 auto-generate a new buildkite file
'

# Must find the "app" app before we can do anything
# Our home should be $AHA/.buildkite/bin/weekly-regressions.sh
# app should be $AHA/aha/bin/app

function where_this_script_lives {

    local cmd="$0"    # Is script being executed or sourced?
    [ "${BASH_SOURCE[0]}" -ef "$0" ] || cmd="${BASH_SOURCE[0]}" 

    local scriptpath=`realpath $cmd`       # Full path of script e.g. "/foo/bar/baz.sh"
    local scriptdir=${scriptpath%/*}       # Script dir e.g. "/foo/bar"
    scriptdir=$(cd $scriptdir; pwd)       # Get abs path instead of rel
    [ "$scriptdir" == `pwd` ] && scriptdir="."
    echo $scriptdir
}
script_home=`where_this_script_lives`
echo $script_home

AHA=$(cd ../../; pwd); echo $AHA
app=$AHA/aha/bin/app; ls -l $app
printf '\n\n'

# Little hack to list all groups in 'full' config
groups=$($app --debug --show fast | awk -F, '$1=="full"{print $2}' | uniq)
echo "$groups"
printf '\n\n'


# Generate a yaml file for the groups I guess
printf '========================================================================\n'
for group in $groups; do
printf "    - label: $group\n"
printf "      command: aha/bin/app --update . /aha/aha --subgroup full $group\n"
printf "      wait: ~\n"
done
# 
# 
# 
# # Generate buildkite steps
# TEMPLATE='
#     - label: "GROUP"
#       command: aha/bin/app --update . /aha/aha --subgroup full GROUP
# '
# exit


# Hey let's do '--gen' first that looks like fun

