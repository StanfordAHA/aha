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
# cat $0 | sed '/BEGIN preamble/,/END preamble/s/^# //'
cat $0 | sed '1,/^#BEGIN preamble/d;s/^# //g;/^#END preamble/,$d'
# exit

echo "steps:"

# Use same agent as whoever called us I guess?
# $BUILDKITE_AGENT_META_DATA_HOSTNAME
# agents: { hostname: $BUILDKITE_AGENT_META_DATA_HOSTNAME }

dont="don't"
cat <<'EOF' > /dev/null
- label: "Docker for gold test"
  agents: { hostname: $BUILDKITE_AGENT_META_DATA_HOSTNAME }
  command: echo DONE
  plugins:
    - uber-workflow/run-without-clone:
    - improbable-eng/metahook:
        pre-command: $BUILD_DOCKER

- wait: ~

- label: "Zircon Gold"
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
        msg="Zircon gold check FAILED. We '$dont' want to touch Zircon RTL for now."
        echo "++ $$msg"
        echo "$$msg" | buildkite-agent annotate --style "error" --context onyx
        exit 13
    fi

- wait: ~
EOF

for i in `seq 0 $NSTEPS`; do
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
#     echo "--- Build docker image $IMAGE if not exists yet"
# 
#     # To test retry: FAIL first time through only
#     # if [ "$$BUILDKITE_RETRY_COUNT" == "0" ]; then echo '--- FAIL b/c retry count is 0'; exit 13; fi
# 
#     remote=https://raw.githubusercontent.com/StanfordAHA/aha/$BUILDKITE_BRANCH
# 
#     # In case of retry, may need to (re)download metahooks script
#     if ! test -f $REGRESS_METAHOOKS; then
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
#             echo "# Download and source custom-checkout script to get latest repo"
#             echo curl $$remote/.buildkite/bin/custom-checkout.sh -o custom-checkout.sh
#             curl $$remote/.buildkite/bin/custom-checkout.sh -o custom-checkout.sh
#             source custom-checkout.sh
# 
#             echo "--- (Re)creating garnet Image"
#             docker build --progress plain . -t "$IMAGE"
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
