# GitHub Actions CI/CD Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically deploy to the production server whenever a PR merges into `master` on GitHub.

**Architecture:** A GitHub Actions workflow triggered on push to `master` (and manual `workflow_dispatch`) SSHes into the production server using `appleboy/ssh-action` and runs the same `git pull && remote_run.sh` sequence the user runs manually today, via a dedicated deploy key and scoped passwordless sudo.

**Tech Stack:** GitHub Actions, `appleboy/ssh-action`, bash, existing `deploy/remote_run.sh`.

## Global Constraints

- No changes to `deploy/remote_run.sh` itself — the workflow reproduces the existing manual process, doesn't alter it.
- No test/lint gate before deploy (deploy-only scope, per spec).
- Root is required on the server for both `git pull` and `remote_run.sh` (confirmed: `admin` lacks the necessary permissions directly) — both must run under `sudo` in the workflow script. This corrects a minor inconsistency in the approved design doc, which only prefixed `remote_run.sh` with `sudo`; the user's actual manual process runs everything as root (`sudo su` first), so `git pull` needs `sudo` too for the automation to behave identically.
- Use a dedicated deploy SSH keypair, not the personal `thatsit-keypair1.pem`.
- Secrets (`DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`) are never pasted into chat or committed — set via `gh secret set` or the GitHub UI by the user directly.

---

## File Structure

- Create: `.github/workflows/deploy.yml` — the deploy workflow.
- Create: `docs/deployment.md` — secrets reference, server prerequisite checklist, manual-trigger/rollback instructions.
- Modify: `CLAUDE.md:56` — update the stale "No CI/CD" constraint.

---

### Task 1: Create the deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Produces: a workflow named `Deploy`, triggered on push to `master` and manual dispatch, expecting secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` to exist in the repo (set up in the Manual Steps section below — not by this task).

- [ ] **Step 1: Write the workflow file**

```yaml
name: Deploy

on:
  push:
    branches: [master]
  workflow_dispatch: {}

concurrency:
  group: deploy
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production server
        uses: appleboy/ssh-action@v1.2.0
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd ~/app/portal
            sudo git pull
            sudo bash deploy/remote_run.sh
```

- [ ] **Step 2: Validate workflow syntax with actionlint**

Run:
```bash
docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color
```
Expected: no output (exit code 0) for `.github/workflows/deploy.yml`. If actionlint reports errors, fix the YAML and re-run.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "Add GitHub Actions workflow to deploy on merge to master"
```

---

### Task 2: Update CLAUDE.md to reflect automated deploy

**Files:**
- Modify: `CLAUDE.md:56`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing consumed by other tasks — documentation only.

- [ ] **Step 1: Replace the stale constraint**

In `CLAUDE.md`, find this line (line 56):

```markdown
- **No CI/CD.** Deployment is manual via `./deploy/remote_run.sh` on the server.
```

Replace it with:

```markdown
- **CI/CD:** merging a PR into `master` on GitHub triggers `.github/workflows/deploy.yml`, which SSHes into the production server and runs `deploy/remote_run.sh` automatically. See `docs/deployment.md` for secrets and server setup. Manual deploys (`./deploy/remote_run.sh` after SSHing in) are still available for out-of-band fixes.
```

- [ ] **Step 2: Verify the change**

Run:
```bash
grep -n "CI/CD" CLAUDE.md
```
Expected: the new line appears at line 56, no leftover reference to "No CI/CD".

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Update CLAUDE.md for automated deploy workflow"
```

---

### Task 3: Write the deployment reference doc

**Files:**
- Create: `docs/deployment.md`

**Interfaces:**
- Consumes: the workflow file from Task 1 (references its exact commands/secret names — must stay in sync).
- Produces: nothing consumed by other tasks — reference documentation for the user's manual setup steps (see Manual Steps section).

- [ ] **Step 1: Write the doc**

