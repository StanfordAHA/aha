AHA-FLOW CI

------------------------------------------------------------------------
HOW IT WORKS

- Push- and pull- events from aha submodule repos trigger the
  buildkite `aha-submod-flow` pipeline.

- `Aha-submod-flow` pipeline settings include a filter that only lets
  pull requests go through. If the filter is satisfied, the pipeline
  uploads `pr_trigger.yml`, which triggers the `aha-flow` pipeline.

- The `aha-flow` pipeline uploads `pipeline.yml`, which runs PR regressions
  and reports status back to the original github pull request page.

------------------------------------------------------------------------
THE PLAYERS

  aha-submod-flow-steps.yml
    A copy of the aha-submod-flow pipeline steps at
    https://buildkite.com/stanford-aha/aha-submod-flow/settings/steps

  aha-flow-steps.yml
    A copy of the aha-flow pipeline steps at
    https://buildkite.com/stanford-aha/aha-submod-flow/settings/steps

  pr_trigger.yml
    "aha-submod-flow" pipeline uses this to trigger aha-flow pipeline when
    it gets a pull request from an aha submodule repo

  pipeline.yml
    "aha-flow" pipeline uses this to run aha regression tests
    
  bin/status-update
    A copy of the script used to update github commit statuses, with
    secrets redacted. The script must live on the buildkite agent
    machine in the agent's home directory, e.g.
    `r7cad-docker:/var/lib/buildkite-agent/bin/status-update`

  bin/custom-checkout.sh
    Script sourced by pipeline.yml; clones aha repo and uses info
    gleaned from `update-pr-repo.sh` (see below) to update
    pull-requesting submodule.

  bin/update-pr-repo.sh
    Script sourced by pipeline.yml; detects whether build was
    triggered by a submodule pull request and, if so, derives all
    necessary information to test its specific branch commit.

------------------------------------------------------------------------
DEPRECATED PLAYERS

  hooks/post-checkout
  hooks/pre-exit
    These hooks were used by heroku to detect and report test success or failure.

------------------------------------------------------------------------
SETUP

foreach aha submodule e.g.
  stanfordaha/lake
  stanfordaha/canal
  stanfordaha/garnet
  stanfordaha/lassen
  stanfordaha/gemstone
  stanfordaha/Halide-to-Hardware
  leonardt/pycoreir
  leonardt/hwtypes
  leonardt/fault
  leonardt/ast_tools
  kuree/archipelago
  cdonovick/peak
do:
    Navigate to https://github.com/${submodule}/settings/hooks
    => add webhook

    Payload URL:
    https://webhook.buildkite.com/deliver/55a73...

    Content type: application/json

    Enable SSL verification

    Let me select individual events
        * Deployments
        * Pull requests
        * Pushes
        ---
        * Active

    Add webhook

Then: for each repo or organization, must provide bin/status-update
with a personal access token for the repo with "report commit status"
permissions; see bin/status-update code for more info.


========================================================================
NOTES

---
PROBLEM: Github thinks that PR retry events are "push" events, so even
when submodule repos are set up to send only PR events, PR-retries do
not activate buildkite webhook (no payload gets sent to buildkite).

SOLUTION: Let submod repo send both pull and push events to
buildkite. Use buildkite "github settings" to reject non-retry push
events using a magic filter that builds only when
'build.pull_request.base_branch == "master"'

---
PROBLEM: Using the solution above, builds no longer trigger for
aha-repo push events.

SOLUTION: Make a separate buildkite pipeline 'aha-submod-flow' that
has the magic filter, and whose only purpose is to trigger 'aha-flow'
when the filter succeeds. Aha repo gets "aha-flow" webhook, submod
repos get "aha-submod-flow" webhook.

---
PROBLEM: Buildkite default setup tries to clone aha repo using commit
hash sent by github, fails.

SOLUTION: Use buildkite plugin to turn off default setup behavior.
