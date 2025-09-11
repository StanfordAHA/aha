#!/bin/bash
# This is designed to be called from pipeline.yml

# Run "fast" app suite as regression step 0.
# Then run regression configs CONFIG=pr_aha1,2,3

# A typical step should look like this:
# 
#     - label: "Regress 1"
#       key: "regress"
#       env: { REGRESSION_STEP: 0 }
#       plugins:
#         - uber-workflow/run-without-clone:
#     
#         - improbable-eng/metahook:
#             pre-command: $BUILD_DOCKER
#             pre-exit:    $REGRESS_METAHOOKS --pre-exit
#     
#       command: $REGRESS_METAHOOKS --commands

########################################################################
# HELPER FUNCTIONS
########################################################################

finalmsg=""
function setstate { buildkite-agent meta-data set "$1" --job "$BUILDKITE_JOB_ID" "$2"; }
function getstate { buildkite-agent meta-data get "$1" --job "$BUILDKITE_JOB_ID"; }
function bkmsg { buildkite-agent annotate --context foo --append "$1<br />"; }
function bkclr {
    finalmsg="$(date +%H:%M) $finalmsg$1<br />"
    buildkite-agent annotate --context foo "$finalmsg"
}

# Wait for increasingly-longer times with each new invocation of this function
# To use:   "while !COND ; do gradwait; done"
function gradwait {
    # Note it will be BIG TROUBLE if you try and execute this in a subshell :(
    # FIXME can we invent a version that works in a subshell?
    sleepytime=0
    if [ "$1" == "--init" ]; then
        gwtotal="0 sec"
        tot1=0;  inc1=10; max1=60   # Check every 10 sec for one minute
        tot2=1;  inc2=1;  max2=20   # Check once per minute for twenty minutes
        tot3=20; inc3=5;  max3=600  # Every 5 min thereafter, max 6 hours I guess

    elif [ $tot1 -lt $max1 ]; then
        ((tot1+=inc1)); gwtotal="$tot1 sec"; sleepytime=$inc1
    elif [ $tot2 -lt $max2 ]; then
        ((tot2+=inc2)); gwtotal="$tot2 min"; sleepytime=$((60*inc2))
    elif [ $tot3 -lt $max3 ]; then
        ((tot3+=inc3)); gwtotal="$tot3 min"; sleepytime=$((60*inc3))
    fi
    # printf "sleep %3d" $sleepytime
    sleep $sleepytime
}

# After loading a step, invoke this function to wait for it to start running
# Example:
#    buildkite-agent pipeline upload step1.yml
#    wait-for-launch "step1"

function wait-for-launch {
    gradwait --init
    bkmsg "WAITING..."
    while [ "$(getstate launch-state)" != LAUNCHED ]; do
        gradwait; bkmsg "...$gwtotal..."  # E.g. "...10 sec..."
    done
    bkclr "'$1' launches after $gwtotal wait"
}

########################################################################
# MAIN
########################################################################

bdkhaki=$(
  cat << '    EOF' | sed 's/^    //'  # sed script to correct for indentation
    steps:
    - label: "khaki prep"
      key: "kprep"
      agents: { hostname: khaki }
      command: echo done
      plugins:
        - uber-workflow/run-without-clone:
        - improbable-eng/metahook:
            pre-command: $BUILD_DOCKER
    EOF
)
bdcad=$(
  cat << '    EOF' | sed 's/^    //'  # sed script to correct for indentation
    steps:
    - label: "r8cad prep"
      key: "r8prep"
      agents: { hostname: r8cad-docker }
      command: echo done
      plugins:
        - uber-workflow/run-without-clone:
        - improbable-eng/metahook:
            pre-command: $BUILD_DOCKER
    EOF
)
buildsteps=$(
  sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d' "$0"  # Preamble from below
  echo "$bdkhaki"
  # echo "$bdcad"  # FIXME restore before final check-in
)

# Launch image build step(s) and wait for at least one to complete
setstate image-exists FALSE
echo "$buildsteps" | buildkite-agent pipeline upload

# At completion of docker build, BUILD_DOCKER will set image-exists=TRUE
bkmsg "Waiting for at least one image build..."
gradwait --init; max1=0  # Skip the once-every-10-seconds phase
while [ "$(getstate image-exists)" != TRUE ]; do
    gradwait; bkmsg "...waited $gwtotal for image build..."
done
bkclr "Docker image exists on at least one agent machine"
bkclr "Took $gwtotal to build first image"

# Upload gold step, wait for it to start running (i.e. "launch")
goldstep=$(
sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d' "$0"  # Preamble from below
cat <<'EOF'
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
  plugins:
    - uber-workflow/run-without-clone:
    - improbable-eng/metahook:
        pre-command: $BUILD_DOCKER cd . ; $REGRESS_METAHOOKS --pre-command
EOF
)

# FIXME restore this before final check-in
# setstate launch-state READY
# echo "$goldstep" | buildkite-agent pipeline upload
# wait-for-launch "Zircon Gold"

# Fairness algorithm (CONCURRENCY=4) means at most four regression steps can run at a time
CONCURRENCY="
  concurrency: $MAX_AGENTS  # Limit long-running jobs to at most <MAX> at a time.
  concurrency_group: "aha-flow-${BUILDKITE_BUILD_ID}"
"
# Launch regression steps
# Each new step uploads only after previous step has started running.
# E.g. NSTEPS="0 1 2 3 4 5 6 7 8 9"
# NSTEPS="0 1 3 4 5"  # Trying to reproduce intermittent 'missing design.place' error e.g. Regress 3 on build 12067
NSTEPS="3 3 3 3 3 3"  # Trying to reproduce intermittent 'missing design.place' error e.g. Regress 3 on build 12067
NSTEPS=3  # Trying to reproduce intermittent 'missing design.place' error e.g. Regress 3 on build 12067
NSTEPS="0 1 3 4 5"  # Trying to reproduce intermittent 'missing design.place' error e.g. Regress 3 on build 12067
for i in $NSTEPS; do
for j in ""; do
    [ "$i" == 0 ] && label="Fast" || label="Regress $i"
    setstate launch-state READY
    bkmsg "$label READY TO LAUNCH"
    (sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d' "$0"
     cat <<EOF
steps:
- label: "$label$j"
  agents: { hostname: khaki }  # FIXME delete this after debugging is through...
  key: "regress$i$j"
  env: { REGRESSION_STEP: $i }
  command: |
      \$REGRESS_METAHOOKS --commands
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
    wait-for-launch "$label";
    bkmsg "Step '$label' be LAUNCHED"
done
done

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
#             buildkite-agent step update "label" " DB" --append
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
#             docker build --progress plain . -t "$IMAGE"
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
#     bkmsg "BD: $$BUILDKITE_LABEL LAUNCHED"
# 
#END preamble
