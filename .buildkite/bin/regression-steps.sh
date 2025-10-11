#!/bin/bash



# FIXME delete before final check-in
export CONFIG=full  # Trying a thing: BEFORE



# This is designed to be called from pipeline.yml
set -x

# "full" is a special case why not
if [ "$CONFIG" == "full" ]; then
    if [ "$next" != "--cleanup" ]; then
        # Delete ALL steps, run full config as step "1" i.e. set $1="1"
        set -- "1"  # This deletes all other steps so only 'full' runs and only runs once
    fi
fi

# Uncomment for debugging maybe; e.g. uncomment and then run "$0 build gold 0 1 2" etc.
# function buildkite-agent { [ "$2" == "upload" ] && cat; }
# function bkmsg { echo "$1"; }

# Run first reg step on command line, then recurse on remaining args.
# E.g. "$0 build gold 0 1 2" launches the build step(s) and then calls "$0 gold 0 1 2"
# Regression step 0 = "fast"; steps 1,2,3... = "pr_aha1", "pr_aha2", "pr_aha3"...

########################################################################
# HELPER FUNCTIONS
########################################################################

# Commands for showing messages on buildkite run page.
finalmsg=""
function setstate { buildkite-agent meta-data set "$1" --job "$BUILDKITE_JOB_ID" "$2"; }
function getstate { buildkite-agent meta-data get "$1" --job "$BUILDKITE_JOB_ID"; }
function bkmsg { buildkite-agent annotate --context foo --append "$1<br />"; }
function bkclr {
    finalmsg="$(date +%H:%M) $finalmsg$1<br />"
    buildkite-agent annotate --context foo "$finalmsg"
}

# E.g. "key-exists regress1" fails if there is no step key "regress1" (yet)
function key-exists {
    buildkite-agent step get "label" --step "$1" --build "$BUILDKITE_BUILD_ID" >& /dev/null;
}

########################################################################
# MAIN
########################################################################

# Pop next step off arg list e.g. args=(build gold 1 2 3 4 5 6 7 8 9)
# => next="build", args=(gold 1 2 3 4 5 6 7 8 9)
next="$1"; if ! [ "$next" ]; then echo DONE; exit; fi
shift
# bkmsg "Processing arg next='$next'"

#------------------------------------------------------------------------------
if [ "$next" == "--cleanup" ]; then
    echo '+++ Step outcomes'

    # Cleanup step summarizes outcomes of all previous steps
    # and sends final status to any waiting PRs

    # Set FAIL if indicated step failed
    FAIL=; function cleanup {
        echo "$1": "$(buildkite-agent step get outcome --step "$2")"
        echo "$1": "$(buildkite-agent step get outcome --step "$2")"
        [ "$(buildkite-agent step get outcome --step "$2")" == "passed" ] || FAIL=True
    }

    # For each step indicated in command line, check that step for failure
    for step in "$@"; do
        if [ "$step" == "build" ]; then
            cleanup 'khaki prep' kprep
            cleanup 'r8cad prep' r8prep

        elif [ "$step" == "gold" ]; then
            cleanup 'Zircon Gold' zircon_gold

        else
            # Only remaining choice is that step is a single digit 0-9
            [ "$step" == 0 ] && label="Fast" || label="Regress $i"
            [ "$CONFIG" == "full" ] && label="Full Regressions"
            cleanup "$label" regress"$step"
        fi
    done
    echo "-- FAIL=$FAIL"

    # Note, /home/buildkite-agent/bin/status-update must exist on agent machine
    # Also see ~steveri/bin/status-update on kiwi
    echo '- Send summary outcome "success" or "failure" to github PR'
    if [ "$FAIL" ]; then
        ~/bin/status-update --force failure
    else
        ~/bin/status-update --force success
    fi
    echo '- Clean up your mess'

#------------------------------------------------------------------------------
elif [ "$next" == "build" ]; then

    # FIXME this launches two build steps at the same time; the
    # possibility exists that both call regression-steps.sh at same time.
    # That would be trouble for our new chaining approach, yes?
    # Need flock? something simpler/smarter?

    # Early-out if these steps have already been launched!
    if key-exists 'kprep'; then
        if key-exists 'r8prep'; then
            echo "Steps 'kprep' and 'r8prep' already exist in pipeline. So. Nothing to do!"; exit 0
        fi
    fi

    # Build the two individual build steps, one for each agent :)
    bdkhaki=$(
  cat << '    EOF' | sed 's/^    //' | sed "s/ARGS/$*/"
    - label: "khaki prep"
      key: "kprep"
      agents: { hostname: khaki }
      # Launch next step if/when build is complete
      command: .buildkite/bin/regression-steps.sh ARGS
      plugins:
        - uber-workflow/run-without-clone:
        - improbable-eng/metahook:
            pre-command: $BUILD_DOCKER
    EOF
)
    bdcad=$(
  cat << '    EOF' | sed 's/^    //' | sed "s/ARGS/$*/"
    - label: "r8cad prep"
      key: "r8prep"
      agents: { hostname: r8cad-docker }
      # Launch next step if/when build is complete
      command: .buildkite/bin/regression-steps.sh ARGS
      plugins:
        - uber-workflow/run-without-clone:
        - improbable-eng/metahook:
            pre-command: $BUILD_DOCKER
    EOF
)
    # Package the two steps into one bundle, then upload the bundle
    buildsteps=$(
      sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d' "$0"  # Preamble from below
      echo "steps:"
      key-exists 'kprep'  || echo "$bdkhaki"
      key-exists 'r8prep' || echo "$bdcad"  # FIXME restore before final check-in
    )
    echo "$buildsteps" | buildkite-agent pipeline upload

