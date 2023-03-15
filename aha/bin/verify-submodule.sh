#!/bin/bash

CMD=$0
aha_branch=tmp-verify-submodule
HELP="""
  DESCRIPTION

    Uses a dummy aha branch '"$aha_branch"' to launch aha-flow regressions
    on the given submodule and branch/hash.

    Test progress can be monitored online at 
    https://buildkite.com/stanford-aha/aha-flow/builds?branch=tmp-verify-submodule

  EXAMPLES

    # Launch CI tests on the given submodule and branch or hash
    $CMD garnet spv-merge-to-spv-8
    $CMD garnet bebca3
"""

if [ "$1" == "--help" ]; then
    echo "$HELP"
    exit
fi

# Assume this script lives in $AHA/aha/bin
echo "--- cd to AHA repo root directory"

scriptpath=$0
scriptpath=`readlink $scriptpath || echo $scriptpath`  # Full path of script dir
scriptdir=${scriptpath%/*}  # E.g. "build_tarfile.sh" or "foo/bar"
cd $scriptdir/../..

###
# Die if not in the right place
git remote -v | grep StanfordAHA/aha.git > /dev/null && unset err || err=True
if [ $err ]; then
    echo ""
    echo "ERROR: Looks like we are not in aha repo"
    echo "$HELP"; exit 13
fi

# Use branch $aha_branch
echo "--- Use aha branch $aha_branch to launch the regression"

# Build the verification branch if it does not yet exist
if ! git checkout $aha_branch; then
    echo "WARNING: Looks like branch $aha_branch does not exist yet; I will create it for you"
    git checkout master; git pull
    git checkout -b $aha_branch
fi

# Clear out all the (existing) submodules (why?)
git submodule deinit -f --all
    
# Unpack args if it's not too late :)
# E.g. "$CMD garnet spv-merge-to-spv-8"
# submodule=garnet; branch=spVspV
submodule=$1; branch=$2

echo "--- Update submodule '$submodule' w given branch/hash '$branch'"
git submodule init $submodule
git submodule update $submodule
cd $submodule
git fetch origin
git checkout $branch; git pull
c=`git log | head -1 | cut -b 8-13`; echo $c

cd ..
echo "--- gcam 'verify garnet branch $branch ($c)'"
git commit -am "verify garnet branch $branch ($c)"
echo git push --set-upstream origin $aha_branch
git push --set-upstream origin $aha_branch

# Clean up the submodule
git submodule deinit $submodule

# Notify the user
echo "+++ REGRESSION LAUNCHED; for progress see"
echo https://buildkite.com/stanford-aha/aha-flow/builds
