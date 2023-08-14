#!/bin/bash

# What this script does:
# - Update and initialize all aha repo submodules
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo
#   or AHA DEFAULT (no-heroku now, master later) if triggered from submod push/pull
# - If triggered from submod, update submod to match commit hash of triggering repo

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4="_"   # Prevents "+++" prefix during 3-deep set -x execution

# Checkout
echo "+++ custom-checkout.sh BEGIN"
echo I am `whoami`     # Watch out if this ever says "I am root"
echo I am in dir `pwd` # Watch out if this ever we are in root dir (/)

echo "--- PREP AHA REPO and all its submodules"; set -x
pwd
# E.g. CHECKOUT_PATH=/var/lib/buildkite-agent/builds/r7cad-docker-1/stanford-aha/aha-flow
cd $BUILDKITE_BUILD_CHECKOUT_PATH # Actually I think we're already there but whatevs

git submodule update --checkout # This is probably unnecessary but whatevs
git remote set-url origin https://github.com/hofstee/aha
git submodule foreach --recursive "git clean -ffxdq"
git clean -ffxdq
set +x

# Would this work for heroku maybe? Surely this would work for heroku.

# Heroku always sets message to "PR from <repo>" with BUILDKITE_COMMIT="HEAD"
# so as to checkout aha master. Heroku sends desired submod commit <repo>
# hash as env var FLOW_HEAD_SHA.  In this new regime, we set BUILDKITE_COMMIT
# as the desired submod commit, and auto-discover the repo that goes with the commit.

if expr "$$BUILDKITE_MESSAGE" : "PR from "; then
    BUILDKITE_COMMIT=$FLOW_HEAD_SHA
fi

AHA_DEFAULT_BRANCH=no-heroku
echo "--- Check out appropriate AHA branch: $BUILDKITE_COMMIT, $AHA_DEFAULT_BRANCH, or master"
unset PR_FROM_SUBMOD

# PR_FROM_SUBMOD means build was triggered by foreign (non-aha) repo,
# i.e. one of the submods. The submod sends its commit hash BUT DOES
# NOT TELL US WHAT REPO IT IS. :(

# We detect this by attempting to checkout BUILDKITE_COMMIT from aha repo.
# Success means this is an aha-triggered build. Failure means we need to
# find what repo actually did trigger the commit.

echo git fetch -v --prune -- origin $BUILDKITE_COMMIT
if   git fetch -v --prune -- origin $BUILDKITE_COMMIT; then
    git checkout -f $BUILDKITE_COMMIT
    echo "Checked out aha commit '$BUILDKITE_COMMIT'"
else
    echo '-------------------------------------------'
    echo 'REQUESTED COMMIT DOES NOT EXIST in aha repo'
    echo 'This must be a pull request from one of the submods'
    PR_FROM_SUBMOD=true

    # FIXME don't need if-then-else below fter dev merges to master.
    
    # Use dev branch as default until it gets merged and deleted.
    AHA_DEFAULT_BRANCH=no-heroku
    echo "Meanwhile, will use default branch '$AHA_DEFAULT_BRANCH' for aha repo"
    if git fetch -v --prune -- origin $AHA_DEFAULT_BRANCH; then
        echo "Fetching aha branch '$AHA_DEFAULT_BRANCH'"
        git checkout -f $AHA_DEFAULT_BRANCH
    else
        echo "Aha branch '$AHA_DEFAULT_BRANCH' does not exist"
        echo "Fetching aha master branch"
        git fetch -v --prune -- origin master
        git checkout -f master
    fi
fi

set -x
git submodule sync --recursive
echo "--- git submodule update --init --recursive --force"
git submodule update --init --recursive --force
echo '--- git submodule foreach --recursive "git reset --hard"'
git submodule foreach --recursive "git reset --hard"
set +x

# To find out what repo triggered the commit, we iterate through
# all the submodules and find which one can successfully checkout
# the desired BUILKITE_COMMIT.

if [ "$PR_FROM_SUBMOD" ]; then
    echo "--- Handle PR"
    echo "--- Looking for submod commit $BUILDKITE_COMMIT"
    unset FOUND_SUBMOD
    for submod in garnet Halide-to-Hardware lassen gemstone canal lake; do
        echo "--- - " Looking in submod $submod
        # --- THIS IS WHERE THE CHECKOUT HAPPENS ---
        (set -x; cd $submod; git fetch origin && git checkout $BUILDKITE_COMMIT) && FOUND_SUBMOD=true || echo "--- -- NOT " Ssubmod
        [ "$FOUND_SUBMOD" ] && echo "--- -- FOUND " $submod
        [ "$FOUND_SUBMOD" ] && break
    done

    if [ "$FOUND_SUBMOD" ]; then
        echo "--- Checked out submodule '$submod', commit '$BUILDKITE_COMMIT'"
    else
        echo "ERROR could not find requesting submod"; exit 13
    fi
    set +x
else
    echo "--- NOT A PULL REQUEST"
fi
echo "--- custom-checkout.sh END"



##############################################################################
# TRASH

# echo "--- BEGIN CLEANUP"
# 
# function cleanup {
#     dir=$1; ndays=$3
# 
# #     echo "SPACE"
# #     du -hx --max-depth=0 $dir/* 2> /dev/null || echo no
# #     echo "----------------------------------------------"
# 
#     echo "TIME"
#     FIND="find $dir -maxdepth 1 -user buildkite-agent"
#     files=`$FIND 2> /dev/null`
#     ls -ltd $files | cat -n
#     echo "----------------------------------------------"
# 
#     echo "PURGE/BEFORE"
#     ntrash=`$FIND 2> /dev/null | wc -l` || echo Ignoring find-command problem
#     echo "Found $ntrash buildkite-agent files in $dir"
#     echo "----------------------------------------------"
# 
#     echo "PURGE/PURGE delete files older than 24 hours"
#     $FIND -mtime +$ndays -exec /bin/rm -rf {} \; || echo Ignoring find-command problem
#     echo "----------------------------------------------"
# 
#     echo "PURGE/AFTER"
#     ntrash=`$FIND 2> /dev/null | wc -l` || echo Ignoring find-command problem
#     echo "Found $ntrash buildkite-agent files in $dir"
#     echo "----------------------------------------------"
# }
# 
# set +x
# echo "--- Check on our trash in /tmp"
# cleanup /tmp older-than 1 days
# 
# echo "--- END CLEANUP"