#------------------------------------------------------------------------------
elif [ "$next" == "gold" ]; then

    # Upload gold step, wait for it to start running (i.e. "launch")

    # This is one way how you can skip a step for e.g. debugging
    # exec "$0" "$@"  # FIXME Skip gold for now FIXME restore before final check-in

    # Early-out if step has already been launched!
    key='zircon_gold'; if key-exists $key; then
        echo "Step '$key' already exists in pipeline. So. Nothing to do!"; exit 0
    fi
    goldstep=$(
  sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d' "$0"  # Preamble from below
  cat << '    EOF' | sed 's/^    //' | sed "s/ARGS/$*/"
    steps:
    - label: "Zircon Gold"
      key: "zircon_gold"
      command: |
        if ! $REGRESS_METAHOOKS --exec '/aha/.buildkite/bin/rtl-goldcheck.sh zircon'; then
            msg="Zircon gold check FAILED. We don't want to touch Zircon RTL for now."
            echo "--- $$msg"
            echo "$$msg" | buildkite-agent annotate --style "error" --context onyx
            exit 13
        else echo "--- $$msg Zircon gold check PASSED"
        fi
        .buildkite/bin/regression-steps.sh ARGS  # Chain to next step
      plugins:
        - uber-workflow/run-without-clone:
        - improbable-eng/metahook:
            pre-command: $BUILD_DOCKER cd . ; $REGRESS_METAHOOKS --pre-command
    EOF
)
# setstate launch-state READY  # FIXME do we use this??
echo "$goldstep" | buildkite-agent pipeline upload


# BOOKMARK
#------------------------------------------------------------------------------
else
    # "$next" must be "build", "gold" or a single digit 0-9
    # Since we already processed "build and "gold" above, that leaves 0-9
    i=$next  # Should be one of {0,1,2,3,4,5,6,7,8,9}

    # Early-out if step has already been launched!
    key="regress$i"; if key-exists "$key"; then
        echo "Step '$key' already exists in pipeline. So. Nothing to do!"; exit 0
    fi

    # Fairness algorithm (CONCURRENCY=4) means at most four regression steps can run at a time
CONCURRENCY="
  concurrency: $MAX_AGENTS  # Limit long-running jobs to at most <MAX> at a time.
  concurrency_group: "aha-flow-${BUILDKITE_BUILD_ID}"
"
    # Launch next step
    # Each new step uploads only after previous step has started running.
    [ "$i" == 0 ] && label="Fast" || label="Regress $i"
    [ "$CONFIG" == "full" ] && label="Full Regressions"

    # setstate launch-state READY
    # bkmsg "$label READY TO LAUNCH"

    (sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d' "$0"
    cat <<EOF | sed 's/^    //' | sed "s/ARGS/$*/"
    steps:
    - label: "$label"
      # agents: { hostname: khaki }  # Can uncomment for debugging etc.
      key: "regress$i"
      env: { REGRESSION_STEP: $i }
      command: |
        .buildkite/bin/regression-steps.sh ARGS  # Chain to next step
        CONFIG=$CONFIG \$REGRESS_METAHOOKS --commands
      plugins:
        - uber-workflow/run-without-clone:
        - improbable-eng/metahook:
            pre-command: |
                RSTEP=$i
                \$BUILD_DOCKER
                cd .
                \$REGRESS_METAHOOKS --pre-command
            pre-exit: |
                \$REGRESS_METAHOOKS --pre-exit
EOF
    [ "$i" != 0 ] && echo "$CONCURRENCY"
    echo "") | buildkite-agent pipeline upload
fi

#------------------------------------------------------------------------------
exit

