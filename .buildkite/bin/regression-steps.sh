#!/bin/bash
# This is designed to be called from pipeline.yml

# Run "fast" app suite as regression step 0.
# Then run regression configs CONFIG=pr_aha1,2,3..nsteps

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

# Preamble from below
cat $0 | sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d'

echo "steps:"

cat <<'EOF'
- label: "Docker for gold test"
  key: "docker_gold"
  # Gold test must run on same agent that builds its docker image
  agents: { hostname: $BUILDKITE_AGENT_META_DATA_HOSTNAME }
  command: echo DONE
  plugins:
    - uber-workflow/run-without-clone:
    - improbable-eng/metahook:
        pre-command: $BUILD_DOCKER

# - wait: ~

- label: "Zircon Gold"
  depends_on: "docker_gold"
  # Gold test must run on same agent that builds its docker image
  # FIXME but what if this step fails and we want to retry???
  agents: { hostname: $BUILDKITE_AGENT_META_DATA_HOSTNAME }
  key: "zircon_gold"
  plugins:
    - uber-workflow/run-without-clone:
    - docker#v3.2.0:
        image: garnet:aha-flow-build-${BUILDKITE_BUILD_NUMBER}
        volumes: ["/cad/:/cad"]
        shell:   ["/bin/bash", "-e", "-c"]
        mount-checkout: false
  commands: |
    echo "/aha/.buildkite/bin/rtl-goldcheck.sh zircon"
    if ! /aha/.buildkite/bin/rtl-goldcheck.sh zircon; then
        msg="Zircon gold check FAILED. We don't want to touch Zircon RTL for now."
        echo "++ $$msg"
        echo "$$msg" | buildkite-agent annotate --style "error" --context onyx
        exit 13
    fi

EOF

for i in `seq 0 $((NSTEPS-1))`; do
    [ "$i" == 0 ] && label="Fast" || label="Regress $i"
    cat <<EOF
- label: "$label"
  key: "regress$i"
  env: { REGRESSION_STEP: $i }
  command: \$REGRESS_METAHOOKS --commands
  plugins:
    - uber-workflow/run-without-clone:
    - improbable-eng/metahook:
        pre-command: \$BUILD_DOCKER cd . ; \$REGRESS_METAHOOKS --pre-command
        pre-exit:    \$REGRESS_METAHOOKS --pre-exit

EOF
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
# 
#END preamble
