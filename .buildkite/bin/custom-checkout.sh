#!/bin/bash

# What this script does:
# - Update and initialize all aha repo submodules.
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo
#   or AHA DEFAULT (no-heroku now, master later) if triggered from submod push/pull.
# - If triggered from submod, update submod to match commit hash of triggering repo.

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4="_"   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "--- CHECKOUT FULL REPO, submodules and all"

# Checkout
echo "+++ custom-checkout.sh BEGIN"
echo I am `whoami`
echo I am in dir `pwd`
cd $BUILDKITE_BUILD_CHECKOUT_PATH    # Just in case, I dunno, whatevs.

if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "Pull request from a submod repo: check out aha master branch"
    git fetch -v --prune -- origin master
    git checkout -qf master
else
    echo "Push or PR from aha repo: check out requested aha branch"
    git fetch -v --prune -- origin $BUILDKITE_COMMIT
    git checkout -qf $BUILDKITE_COMMIT
fi

# This is maybe slow (ish) so don't do it at the beginning...
echo "--- PREP AHA REPO and all its submodules"; set -x
pwd
# E.g. CHECKOUT_PATH=/var/lib/buildkite-agent/builds/r7cad-docker-1/stanford-aha/aha-flow
cd $BUILDKITE_BUILD_CHECKOUT_PATH # Actually I think we're already there but whatevs
git remote set-url origin https://github.com/StanfordAHA/aha
git submodule update --checkout # This is probably unnecessary but whatevs
git submodule foreach --recursive "git clean -ffxdq"
git clean -ffxdq
set +x

echo "--- Initialize submodules YES THIS TAKES AWHILE"
set -x
git submodule sync --recursive
echo "--- git submodule update --init --recursive --force"
git submodule update --init --recursive --force
echo '--- git submodule foreach --recursive "git reset --hard"'
git submodule foreach --recursive "git reset --hard"
set +x

# update_repo=`git config --get remote.origin.url`

if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$BUILDKITE_COMMIT'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $BUILDKITE_COMMIT)
fi

echo "--- custom-checkout.sh END"
