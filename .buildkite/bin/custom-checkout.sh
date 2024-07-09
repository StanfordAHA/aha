#!/bin/bash

# Invoked from e.g. pipeline.yml and online aha-flow, aha-submod-flow steps maybe

# What this script does:
# - Check out aha branch BUILDKITE_COMMIT if build triggered from aha repo.
# - Else check out master if triggered from submod push/pull.
# - Update and initialize all submodules.
# - If triggered from submod, update submod to match commit hash of triggering repo.

# Setup
set +u    # nounset? not on my watch!
set +x    # debug OFF
PS4="."   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "+++ BEGIN custom-checkout.sh"
echo I am in dir `pwd`

# args. arg.
SKIP_SUBMOD_INIT=
save_reqtype=
if [ "$1" == "--aha-flow" ]; then
    # E.g. aha-flow online pipeline steps invokes '$0 --aha-flow'
    echo "--- Found arg '$1'"
    DEV_BRANCH=master  # I.e. not using a dev branch atm
    export DEV_BRANCH=$DEV_BRANCH  # FIXME things break if DEV_BRANCH not set?

    save_reqtype=$REQUEST_TYPE
    export REQUEST_TYPE=NONE
    SKIP_SUBMOD_INIT=True
    # source custom-checout.sh --skip-submod-init
    # if [ "save_reqtype"]; then export REQUEST_TYPE=${save_reqtype}; fi
    # export REQUEST_TYPE=${save_reqtype}
fi

echo "--- Must have a (empty!) working directory"
d=$BUILDKITE_BUILD_CHECKOUT_PATH;
/bin/rm -rf $d; mkdir -p $d; ls -ld $d; cd $d

echo "--- Clone the repo"
aha_clone=$BUILDKITE_BUILD_CHECKOUT_PATH;
test -e $aha_clone/.git || git clone https://github.com/StanfordAHA/aha $aha_clone
cd $aha_clone;

if [ "$1" == "--aha-submod-flow" ]; then
    # E.g. aha-flow online pipeline steps invokes '$0 --aha-flow'
    echo "--- Found arg '$1'"

    echo "Set BPPR_TAIL for later usage, e.g. BPPR_TAIL=canal";
    export BPPR_TAIL=`echo "$BUILDKITE_PULL_REQUEST_REPO" | sed "s/.git\$//"` || echo fail;
    url=$BPPR_TAIL
    BPPR_TAIL=`echo "$BPPR_TAIL" | sed "s,http.*github.com/.*/,,"` || echo fail;

    # Find submod commit hash; use url calculated above
    # E.g. https://github.com/StanfordAHA/lake/pull/194
    set -x;
    curl $url/pull/$BUILDKITE_PULL_REQUEST > tmp;
    grep 'oid=' tmp | tr -cd '[:alnum:]=\n' | head -n 1;
    grep 'oid=' tmp | tr -cd '[:alnum:]=\n' | head -n 1 || echo OOPS;

    # No good; must have full 40-char commit sha
    # Also: should I guess be TAIL, not head, -n 1 ?
    # submod_commit=`curl -s $url/pull/$BUILDKITE_PULL_REQUEST \
    #       | grep 'oid=' | tr -cd '[:alnum:]=\n' | head -n 1 \
    #       | sed 's/.*oid=\(.......\).*/\1/'`;

    submod_commit=`curl -s $url/pull/$BUILDKITE_PULL_REQUEST \
          | grep 'oid=' | tr -cd '[:alnum:]=\n' | tail -n 1 \
          | sed 's/.*oid=\(.*\)/\1/'`;

    echo "found submod commit $submod_commit";
    save_commit=$BUILDKITE_COMMIT;
    export BUILDKITE_COMMIT=$submod_commit;

    # See what this does maybe
    cat <<EOF | buildkite-agent annotate --style "info" --context foofoo
    BUILDKITE_PULL_REQUEST_REPO=${BUILDKITE_PULL_REQUEST_REPO}
    BUILDKITE_PULL_REQUEST=${BUILDKITE_PULL_REQUEST}
    BUILDKITE_COMMIT=${BUILDKITE_COMMIT}
    BUILDKITE_BUILD_CHECKOUT_PATH=${BUILDKITE_BUILD_CHECKOUT_PATH}
    BUILDKITE_MESSAGE=${BUILDKITE_MESSAGE}
    BPPR_TAIL=${BPPR_TAIL}
