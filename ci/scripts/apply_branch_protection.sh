#!/usr/bin/env bash
# WP-CICD-001 — apply ci/required_checks.json to GitHub branch protection.
# Requires an admin GitHub CLI session for the repository owner. Prints the
# request first; pass --apply to send it. Running it is a protected repository
# setting change: do it once the plan supports private-repo protection, then
# record the response under evidence/WP-CICD-001/.
set -euo pipefail
cd "$(dirname "$0")/../.."
config=ci/required_checks.json
repo=$(python3 -c "import json;print(json.load(open('$config'))['repository'])")
branch=$(python3 -c "import json;print(json.load(open('$config'))['branch'])")
payload=$(python3 - "$config" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
print(json.dumps({
    "required_status_checks": {"strict": c["strict"], "contexts": c["required_status_checks"]},
    "enforce_admins": c["enforce_admins"],
    "required_pull_request_reviews": {"required_approving_review_count": c["required_approving_review_count"]},
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
}, indent=2))
PY
)
echo "PUT repos/${repo}/branches/${branch}/protection"
echo "${payload}"
if [[ "${1:-}" != "--apply" ]]; then
  echo "Dry run only. Re-run with --apply to change GitHub settings."
  exit 0
fi
echo "${payload}" | gh api -X PUT "repos/${repo}/branches/${branch}/protection" --input -
gh api "repos/${repo}/branches/${branch}/protection/required_status_checks"
