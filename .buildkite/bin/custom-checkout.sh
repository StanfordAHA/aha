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
echo "--- See if we need to update a submodule"
unset PR_FROM_SUBMOD

# PR_FROM_SUBMOD means build was triggered by foreign (non-aha) repo,
# i.e. one of the submods. The submod sends its commit hash BUT DOES
# NOT TELL US WHAT REPO IT IS. :(

# We detect this by attempting to fetch BUILDKITE_COMMIT from aha repo.
# Success means this is an aha-triggered build. Failure means we need to
# find what repo actually did trigger the commit.

echo git fetch -v --prune -- origin $BUILDKITE_COMMIT
if   git fetch -v --prune -- origin $BUILDKITE_COMMIT; then

    # Pretty sure we already did this, in pipeline.xml BDI step pre-checkout hook
    # But what the heck, let's do it again, don't break what is working already.
    git checkout -f $BUILDKITE_COMMIT
    echo "Found aha commit '$BUILDKITE_COMMIT'; no need to update submodule"

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

update_repo=`git remote git_url origin`

# To find out what repo triggered the commit, we iterate through
# all the submodules and find which one can successfully checkout
# the desired BUILKITE_COMMIT.

if [ "$PR_FROM_SUBMOD" ]; then
    echo "--- Handle PR"
    echo "+++ Looking for submod commit $BUILDKITE_COMMIT"
    unset FOUND_SUBMOD
    for submod in garnet Halide-to-Hardware lassen gemstone canal lake hwtypes; do
        echo "--- - " Looking in submod $submod
        # --- THIS IS WHERE THE CHECKOUT HAPPENS ---
        (set -x; cd $submod; git fetch origin && git checkout $BUILDKITE_COMMIT) && FOUND_SUBMOD=true || echo "NOT " $submod
        [ "$FOUND_SUBMOD" ] && echo "--- -- FOUND " $submod
        [ "$FOUND_SUBMOD" ] && break
    done

    if [ "$FOUND_SUBMOD" ]; then
        echo "--- Updated submodule '$submod' w commit '$BUILDKITE_COMMIT'"
        update_repo=`cd $submod; git remote git_url origin`
    else
        echo "ERROR could not find requesting submod"; exit 13
    fi
    set +x
else
    echo "--- NOT A PULL REQUEST"
fi

echo "+++ NOTIFY GITHUB OF PENDING JOB"
echo "Sending update to repo $update_repo"
~buildkite-agent/bin/status-update $BUILDKITE_BUILD_NUMBER $update_repo $BUILDKITE_COMMIT pending

echo "--- custom-checkout.sh END"