```markdown
# Deployment

Deploys to the single production server (`52.59.170.52`) happen automatically
when a PR merges into `master`, via `.github/workflows/deploy.yml`. The
workflow SSHes in and runs the same steps as the old manual process:

\`\`\`
cd ~/app/portal
sudo git pull
sudo bash deploy/remote_run.sh
\`\`\`

## Triggering a deploy manually

Without pushing a new commit, trigger a re-deploy from the Actions tab:
GitHub repo → Actions → "Deploy" workflow → "Run workflow" → select `master`.

Or via the CLI:

\`\`\`bash
gh workflow run deploy.yml --ref master
\`\`\`

## Required GitHub secrets

Set once under repo Settings → Secrets and variables → Actions. Never commit
these values or paste them into chat/AI tooling.

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | `52.59.170.52` |
| `DEPLOY_USER` | `admin` |
| `DEPLOY_SSH_KEY` | Private half of a dedicated deploy keypair (see below) — **not** the personal `thatsit-keypair1.pem` |

## One-time server setup

1. Generate a dedicated deploy keypair (don't reuse personal keys, so it can
   be rotated/revoked independently):
   \`\`\`bash
   ssh-keygen -t ed25519 -f ~/petanque-deploy-key -C "github-actions-deploy" -N ""
   \`\`\`
2. Add the public key to the server:
   \`\`\`bash
   ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -o 'IdentitiesOnly yes' -p 22 admin@52.59.170.52 \\
     "cat >> ~/.ssh/authorized_keys" < ~/petanque-deploy-key.pub
   \`\`\`
3. Set the three secrets from the table above:
   \`\`\`bash
   gh secret set DEPLOY_HOST --body "52.59.170.52"
   gh secret set DEPLOY_USER --body "admin"
   gh secret set DEPLOY_SSH_KEY < ~/petanque-deploy-key
   \`\`\`
4. Grant `admin` scoped passwordless sudo for exactly the deploy commands.
   SSH into the server, then `sudo visudo -f /etc/sudoers.d/deploy` and add
   (confirm the real path to `git` on the server first with `which git`):
   \`\`\`
   admin ALL=(root) NOPASSWD: /usr/bin/git pull, /bin/bash /home/admin/app/portal/deploy/remote_run.sh
   \`\`\`
   Do not grant blanket `NOPASSWD: ALL` — scope it to just these two commands.
5. Confirm `~/app/portal` on the server has its git remote pointed at GitHub,
   not Bitbucket:
   \`\`\`bash
   ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -p 22 admin@52.59.170.52 \\
     "cd ~/app/portal && git remote -v"
   \`\`\`
   If it still points at `bitbucket.org`, update it:
   \`\`\`bash
   ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -p 22 admin@52.59.170.52 \\
     "cd ~/app/portal && git remote set-url origin git@github.com:andreyvoloshko/petanque-portal.git"
   \`\`\`
   The server also needs the GitHub deploy key (or a separate read key) able
   to `git pull` from the GitHub repo — add a deploy key under repo Settings
   → Deploy keys, or reuse an existing key already authorized on GitHub.

## Failure handling

`remote_run.sh` already has `set -e`, so a failed build/collectstatic/up
step aborts the script and the SSH action step fails. The Actions run shows
red in GitHub, and GitHub's default email notifications alert the pusher and
repo watchers — no extra notification integration is configured.

## Rollback / manual fallback

The manual process still works if the workflow needs to be bypassed:

\`\`\`bash
ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -o 'IdentitiesOnly yes' -p 22 admin@52.59.170.52
sudo su
cd ~/app/portal/
git pull
bash deploy/remote_run.sh
\`\`\`
```

- [ ] **Step 2: Review for consistency with Task 1's workflow file**

Confirm the commands, secret names, and file paths in `docs/deployment.md`
exactly match `.github/workflows/deploy.yml` from Task 1 (same `sudo git
pull`, same `sudo bash deploy/remote_run.sh`, same secret names
`DEPLOY_HOST`/`DEPLOY_USER`/`DEPLOY_SSH_KEY`).

- [ ] **Step 3: Commit**

```bash
git add docs/deployment.md
git commit -m "Document GitHub Actions deploy setup and secrets"
```

---

## Manual Steps (User Must Perform — Not Agent-Executable)

These require production SSH access and GitHub repo admin access that an
agent does not have. Follow the "One-time server setup" section of
`docs/deployment.md` (written in Task 3) in order:

1. Generate the dedicated deploy keypair.
2. Add its public key to the server's `authorized_keys`.
3. Set the three GitHub secrets (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`).
4. Configure scoped passwordless sudo on the server via `visudo`.
5. Confirm/update the server's git remote to point at GitHub, and ensure the
   server can pull from it (deploy key or existing GitHub auth on the box).

## End-to-End Verification (After Manual Steps Are Complete)

- [ ] Trigger a manual run: `gh workflow run deploy.yml --ref master`
- [ ] Watch it: `gh run watch` (or check the Actions tab)
- [ ] Confirm the run's log shows `git pull` advancing to the latest commit
      and `docker compose up -d` completing without error.
- [ ] Open the site in a browser and confirm it's reachable and reflects the
      latest `master` commit (same manual "check browser" step as before).
- [ ] Merge a real PR into `master` and confirm the workflow fires
      automatically (in addition to the manual dispatch test above).
