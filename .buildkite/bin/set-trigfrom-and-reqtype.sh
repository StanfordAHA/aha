#!/bin/bash

# What does this script do?
# 1. If build was triggered by a pull request, annotate build with
#    links pointing to pull request on github.
# 2. Set REQUEST_TYPE to one of "AHA_PUSH", "AHA_PR", or "SUBMOD_PR"
# 3. Set PR_REPO_TAIL to submod associated with the PR, e.g. "canal"
# 4. Add REQUEST_TYPE env temp file for use by later steps

PS4="."   # Prevents "+++" prefix during 3-deep "set -x" execution

echo "+++ set-trigfrom-and-reqtype.sh BEGIN"
cd $BUILDKITE_BUILD_CHECKOUT_PATH    # Just in case, I dunno, whatevs.

echo "--- BEGIN TRIGGERED-FROM LINKS"

# If pull request, show where request came from.
# And set e.g. PR_REPO_TAIL="lake"
PR_REPO_TAIL=
if [ "$BUILDKITE_PULL_REQUEST_REPO" ]; then
    # BUILDKITE_PULL_REQUEST_REPO="https://github.com/StanfordAHA/lake.git"
    # BUILDKITE_PULL_REQUEST="166"
    # BUILDKITE_COMMIT=7c5e88021a01fef1a04ea56b570563cae2050b1f

    # E.g. repo="https://github.com/StanfordAHA/lake"
    repo=`echo "$BUILDKITE_PULL_REQUEST_REPO" | sed 's/.git$//'`
    r=`echo "$repo" | sed 's/http.*github.com.//'`               # "StanfordAHA/lake"
    PR_REPO_TAIL=`echo "$repo" | sed "s,http.*github.com/.*/,,"` # "lake"
    echo "Found PR from submod '$PR_REPO_TAIL'"

    if [ "$BUILDKITE_COMMIT" == "HEAD" ]; then
    cat <<EOF | buildkite-agent annotate --style "info" --context foo3
### Triggered from garnet push, whaddaya want from me
EOF

    else
    # E.g. url_cm="https://github.com/StanfordAHA/lake/commit/7c5...0b1f"
    first7=`expr "$BUILDKITE_COMMIT" : '\(.......\)'`  # 7c5e880
    url_cm=${repo}/commit/${BUILDKITE_COMMIT}  # https://...lake/commit/7c5e88077998899...
    mdlink_cm="[${first7}](${url_cm})"         # [7c5e880](https://...lake/commit/7c5e88077998899...)

    # E.g. url_pr="https://github.com/StanfordAHA/lake/pull/166"
    url_pr=${repo}/pull/${BUILDKITE_PULL_REQUEST}
    mdlink_pr="[Pull Request #${BUILDKITE_PULL_REQUEST}](${url_pr})"

    # E.g. "Triggered from StanfordAHA/canal ca602ef (Pull Request #58)"
    cat <<EOF | buildkite-agent annotate --style "info" --context foo3
### Triggered from ${r} ${mdlink_cm} (${mdlink_pr})
EOF
    fi
fi
echo "--- END TRIGGERED-FROM LINKS"

case "$PR_REPO_TAIL" in
    "aha") REQUEST_TYPE="AHA_PR"    ;;
    "")    REQUEST_TYPE="AHA_PUSH"  ;;
    *)     REQUEST_TYPE="SUBMOD_PR" ;;
esac
echo "--- FOUND REQUEST_TYPE '$REQUEST_TYPE'"

# Squirrel away the info for later use
temp=/var/lib/buildkite-agent/builds/DELETEME; mkdir -p $temp
env=$temp/env-$BUILDKITE_BUILD_NUMBER
echo REQUEST_TYPE=${REQUEST_TYPE} >> $env
echo PR_REPO_TAIL=${PR_REPO_TAIL} >> $env
set -x; cat $env; set +x

echo "+++ set-trigfrom-and-reqtype.sh END"
