#!/bin/bash

# This is where we offload meta-hook commands for pipeline.yml
# Note these commands are designed to run INSIDE a docker container

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
fi

