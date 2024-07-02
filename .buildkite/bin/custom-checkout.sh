#!/bin/bash

# What this script does:
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo.
# - Else check out master if triggered from submod push/pull.
# - Update and initialize all submodules.
# - If triggered from submod, update submod to match commit hash of triggering repo.

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4=">"   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "+++ BEGIN custom-checkout.sh"
echo I am in dir `pwd`

# Checkout master or BUILDKITE_COMMIT
aha_clone=$BUILDKITE_BUILD_CHECKOUT_PATH;
git clone https://github.com/StanfordAHA/aha $aha_clone; cd $aha_clone;
# REQUEST_TYPE comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then

    # This script is called only from pipeline.yml BDI step (I think).
    # BDI step should have put us in default aha branch (e.g. master or dev)
    echo "Pull request from a submod repo: stay in aha master branch"

    # Not sure why we need this 'git fetch' (below). Keeping it for legacy reasons...
    # THIS DOES NOT CHECKOUT MASTER; e.g. if we were on DEV_BRANCH, we stay there...
    git fetch -v --prune -- origin master

else
    echo "Push or PR from aha repo: check out requested aha branch '$BUILDKITE_COMMIT'"
    git fetch -v --prune -- origin $BUILDKITE_COMMIT
    git checkout -qf $BUILDKITE_COMMIT
fi
echo DEV_BRANCH=$DEV_BRANCH || echo okay
echo -n "DEV_BRANCH commit = "; git rev-parse $DEV_BRANCH || echo okay
echo -n "Aha master commit = "; git rev-parse master
echo -n "We now have commit: "; git rev-parse HEAD

echo "--- Initialize all submodules YES THIS TAKES AWHILE"

set -x
git submodule update --checkout # This is probably unnecessary but whatevs
git submodule foreach --recursive "git clean -ffxdq"
git submodule sync --recursive
echo "--- git submodule update --init --recursive --force"
git submodule update --init --recursive --force
echo '--- git submodule foreach --recursive "git reset --hard"'
git submodule foreach --recursive "git reset --hard"
set +x

# Update submod

# Note PR_REPO_TAIL comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$BUILDKITE_COMMIT'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $BUILDKITE_COMMIT)
fi

echo "--- END custom-checkout.sh"