EOF

    # Note, /home/buildkite-agent/bin/status-update must exist on agent machine
    # Also see ~steveri/bin/status-update on kiwi
    echo "+++ Notify github of pending status";
    ~/bin/status-update --force pending;

    # 'update-pr-repo.sh' will use AHA_SUBMOD_FLOW_COMMIT to set up links and such
    export BUILDKITE_COMMIT=$save_commit;
    echo "Trigger aha-flow pipeline";
    export AHA_SUBMOD_FLOW_COMMIT=$submod_commit;

    # If we don't set meta-data here, buildkite default checkout will overwrite
    # submod commit message with aha-repo commit message instead.
    echo "Reset metadata buildkite:git:commit to BUILDKITE_MESSAGE=$BUILDKITE_MESSAGE"
    echo "$BUILDKITE_MESSAGE" | buildkite-agent meta-data set buildkite:git:commit

    # buildkite-agent pipeline upload .buildkite/pr_trigger.yml;
    buildkite-agent pipeline upload ~/bin/pr_trigger.yml;
    echo "--- CUSTOM CHECKOUT END";
    return
fi

# Checkout master or BUILDKITE_COMMIT
# REQUEST_TYPE comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then

    # This script is called only from pipeline.yml BDI step (I think).
    # BDI step should have put us in default aha branch (e.g. master or dev)
    echo "Pull request from a submod repo: stay in aha master branch"

    # Not sure why we need this 'git fetch' (below). Keeping it for legacy reasons...
    # THIS DOES NOT CHECKOUT MASTER; e.g. if we were on DEV_BRANCH, we stay there...
    git fetch -v --prune -- origin master

else
    # My scripts don't deal well with a commit that's not a full hash!
    if [ "$BUILDKITE_COMMIT" == "HEAD" ]; then
        BUILDKITE_COMMIT=`git rev-parse HEAD`; fi

    echo "Push or PR from aha repo: check out requested aha branch '$BUILDKITE_COMMIT'"
    git fetch -v --prune -- origin $BUILDKITE_COMMIT || echo okay
    # git checkout -qf $BUILDKITE_COMMIT
    if ! git checkout -qf $BUILDKITE_COMMIT; then
        echo "Submod commit hash found, using aha master branch";
        git checkout -q $DEV_BRANCH || echo "No dev branch found, continuing w master..."; fi;
fi
echo DEV_BRANCH=$DEV_BRANCH || echo okay
echo -n "DEV_BRANCH commit = "; git rev-parse $DEV_BRANCH || echo okay
echo -n "Aha master commit = "; git rev-parse master
echo -n "We now have commit: "; git rev-parse HEAD

if ! [ "$SKIP_SUBMOD_INIT" ]; then
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
fi

# Update submod

# Note PR_REPO_TAIL comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$BUILDKITE_COMMIT'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $BUILDKITE_COMMIT)
fi

if [ "$1" == "--aha-flow" ]; then
    export REQUEST_TYPE=${save_reqtype}

    # Note, /home/buildkite-agent/bin/status-update must exist on agent machine
    # Also see ~steveri/bin/status-update on kiwi

    echo "+++ Notify github of pending status"
    ~/bin/status-update --force pending;

    echo "--- Upload pipeline.yml"
    buildkite-agent pipeline upload .buildkite/pipeline.yml;
fi

echo "--- END custom-checkout.sh"
