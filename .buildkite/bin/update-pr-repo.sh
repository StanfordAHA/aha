#!/bin/bash
# This script is designed to be SOURCED, obviously :)
set +u

echo "+++ BEGIN update-pr-repo.sh"
cd $BUILDKITE_BUILD_CHECKOUT_PATH    # Just in case, I dunno, whatevs.

# (Re)set env var BUILDKITE_PULL_REQUEST_REPO according to whether build
# was triggered from a pull request. An actual pull request will set
# BUILDKITE_PULL_REQUEST_REPO correctly, but a rebuild of the same job may
# not. Can use build message "PR from <submod>" to find correct value.
# E.g. BUILDKITE_PULL_REQUEST_REPO='https://github.com/StanfordAHA/garnet.git'

# Also need to rediscover pull number BUILDKITE_PULL_REQUEST

# This script is sourced only from pipeline.yml
# and only when AHA_SUBMOD_FLOW_COMMIT exists i.e.:
# [ "$$AHA_SUBMOD_FLOW_COMMIT" ] && source $$bin/update-pr-repo.sh

echo "- Reset BUILDKITE_COMMIT according to env var set by aha-submod-flow steps :("
echo "- https://buildkite.com/stanford-aha/aha-submod-flow/settings/steps"
[ "$AHA_SUBMOD_FLOW_COMMIT" ] && BUILDKITE_COMMIT=$AHA_SUBMOD_FLOW_COMMIT || echo okay

if [ "$BUILDKITE_PULL_REQUEST_REPO" ]; then
    echo "- BUILDKITE_PULL_REQUEST_REPO already set, to '$BUILDKITE_PULL_REQUEST_REPO'"
    echo "- Nothing to do, returning to main script."

elif expr "$BUILDKITE_MESSAGE" : "PR from " > /dev/null; then

    # ?? does this ever happen? FIXME/TODO maybe scrub the logs and see.

    echo "- OMG it's a retry of a pull request build"
    echo "- Must recover BUILDKITE_PULL_REQUEST_REPO, BUILDKITE_PULL_REQUEST"

    # Need "exit" in awk script in case commit message has embedded linefeeds :(
    echo '- Extract submod name from PR message e.g. "Pull from lake"'
    submod=`echo "$BUILDKITE_MESSAGE" | awk '{print $3;exit}'`  # E.g. "lake"
    echo "- Found submod '$submod'"

    echo '- Find full path of submod e.g. "https://github.com/stanfordaha/canal"'
    if [ "$submod" == "aha" ]; then
        u="https://github.com/stanfordaha/aha"
        echo '- Oops haha not a submod, this is the aha parent repo'

    elif ! u=`git config --file .gitmodules --get submodule.${submod}.url`; then
        echo "- ERROR cannot find path for submodule '$submod'"
        echo "- Could not (re)set BUILDKITE_PULL_REQUEST_REPO, BUILDKITE_PULL_REQUEST"
        return
    fi
    BUILDKITE_PULL_REQUEST_REPO="$u"
    echo "- Found BUILDKITE_PULL_REQUEST_REPO '$u'"

    # OMG also need to reconstruct the NUMBER of the pull request.
    # Can find it by searching PR's for the appropriate commit SHA

    # Use BUILDKITE_COMMIT to find and set pull request number BUILDKITE_PULL_REQUEST
    echo "- Find pull request corresponding to BUILDKITE_COMMIT $BUILDKITE_COMMIT"

    # Find user_repo combo e.g. "stanfordaha/canal"
    user_repo=`echo $BUILDKITE_PULL_REQUEST_REPO | sed 's/http.*github.com.//'`

    awkscript='
      $1 == "url:" { url=$NF }
      $1 == "head:" { head=1 }
      /'$BUILDKITE_COMMIT'/ { if (head==1) { print url; exit }}'

    # API call gets PR info, awk script extracts desired url.
    url_pr=`curl --location --silent \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/${user_repo}/pulls?state=all" \
      | egrep '"url.*pull|"head|"base|"sha' \
      | tr -d '",' | awk "$awkscript"`

    # E.g. url_pr="https://api.github.com/repos/StanfordAHA/lake/pulls/166"
    echo "- Found url_pr=$url_pr"
    BUILDKITE_PULL_REQUEST=`echo $url_pr | awk -F '/' '{print $NF}'`
    echo Found BUILDKITE_PULL_REQUEST=$BUILDKITE_PULL_REQUEST

    # Squirrel away the info for later use
    temp=/var/lib/buildkite-agent/builds/DELETEME
    mkdir -p $temp
    env=$temp/env-$BUILDKITE_BUILD_NUMBER
    echo BUILDKITE_PULL_REQUEST=$BUILDKITE_PULL_REQUEST > $env
    echo BUILDKITE_PULL_REQUEST_REPO=$BUILDKITE_PULL_REQUEST_REPO >> $env
fi
echo "--- END update-pr-repo.sh"
