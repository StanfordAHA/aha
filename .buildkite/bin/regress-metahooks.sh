#!/bin/bash

# This is where we offload meta-hook commands for pipeline.yml
# These commands run OUTSIDE the docker container, that's why we use meta-hooks.

if [ "$1" == '--pre-command' ]; then
    echo "+++ OIT PRE COMMAND HOOK BEGIN"

    # Use temp/.TEST to pass fail/success info into and out of docker container
    echo Renewing `pwd`/temp/.TEST
    mkdir -p temp; rm -rf temp/.TEST; touch temp/.TEST

    # If trigger came from a submod repo, we will do "pr" regressions.
    # Otherwise, trigger came from aha repo push/pull and we just do "daily" regressions.
    # We use "env" file to pass information between steps.
    # THIS ASSUMES THAT ALL STEPS RUN ON SAME HOST MACHINE and thus see the same commdir!

    # env file sets REQUEST_TYPE to one of "AHA_PUSH", "AHA_PR", or "SUBMOD_PR"
    # also sets "PR_TAIL_REPO" to requesting submod e.g. "garnet"
    set -x; cat /var/lib/buildkite-agent/builds/DELETEME/env-$BUILDKITE_BUILD_NUMBER; set +x
    source /var/lib/buildkite-agent/builds/DELETEME/env-$BUILDKITE_BUILD_NUMBER

    echo "--- Pass DO_PR info to docker"
    echo "Info gets passed to docker by mounting temp dir as /buildkite omg omg"
    if [ "$REQUEST_TYPE" == "SUBMOD_PR" ]; then
        echo "+++ SET DO_PR"; mkdir -p temp; touch temp/DO_PR
        if [ "$PR_REPO_TAIL" == "garnet" ]; then
            # Delete .TEST as a sign to skip tests
            echo "+++ Garnet PR detected, so skip redundant regressions"
            rm -rf temp/.TEST
        fi
    else
        echo "+++ UNSET DO_PR"; /bin/rm -rf temp/DO_PR
    fi
    test -e temp/DO_PR && echo FOO temp/DO_PR exists || echo FOO temp/DO_PR not exists

    echo "--- OIT PRE COMMAND HOOK END"

elif [ "$1" == '--commands' ]; then

    # These commands run INSIDE the docker container
    # Also need to be sourced maybe?
    # So maybe do something like...?
    #    $0 --commands > tmp; source tmp

    cat <<'EOF' | sed "s/--BENCHMARK--/$2/" # Single-quotes prevent var expansion etc.

    echo $foo `echo bar`
    if ! test -e /buildkite/.TEST; then
        echo "+++ No .TEST detected, so skip redundant regressions"
        exit
    fi
    test -e /buildkite/DO_PR && echo "--- DO_PR SET (TRUE)"
    test -e /buildkite/DO_PR || echo "--- DO_PR UNSET (FALSE)"

    source /aha/bin/activate
    source /cad/modules/tcl/init/sh
    module load base incisive xcelium/19.03.003 vcs/T-2022.06-SP2

    # make /bin/sh symlink to bash instead of dash:
    echo "dash dash/sh boolean false" | debconf-set-selections
    DEBIAN_FRONTEND=noninteractive dpkg-reconfigure dash

    # Istall time (what? why?)
    apt update
    apt install time

    echo    "--- PIP FREEZE"; pip freeze  # ??? okay ???
    echo -n "--- GARNET VERSION "; (cd garnet && git rev-parse --verify HEAD)

    # Prepare to run regression tests according to whether it's a submod PR
    if test -e /buildkite/DO_PR; then
      echo "Trigger came from submod repo pull request; use pr config"; export CONFIG=pr;
    else
      echo "Trigger came from aha repo; use default config"; fi

    aha regress --BENCHMARK--  # Magic happens here...

    # Cleanup
    # Okay to remove or check but DO NOT CREATE anything in /buildkite, it is owned by root :(
    echo "--- Removing Failure Canary"; rm -rf /buildkite/.TEST
EOF


elif [ "$1" == '--pre-exit' ]; then

    echo "+++ CHECKING EXIT STATUS"; set -x
    echo "Send status to github."
    cd $BUILDKITE_BUILD_CHECKOUT_PATH

    # Docker will have removed temp/.TEST if all the tests passed
    if [ "$BUILDKITE_COMMAND_EXIT_STATUS" == 0 ]; then
        test -f temp/.TEST && export BUILDKITE_COMMAND_EXIT_STATUS=13
    fi
    /bin/rm -rf temp

    # FIXME
    # OMG! OH no you di'nt! ~/bin??? what are you THINKING
    # Looks like ~/bin devolves to e.g. /var/lib/buildkite-agent/bin

    # status-update will magically override "success" with "failure" as appropriate!
    # (Based on BUILDKITE_COMMAND_EXIT_STATUS and BUILDKITE_LAST_HOOK_EXIT_STATUS)
    ~/bin/status-update success

fi

