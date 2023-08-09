#!/bin/bash

set +u # nounset? not on my watch!
set +x # debug OFF

echo "--- custom-checkout.sh BEGIN"

# export MYTMP='/var/lib/buildkite-agent/builds/$BUILDKITE_BUILD_NUMBER'
# Steps (https://buildkite.com/stanford-aha/aha-flow/settings/steps)
# set MYTMP='/var/lib/buildkite-agent/builds/$BUILDKITE_BUILD_NUMBER'

# Expand MYTMP from '/var/lib/buildkite-agent/builds/$BUILDKITE_BUILD_NUMBER'
# to e.g. '/var/lib/buildkite-agent/builds/4458'
MYTMP=`eval echo $MYTMP`

# BUILDKITE_BUILD_CHECKOUT_PATH=/var/lib/buildkite-agent/builds/r7cad-docker-1/stanford-aha/aha-flow
echo I am `whoami`     # Watch out if this ever says "I am root"
echo I am in dir `pwd` # We are in root dir (/) !!!oh no!!!


set -x
# This script runs from root dir. Flee to safety!
# Note NOTHING SHOULD HAPPEN in this safe space, soon we will cd to working dir, see below.
if ! [ "$MYTMP" ]; then echo ERROR MYTMP NOT SET; exit 13; fi
cd $MYTMP
set +x


echo "+++ Check on our trash"
set -x
find /tmp -user buildkite-agent 2> /dev/null || echo okay
echo "----------------------------------------------"
find $MYTMP -user buildkite-agent 2> /dev/null || echo okay
echo "----------------------------------------------"
du -x --max-depth=0 $MYTMP || echo okay
d=$(cd $MYTMP/..; pwd) || echo okay
du -x --max-depth=0 $d || echo okay
set +x

echo "--- Continue"

# IF this works it enables all kinds of optimiztions
# Okay. Like what for example?
echo FLOW_REPO=$FLOW_REPO || echo nop
echo FLOW_HEAD_SHA=$FLOW_HEAD_SHA || echo nop

echo '-------------'
 
echo "--- CLONE AHA REPO"

# Start with a clean slate. Could be bad news if files leftover from previous runs.
d=$BUILDKITE_BUILD_CHECKOUT_PATH

# temporary check to make sure we are doing the right thing
# DELETE this blockafter i dunno like 08/13/2023 or so
d1=/var/lib/buildkite-agent/builds/$BUILDKITE_AGENT_NAME/stanford-aha/aha-flow
[ "$d" == "$d1" ] || exit 13

if test -d $d; then
  echo "+++ WARNING checkout dir $d exists"
  echo "Deleting $d ..."
  /bin/rm -rf $d || echo nop
fi

echo "--- CLONE AHA REPO AND INIT ALL SUBMODULES"
git clone --recurse-submodules https://github.com/hofstee/aha $d
# git clone https://github.com/hofstee/aha $d

cd $d

set -x
git remote set-url origin https://github.com/hofstee/aha
git submodule foreach --recursive "git clean -ffxdq"
git clean -ffxdq

unset PR_FROM_SUBMOD
# PR_FROM_SUBMOD means build was triggered by foreign (non-aha) repo, i.e. one of the submods

echo git fetch -v --prune -- origin $BUILDKITE_COMMIT
if   git fetch -v --prune -- origin $BUILDKITE_COMMIT; then
    echo "Checked out aha commit '$BUILDKITE_COMMIT'"
else
    echo '-------------------------------------------'
    echo 'REQUESTED COMMIT DOES NOT EXIST in aha repo'
    echo 'This must be a pull request from one of the submods'
    PR_FROM_SUBMOD=true

    AHA_DEFAULT_BRANCH=master
    AHA_DEFAULT_BRANCH=no-heroku
    echo "Meanwhile, will use default branch '$AHA_DEFAULT_BRANCH' for aha repo"
    git fetch -v --prune -- origin $AHA_DEFAULT_BRANCH
fi

set -x
git checkout -f $BUILDKITE_COMMIT
git submodule sync --recursive
git submodule update --init --recursive --force
git submodule foreach --recursive "git reset --hard"
set +x


if [ "$PR_FROM_SUBMOD" ]; then
    echo "--- Handle PR"
    echo "--- Looking for submod commit $BUILDKITE_COMMIT"
    unset FOUND_SUBMOD
    for submod in garnet Halide-to-Hardware lassen gemstone canal lake; do
        echo "--- - " Looking in submod $submod
        # (cd $submod; git checkout $BUILDKITE_COMMIT && echo UPDATE SUBMOD $submod || echo NOT $submod);
        (set -x; cd $submod; git fetch origin && git checkout $BUILDKITE_COMMIT) && FOUND_SUBMOD=true || echo "--- -- NOT " Ssubmod
        [ "$FOUND_SUBMOD" ] && echo "--- -- FOUND " $submod
        [ "$FOUND_SUBMOD" ] && break
    done
    echo now i am here

    # tmp-vars holds e.g. FLOW_REPO and FLOW_HEAD_SHA vars for later commands e.g.
    # commands:
    #   - source custom-checkout.sh           # Sets tmp.vars
    #   - source tmp.vars; echo $FLOW_REPO    # Uses tmp.vars
    # NO no need for tmp-vars.
    set -x
    if [ "$FOUND_SUBMOD" ]; then
        # These are used later by pipeline.xml
        # BUT NOT as global env vars; this script must
        # be sourced in same scope as var usage, see?
        pwd # Should be e.g. /var/lib/buildkite-agent/builds/r7cad-docker-2/stanford-aha/aha-flow
        test -e tmp-vars && /bin/rm -rf tmp-vars
        echo "FLOW_REPO=$submod; export FLOW_REPO" >> tmp-vars
        echo "FLOW_HEAD_SHA=$BUILDKITE_COMMIT; export FLOW_HEAD_SHA" >> tmp-vars
    else
        echo "ERROR could not find requesting submod"; exit 13
    fi
    set +x
