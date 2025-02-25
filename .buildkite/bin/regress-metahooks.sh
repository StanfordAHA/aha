#!/bin/bash

# This is where we offload meta-hook commands for pipeline.yml
# These commands run OUTSIDE the docker container, that's why we use meta-hooks.

if [ "$1" == '--pre-command' ]; then

    # This is designed to be invoked from pipeline.yml, which should provide
    # necessary env vars including CONTAINER/IMAGE/TAG/CONFIG/REGRESSION_STEP

    echo "--- OIT PRE COMMAND HOOK BEGIN"
    echo "Check for valid docker image"

    # In case of e.g. manual retry, original docker image may have been deleted already.
    # This new code below gives us the opportunity to revive the dead image when needed.
    if ! docker images | grep $TAG; then
        echo "OH NO cannot find docker image $IMAGE...I will rebuild it for you"

        # Should already be in valid BUILDKITE_BUILD_CHECKOUT_PATH with aha clone
        # E.g. pwd=/var/lib/buildkite-agent/builds/r7cad-docker-6/stanford-aha/aha-flow
        git clean -ffxdq
        bin=$BUILDKITE_BUILD_CHECKOUT_PATH/.buildkite/bin

        if [ "$AHA_SUBMOD_FLOW_COMMIT" ]; then
            echo 'Submod pull requests use master branch (sometimes overridden by DEV_BRANCH)'
            # (aha-flow steps is responsible for setting DEV_BRANCH)
            # (https://buildkite.com/stanford-aha/aha-flow/settings/steps)
            git checkout $DEV_BRANCH || echo no dev branch found, continuing with master

            # Make sure env var BUILDKITE_PULL_REQUEST_REPO is set correctly
            source $bin/update-pr-repo.sh
        else
            echo 'Aha push/PR uses pushed branch'
            git checkout $BUILDKITE_COMMIT
        fi

        # Checkout and update correct aha branch and submodules
        source $bin/custom-checkout.sh
        test -e .git/modules/sam/HEAD || echo OH NO HEAD not found

        echo "--- (Re)creating garnet Image"
        docker build --progress plain . -t "$IMAGE"
    fi

    echo "--- OIT PRE COMMAND HOOK CONTINUES..."
    # Use temp/.TEST to pass fail/success info into and out of docker container
    echo Renewing `pwd`/temp/.TEST
    mkdir -p temp; rm -rf temp/.TEST; touch temp/.TEST

    # If trigger came from a submod repo, we will do "pr" regressions.
    # Otherwise, trigger came from aha repo push/pull and we do (default) "aha_pr" regressions.
    # We use "env" file to pass information between steps.
    # THIS ASSUMES THAT ALL STEPS RUN ON SAME HOST MACHINE and thus see the same commdir!

    # env file sets REQUEST_TYPE to one of "AHA_PUSH", "AHA_PR", or "SUBMOD_PR"
    # also sets "PR_TAIL_REPO" to requesting submod e.g. "garnet"
    echo cat /var/lib/buildkite-agent/builds/DELETEME/env-$BUILDKITE_BUILD_NUMBER
    cat /var/lib/buildkite-agent/builds/DELETEME/env-$BUILDKITE_BUILD_NUMBER
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

    echo "--- BEGIN regress-metahooks.sh --commands"

    # This is designed to be invoked from pipeline.yml, which should provide
    # necessary env vars including CONTAINER/IMAGE/TAG/CONFIG/REGRESSION_STEP

    docker kill $CONTAINER || echo okay
    docker images; echo IMAGE=$IMAGE; echo TAG=$TAG
    docker run -id --name $CONTAINER --rm -v /cad:/cad -v ./temp:/buildkite:rw $IMAGE bash
    cat <<'EOF' > tmp$$  # Single-quotes prevent var expansion etc.

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

    # Install 'time' package (what? why?)
    apt update
    apt install time

    echo    "--- PIP FREEZE"; pip freeze  # ??? okay? why? ???
    echo    "+++ RUN REGRESSIONS"
    echo -n "Garnet version "; (cd garnet && git rev-parse --verify HEAD)

    # FIXME (below) this if-then-else jungle is awful; redo it!

    DO_AR=True

    # Prepare to run regression tests according to whether it's a submod PR
    if test -e /buildkite/DO_PR; then
      echo "Trigger came from submod repo pull request; use pr config"; export CONFIG=pr;
      if [ "$REGSTEP" == 2 -o "$REGSTEP" == 3 ]; then
        echo "oops no REGSTEP='$REGSTEP', not doing regressions"
        DO_AR=False
      fi

    elif [ "$CONFIG" == "pr_aha" ]; then

      # Normal
      [ "$REGSTEP" == 1 ] && export CONFIG=pr_aha1
      [ "$REGSTEP" == 2 ] && export CONFIG=pr_aha2
      [ "$REGSTEP" == 3 ] && export CONFIG=pr_aha3

      # Prototype
      # [ "$REGSTEP" == 1 ] && export CONFIG=fast
      # [ "$REGSTEP" == 2 ] && export CONFIG=fast
      # [ "$REGSTEP" == 3 ] && export CONFIG=fast

      echo "Trigger came from aha repo step '$REGSTEP'; use $CONFIG";

    else
      echo "Trigger came from OTHER, use default and/or config='$CONFIG'"
      if [ "$REGSTEP" == 2 -o "$REGSTEP" == 3 ]; then
        echo "oops no REGSTEP='$REGSTEP', not doing regressions"
        DO_AR=False
      fi
    fi

    if [ "$DO_AR" == "True" ]; then
      # aha regress --BENCHMARK-- --include-dense-only-tests || exit 13  # Magic happens here...
      # aha regress pr_aha1 --daemon auto --include-dense-only-tests || exit 13

      # For fast prototyping: ECHO ONLY and/or try config 'fast'
      if [ "$CONFIG" == "pr_aha3" ]; then 
        set -x
        echo "aha regress $CONFIG"
        aha regress $CONFIG --daemon auto --include-no-zircon-tests || exit 13
        set +x
      else
        set -x
        echo "aha regress $CONFIG"
        aha regress $CONFIG --daemon auto || exit 13
        set +x
      fi
    fi


    # Remove .TEST to signal that benchmark completed successfully
    # Okay to remove or check but DO NOT CREATE anything in /buildkite, it is owned by root :(
    echo "--- Removing Failure Canary"; rm -rf /buildkite/.TEST

EOF
    docker exec -e CONFIG=$CONFIG -e REGSTEP=$REGRESSION_STEP $CONTAINER /bin/bash -c "$(cat tmp$$)" || exit 13
    docker kill $CONTAINER; rm tmp$$  # Cleanup on aisle FOO
    echo "--- END regress-metahooks.sh --commands"

elif [ "$1" == '--pre-exit' ]; then

    echo "+++ [pre-exit] KILL CONTAINER $CONTAINER"
    set -x; docker kill $CONTAINER; set +x

    # Make sure we are in the right place to reference "temp" subdir
    cd $BUILDKITE_BUILD_CHECKOUT_PATH

    # Docker will have removed temp/.TEST if all the tests passed
    echo "+++ [pre-exit] CHECKING EXIT STATUS"
    if [ "$BUILDKITE_COMMAND_EXIT_STATUS" == 0 ]; then
        test -f temp/.TEST && export BUILDKITE_COMMAND_EXIT_STATUS=13
    fi
    /bin/rm -rf temp

fi