#------------------------------------------------------------------------------
#BEGIN preamble
# env:
#   # This script allows retries even after original collateral is gone...
#   BUILD_DOCKER: |
#     set +u  # Cannot do [ "$VAR" ] if this is not set :(
#     echo "--- Build docker image $IMAGE if not exists yet"
# 
#     # To test retry: FAIL first time through only
#     # if [ "$$BUILDKITE_RETRY_COUNT" == "0" ]; then echo '--- FAIL b/c retry count is 0'; exit 13; fi
# 
#     # Submod PRs use DEV branch (usually "master")
#     [ "$$AHA_SUBMOD_FLOW_COMMIT" ] && tbranch=$DEV_BRANCH || tbranch=$BUILDKITE_BRANCH
#     remote=https://raw.githubusercontent.com/StanfordAHA/aha/$$tbranch
# 
#     # In case of retry, may need to (re)download metahooks script
#     # if ! test -f $REGRESS_METAHOOKS; then
#     if [ 1 ]; then
#         mkdir -p $COMMON  # Make sure there is a landing pad for the downloaded file
#         echo curl $$remote/.buildkite/bin/regress-metahooks.sh -o $REGRESS_METAHOOKS
#         curl $$remote/.buildkite/bin/regress-metahooks.sh -o $REGRESS_METAHOOKS
#         chmod +x $REGRESS_METAHOOKS
#         curl $$remote/.buildkite/bin/regression-steps.sh -o .buildkite/bin/regression-steps.sh
#         chmod +x .buildkite/bin/regression-steps.sh
#     fi
# 
#     # If docker image is gone, e.g. in case of retry maybe, we'll have to rebuild it
#     (
#         # "flock" exclusionary zone ensures that only one guy builds the new image
#         lockfile=aha-flow-lock-$BUILDKITE_BUILD_NUMBER
#         i=0; while ! flock -n 9; do
#             [ "$$i" -eq  0 ] && echo "Someone appears to be currently (re)building docker image"
#             echo "Waited $$((i++)) minutes..."
#             sleep 60
#             [ "$$i" -gt 99 ] && echo "Giving up" && exit 13
#         done
# 
#         echo "# We have the lock; look for $IMAGE"
#         if ! [ `docker images -q $IMAGE` ]; then
#             echo "+++ CANNOT FIND DOCKER IMAGE '$IMAGE'"
#             echo "And I have the lock so...guess I am the one who will be (re)building it"
# 
#             # Change step label to reflect docker build DB
#             buildkite-agent step update "label" " + DB($(hostname))" --append
# 
#             # Remove docker images older than one day
#             echo "--- Cleanup old docker images"
#             docker image ls | awk '/(days|weeks|months) ago/ {print}' || echo okay
#             docker image ls | awk '/(days|weeks|months) ago/ {print $$3}' | xargs docker image rm || echo okay
# 
#             # Remove DELETEME* dirs older than one week
#             # FIXME pretty sure this is BROKEN
#             echo "--- Cleanup old common areas"
#             find /var/lib/buildkite-agent/builds/DELETEME* -type d -mtime +7 -exec /bin/rm -rf {} \; || echo okay
# 
#             echo "--- Save repo things in common area"
#             mkdir -p $$COMMON
#             cp $$BUILDKITE_BUILD_CHECKOUT_PATH/.buildkite/bin/regress-metahooks.sh $$COMMON
#            
#             echo "--- DEBUG DOCKER TRASH"
#             docker images; docker ps;
# 
#             # For dev purposes...can skip docker build e.g. to work on retry mechanism
#             # - echo "--- SKIP REST OF DOCKER BUILD for dev purposes only"; exit
# 
#             # What does this doohickey do?
#             echo "# Set REQUEST_TYPE for custom checkout"
#             echo curl $$remote/.buildkite/bin/custom-checkout.sh -o custom-checkout.sh
#             curl $$remote/.buildkite/bin/set-trigfrom-and-reqtype.sh -o set-trigfrom-and-reqtype.sh
#             source set-trigfrom-and-reqtype.sh
#             
#             echo "# Download and source custom-checkout script to get latest repo"
#             echo curl $$remote/.buildkite/bin/custom-checkout.sh -o custom-checkout.sh
#             curl $$remote/.buildkite/bin/custom-checkout.sh -o custom-checkout.sh
#             source custom-checkout.sh
# 
#             echo "--- Remove 700MB of clockwork, halide metadata"
#             dotgit=.git/modules/clockwork;          du -shx $$dotgit; /bin/rm -rf $$dotgit
#             dotgit=.git/modules/Halide-to-Hardware; du -shx $$dotgit; /bin/rm -rf $$dotgit
# 
#             echo "--- (Re)create garnet Image"
#             ~/bin/buildkite-docker-build --progress plain . -t "$IMAGE"
# 
#             echo "--- Pruning Docker Images"
#             yes | docker image prune -a --filter "until=6h" --filter=label='description=garnet' || true
#         else
#             echo Docker image exists, hooray
#         fi
#     ) 9>/tmp/aha-flow-lock-$BUILDKITE_BUILD_NUMBER
#     # echo I am in dir `pwd`  # builds/<agent>/stanford-aha/aha-flow
#     # cd .  # Got weird error without this...??
#     # set -x; $REGRESS_METAHOOKS --pre-command
# 
#     function setstate { buildkite-agent meta-data set $$1 --job $BUILDKITE_JOB_ID $$2; }
#     function bkmsg    { buildkite-agent annotate --context foo --append "$$1<br />"; }
# 
#     setstate image-exists TRUE
#     setstate launch-state LAUNCHED
#     # bkmsg "BD: $$BUILDKITE_LABEL LAUNCHED"
# 
#END preamble