else
    echo "--- NOT A PULL REQUEST"
fi

echo '+++ FLOW_REPO?'
set -x
ls -l tmp-vars 2> /dev/null || echo no
cat tmp-vars   2> /dev/null || echo no
set +x


# https://github.com/StanfordAHA/garnet/blob/aha-flow-no-heroku/TEMP/custom-checkout.sh
# https://raw.githubusercontent.com/StanfordAHA/garnet/aha-flow-no-heroku/TEMP/custom-checkout.sh
# curl -s https://raw.githubusercontent.com/StanfordAHA/garnet/aha-flow-no-heroku/TEMP/custom-checkout.sh > /tmp/tmp
# BUILDKITE_BUILD_NUMBER

# Temporarily, for dev purposes, load pipeline from garnet repo;
# later replace aha repo .buildkite/pipeline.yml w dev from garnet, see?

# if [ "$FOUND_SUBMOD" ]; then
#   if [ "$submod" == "garnet" ]; then

if (cd garnet; git log remotes/origin/aha-flow-no-heroku | grep $BUILDKITE_COMMIT); then
    echo "+++ FOR NOW, load pipeline from garnet aha-flow-no-heroku"
    # echo "  BEFORE: " `ls -l .buildkite/pipeline.yml`
    u=https://raw.githubusercontent.com/StanfordAHA/garnet/aha-flow-no-heroku/TEMP/pipeline.yml
    curl -s $u > .buildkite/pipeline.yml
    # echo "  curl -s $u > .buildkite/pipeline.yml"
    # echo "  AFTER:  " `ls -l .buildkite/pipeline.yml`
fi

pwd
echo "--- custom-checkout.sh END"





##############################################################################
# TRASH

# echo "+++ checkout.sh cleanup"
# rm /tmp/ahaflow-custom-checkout-83* || echo nop
# rm /tmp/ahaflow-custom-checkout-84[01]* || echo nop

# ########################################################################
# echo "+++ checkout.sh trash"
# echo '-------------'
# ls -l /tmp/ahaflow-custom-checkout* || echo nope
# 
# echo '-------------'
# ls -ld /var/lib/buildkite-agent/builds/*[1-8]/stanford-aha/aha-flow/ || echo nope
# 
# echo '-------------'
# ls -ld /var/lib/buildkite-agent/builds/*[1-8]/stanford-aha/aha-flow/aha || echo nope
# 
# echo '-------------'
# ls -ld /var/lib/buildkite-agent/builds/*[1-8]/stanford-aha/aha-flow/.buildkite/hooks || echo nope
# 
# echo '-------------'
# ls -ld /var/lib/buildkite-agent/builds/*[1-8]/stanford-aha/aha-flow-aha/.buildkite/hooks || echo nope

# # If temp subdir contains files owned by root, that's bad.
# # Delete the entire directory if this is found to be true.
# echo "+++ PURGE BAD TEMP FILES"
# echo I am `whoami`
# for d in /var/lib/buildkite-agent/builds/*/stanford-aha/aha-flow/temp/; do
#     if (ls -laR $d | grep root); then
#         echo "WARNING found root-owned objects in $d"
#         set -x; /bin/rm -rf $d; set +x
#     fi
# done

# Current mechanism is such that
# - heroku is detected in prior upload-pipeline.sh script
# - which then loads OLD pipeline.xml, which does NOT use this checkout script. Right?
# # This is supposed to detect heroku jobs
# if [ "$BUILDKITE_STEP_KEY" == "" ]; then
#     if [ "$FLOW_REPO" ]; then
#         # set commit to "master" and let default pipeline do the rest
#         echo "--- HEROKU DETECTED"
#         BUILDKITE_COMMIT=master
#         echo Reset BUILD_COMMIT=$BUILD_COMMIT
#     fi
# fi

# # No!
# f='/tmp/ahaflow-custom-checkout-$BUILDKITE_BUILD_NUMBER.sh'
# test -f $f && /bin/rm $f
# 
# 
# echo "--- CONTINUE"
# ########################################################################

# # save and restore existing shell opts in case script is sourced
# RESTORE_SHELLOPTS="$(set +o)"





# echo "+++ WHAT IS UP WITH THE HOOKS?"
# # set -x
# # echo '--------------'
# # git branch
# # echo '--------------'
# # git status -uno
# ls -l .buildkite/hooks || echo nop
# cat .buildkite/hooks/post-checkout || echo hop
# set +x
# 
# echo '+++ HOOKS 155'
# pwd
# ls -l .buildkite/hooks || echo nop
# grep foo .buildkite/hooks/* || echo nop

# Yeah we don't do this no more
# echo "--- RESTORE SHELLOPTS"
# eval "$RESTORE_SHELLOPTS"

