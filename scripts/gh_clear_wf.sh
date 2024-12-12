#!/bin/sh
ORG=""
REPO=""

gh api repos/$ORG/$REPO/actions/runs --paginate -q '.workflow_runs[].id' \
| xargs -I {} gh api repos/$ORG/$REPO/actions/runs/{} -X DELETE

