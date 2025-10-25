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

# This replaces ~/bin/pr_trigger.yml, which can now be deleted from khaki and r8cad
TRIGGER='
- trigger: "aha-flow"
  label: "PR check"
  build:
    message: "PR from ${BPPR_TAIL} \"${BUILDKITE_MESSAGE}\""
    commit: "${AHA_SUBMOD_FLOW_COMMIT}"
    env:
      BUILDKITE_PULL_REQUEST:      "${BUILDKITE_PULL_REQUEST}"
      BUILDKITE_PULL_REQUEST_REPO: "${BUILDKITE_PULL_REQUEST_REPO}"
      BUILDKITE_COMMIT:            "${AHA_SUBMOD_FLOW_COMMIT}"
      AHA_SUBMOD_FLOW_COMMIT:      "${AHA_SUBMOD_FLOW_COMMIT}"
      DEV_BRANCH:                  "${DEV_BRANCH}"
'

# BUILDKITE_PULL_REQUEST:      "232"
# BUILDKITE_PULL_REQUEST_REPO: "https://github.com/StanfordAHA/garnet.git"

TRIGGER_GARNET_PUSH='
- trigger: "aha-flow"
  label: "Garnet push"
  build:
    message: "Push from Garnet \"${BUILDKITE_MESSAGE}\""
    commit: "${AHA_SUBMOD_FLOW_COMMIT}"
    env:
      RSTEPS:                      "0"
      BUILDKITE_PULL_REQUEST:      "0"
      BUILDKITE_PULL_REQUEST_REPO: "https://github.com/StanfordAHA/garnet.git"
      BUILDKITE_COMMIT:            "${AHA_SUBMOD_FLOW_COMMIT}"
      AHA_SUBMOD_FLOW_COMMIT:      "${AHA_SUBMOD_FLOW_COMMIT}"
      DEV_BRANCH:                  "${DEV_BRANCH}"
'


TRIGGER_GARNET_PUSH0='
- trigger: "aha-flow"
  label: "Garnet push"
'

