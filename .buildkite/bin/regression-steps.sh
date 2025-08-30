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

echo "steps:"

# Agents must have tag hostname=<hostname>
# And then this will guarantee that all steps run on the same host, see?
agents: { hostname: $BUILDKITE_AGENT_META_DATA_HOSTNAME }

cat <<'EOF'
- label: "Zircon Gold"
  key: "zircon_gold"
  # Change this to true if want to make changes to zircon RTL
  skip: false
  soft_fail: false  # Failing gold check will fail pipeline.
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
        pre-command: \$REGRESS_METAHOOKS --pre-command
        pre-exit:    \$REGRESS_METAHOOKS --pre-exit

EOF
done
