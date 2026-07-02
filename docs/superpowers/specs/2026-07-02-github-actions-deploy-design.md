# GitHub Actions CI/CD Deploy — Design

## Context

Deployment today is fully manual:

```
ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -o 'IdentitiesOnly yes' -p 22 admin@52.59.170.52
sudo su
cd ~/app/portal/
git pull
bash deploy/remote_run.sh
```

`deploy/remote_run.sh` builds the Docker images, runs `collectstatic`, and brings the stack up (`docker compose up -d`). It does not run migrations automatically — those are applied manually via `manage.py migrate` when needed, and are out of scope here.

The repo currently has two remotes: `origin` (Bitbucket, where PRs have historically merged — see the "Merged in ... (pull request #36)" commit message format) and `github`. **The team is moving the PR/merge workflow to GitHub going forward**, so `master` on GitHub becomes the source of truth for what gets deployed.

Goal: when a PR merges into `master` on GitHub, automatically deploy to the single production server, reproducing the manual steps above.

## Scope

- Deploy-only automation. No test/lint gate (there's no meaningful test suite yet — see `federation/tests.py`), no manual-approval gate.
- Out of scope: CI for the Bitbucket repo, running `migrate` automatically, Slack/email notifications beyond GitHub's default failure emails.

## Design

### Trigger

- `on: push: branches: [master]` — a merged PR results in a push to `master`, which fires the workflow.
- `on: workflow_dispatch` — allows a manual re-run from the GitHub Actions UI without needing a new commit.
- `concurrency: group: deploy, cancel-in-progress: false` — if two merges land close together, the second deploy run queues behind the first instead of racing it on the server.

Branch protection on `master` (requiring PR review before merge) is a recommended GitHub repo setting to keep the "push to master = merged PR" assumption true, but is a repo-settings change, not part of the workflow file.

### Workflow file: `.github/workflows/deploy.yml`

Single job (`runs-on: ubuntu-latest`), one step using `appleboy/ssh-action` (or equivalent) that SSHes into the server and runs:

```bash
cd ~/app/portal && git pull && sudo bash deploy/remote_run.sh
```

This is a direct translation of the manual process — no changes to `remote_run.sh` itself.

### GitHub repo secrets

Stored under Settings → Secrets and variables → Actions:

- `DEPLOY_SSH_KEY` — private key for a **new, dedicated deploy keypair** (not the personal `thatsit-keypair1.pem`), so it can be rotated/revoked independently of personal SSH access.
- `DEPLOY_HOST` — `52.59.170.52`
- `DEPLOY_USER` — `admin`

### Server-side prerequisites (manual, one-time — not executed by this design, done by the user directly on the server)

1. Generate a new deploy keypair and add the public half to `admin`'s `~/.ssh/authorized_keys` on the server.
2. Grant `admin` scoped passwordless sudo for exactly the deploy commands, e.g. via `visudo`:
   ```
   admin ALL=(root) NOPASSWD: /usr/bin/git pull, /bin/bash /home/admin/app/portal/deploy/remote_run.sh
   ```
   (not a blanket `NOPASSWD: ALL`).
3. Confirm `~/app/portal` on the server has its git remote pointed at the GitHub repo (`git@github.com:andreyvoloshko/petanque-portal.git`), since the working copy there currently may still track Bitbucket.

Root is required for the deploy commands (confirmed: `admin` is not in the `docker` group / doesn't own the required paths), so passwordless sudo is necessary — GitHub Actions cannot answer an interactive sudo password prompt.

### Failure handling

`remote_run.sh` already has `set -e`, so a failed build/collectstatic/up step aborts the script and returns non-zero. The SSH action step then fails, the Actions run shows red in GitHub, and GitHub's default email notifications alert the pusher/repo watchers. No additional notification integration in this iteration.

### Explicitly rejected alternative

**Self-hosted runner on the production server** — considered but rejected in favor of the SSH-action approach. A self-hosted runner avoids putting an SSH key in GitHub Secrets, but requires a persistent privileged agent process running on the single production box, which is a larger standing attack surface than a key that can be rotated/revoked. The SSH-action approach is also more standard and easier to reason about.

## Testing / Verification

- After the workflow file and secrets are in place, verify with a real PR merge (or `workflow_dispatch`) and confirm:
  - The Actions run SSHes in successfully.
  - `git pull` advances the server checkout to the merged commit.
  - `remote_run.sh` completes (`docker compose up -d` succeeds).
  - The site is reachable and reflects the change in a browser, same as the current manual "check browser" step.
- No automated test suite is added as part of this work.