# E.g: `echo '{"repo":{"name":"garnet"}}' | get_json repo name`  => "garnet"
function get_json { python3 -c 'import sys,json;j=json.load(sys.stdin)
for f in sys.argv[1:]: j=j[f];
print(j)' $*; }

echo "+++ BEGIN custom-checkout.sh"
echo I am in dir `pwd`
cd /  # Start in a safe place!

# Correct the buildkite message, which may be wrong depending on
# whether we were triggered from a submodule.
# Do this right up front b/c metadata gets corrupted sometimes
# FIXME is this one of those times???
echo "Set metadata buildkite:git:commit to BUILDKITE_MESSAGE=$BUILDKITE_MESSAGE"
echo "$BUILDKITE_MESSAGE" | buildkite-agent meta-data set buildkite:git:commit

# should DIE if $BUILDKITE_CLEAN_CHECKOUT==true
if [ "$BUILDKITE_CLEAN_CHECKOUT" == "true" ]; then
    echo "
    ERROR: BUILDKITE_CLEAN_CHECKOUT=$BUILDKITE_CLEAN_CHECKOUT
    ERROR: It looks like maybe someone started a job manually from the
    ERROR: buildkite web interface and clicked the 'clean checkout' option
    ERROR: That's-a no good. I am .buildkite/bin/custom-checkout.sh
"
    exit 13
fi

echo "--- Must have a (empty!) working directory"
d=$BUILDKITE_BUILD_CHECKOUT_PATH;
/bin/rm -rf $d; mkdir -p $d; ls -ld $d; cd $d

echo "--- Clone the repo"
aha_clone=$BUILDKITE_BUILD_CHECKOUT_PATH;
git clone https://github.com/StanfordAHA/aha $aha_clone
cd $aha_clone;

# FIXME things break if DEV_BRANCH not set?
[ "$DEV_BRANCH" ] || export DEV_BRANCH=master

if ! git checkout -q $DEV_BRANCH; then
    export DEV_BRANCH=master
    echo "Cannot checkout dev branch '$DEV_BRANCH', continuing w master..."
fi

SKIP_SUBMOD_INIT=
save_reqtype=

# E.g. aha-flow online pipeline steps invokes '$0 --aha-flow'
if [ "$1" == "--aha-flow" ]; then
    echo "--- Found arg '$1'"
    save_reqtype=$REQUEST_TYPE; 
    export REQUEST_TYPE=NONE       # I.e. not doing submod-flow init
    SKIP_SUBMOD_INIT=True
fi

# E.g. aha-flow online pipeline steps invokes '$0 --aha-flow'
if [ "$1" == "--aha-submod-flow" ]; then
    echo "--- Found arg '$1'"
    #BOOKMARK
    # Submods only run regressions for pull requests
    # Except for Garnet, runs regressions on every git push

    function garnet { false; } 
    if [ "$BUILDKITE_PULL_REQUEST" == "false" ]; then
        echo not a pr. but is it garnet

        webhook="$(buildkite-agent meta-data get buildkite:webhook)"
        echo got webhook "$webhook"
#         repo="$(echo "$webhook" | jq -r '.repository.name')"
#         echo got repo "$repo"
#         if [ "$repo" == "garnet" ]; then

        # if echo "$webhook" | grep '"name":"garnet"' > /dev/null; then
        repo=$(echo "$webhook" | get_json repository name)
        if [ "$repo" == "garnet" ]; then
            echo oh my goodness it is a garnet repo oh me oh moo
            function garnet { true; }

#             echo export RSTEPS=0
#             export RSTEPS=0

            TRIGGER="$TRIGGER      RSTEPS: 0"

#             echo "$TRIGGER_GARNET_PUSH" | buildkite-agent pipeline upload
#             echo "--- CUSTOM CHECKOUT END - garnet-push edition";
#             return
        fi
    fi

    echo "Set BPPR_TAIL for later usage, e.g. BPPR_TAIL=canal";

  if garnet; then
      set -x; echo 'foo faw here i am garnetty'
      export BPPR_TAIL=garnet
      submod_commit=$(echo "$webhook" | get_json head_commit id)
  else

    export BPPR_TAIL=`echo "$BUILDKITE_PULL_REQUEST_REPO" | sed "s/.git\$//"` || echo fail;
    url=$BPPR_TAIL
    BPPR_TAIL=`echo "$BPPR_TAIL" | sed "s,http.*github.com/.*/,,"` || echo fail;

    # Find submod commit hash; use url calculated above
    # E.g. https://github.com/StanfordAHA/lake/pull/194
    # NOTE submod_commit must be full 40-char commit sha for status-update - DO NOT ABBREVIATE
    set -x;
    temp=$(mktemp -u tmp-deleteme-XXX); echo $temp
    curl $url/pull/$BUILDKITE_PULL_REQUEST > $temp;

    # It sometimes throws an error without the OOPS at the end (but why?)
    grep 'oid=' $temp | tr -cd '[:alnum:]=\n' | head -n 1 || echo OOPS;

    submod_commit=`cat $temp \
          | grep 'oid=' | tr -cd '[:alnum:]=\n' | tail -n 1 \
          | sed 's/.*oid=\(.*\)/\1/'`;
    /bin/rm $temp
  fi
    echo "found submod commit $submod_commit";

    # Debuggin
    cat <<EOF | buildkite-agent annotate --style "info" --context foofoo
    submod_commit=$submod_commit
    BUILDKITE_COMMIT=${BUILDKITE_COMMIT}
    BUILDKITE_BUILD_CHECKOUT_PATH=${BUILDKITE_BUILD_CHECKOUT_PATH}
EOF

    # Temporarily replace BUILDKITE_COMMIT env var with submod commit
    save_commit=$BUILDKITE_COMMIT;
    export BUILDKITE_COMMIT=$submod_commit;

    # Note, /home/buildkite-agent/bin/status-update must exist on agent machine
    # Also see ~steveri/bin/status-update on kiwi

    echo "+++ Notify github of pending status";
    ~/bin/status-update --force pending;

    # Restore BUILDKITE_COMMIT
    export BUILDKITE_COMMIT=$save_commit;

    # 'update-pr-repo.sh' will use AHA_SUBMOD_FLOW_COMMIT to set up links and such
    echo "Trigger aha-flow pipeline";
    export AHA_SUBMOD_FLOW_COMMIT=$submod_commit;

    # If buildkite checkout mechanism sees unset buildkite:git:commit meta-data, it will
    # use (incorrect) aha-repo commit message instead of (desired) submod commit message.

    echo "Set metadata buildkite:git:commit to BUILDKITE_MESSAGE=$BUILDKITE_MESSAGE"
    echo "$BUILDKITE_MESSAGE" | buildkite-agent meta-data set buildkite:git:commit

    echo "$TRIGGER" | buildkite-agent pipeline upload
    echo "--- CUSTOM CHECKOUT END";
      set +x
    return
fi

# Checkout appropriate aha branch.
# REQUEST_TYPE comes from e.g. set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then

    # This script is called only from pipeline.yml BDI step (I think).
    # BDI step should have put us in default aha branch (e.g. master or dev)
    echo "Pull request from a submod repo: stay in aha master branch"

    # Not sure why we need this 'git fetch' (below). Keeping it for legacy reasons...
    # THIS DOES NOT CHECKOUT MASTER; e.g. if we were on DEV_BRANCH, we stay there...
    git fetch -v --prune -- origin master

else
    echo "Push or PR from aha repo: check out requested aha branch '$BUILDKITE_COMMIT'"

    # My scripts don't deal well with a commit that's not a full hash!
    [ "$BUILDKITE_COMMIT" == "HEAD" ] && export BUILDKITE_COMMIT=`git rev-parse HEAD`
    git fetch -v --prune -- origin $BUILDKITE_COMMIT || echo okay

    if ! git checkout -qf $BUILDKITE_COMMIT; then
        echo "Submod commit hash not found, using aha master branch";
        git checkout -q $DEV_BRANCH || echo "No dev branch found, continuing w master..."; fi;
fi

echo DEV_BRANCH=$DEV_BRANCH || echo okay
echo -n "DEV_BRANCH commit = "; git rev-parse origin/$DEV_BRANCH || echo okay
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
else
    echo "Skip lengthy submodule initialization"
fi

# Update submod. Note PR_REPO_TAIL comes from set-trigfrom-and-reqtype.sh
if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
    c=$AHA_SUBMOD_FLOW_COMMIT  # This is more stable/accurate vs. $BUILDKITE_COMMIT
    echo "--- Update submodule '$PR_REPO_TAIL' w commit '$c'"
    (set -x; cd $PR_REPO_TAIL; git fetch origin && git checkout $c)
fi

# Restore original REQUEST_TYPE value, even though I think it's maybe never used again...
[ "${save_reqtype}" ] && export REQUEST_TYPE=${save_reqtype}

# Can do '--aha-flow --early-out' to skip pipeline upload etc.
if [ "$2" == "--early-out" ]; then
    echo "Found early out switch, guess we are DONE"

elif [ "$1" == "--aha-flow" ]; then
    echo "+++ Notify github of pending status"

    # Note, /home/buildkite-agent/bin/status-update must exist on agent machine
    # Also see ~steveri/bin/status-update on kiwi
    ~/bin/status-update --force pending;

    echo "--- Upload pipeline.yml"
    buildkite-agent pipeline upload .buildkite/pipeline.yml;
fi

echo "--- END custom-checkout.sh"
