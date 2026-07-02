# Deployment

Deploys to the single production server (`52.59.170.52`) happen automatically
when a PR merges into `master`, via `.github/workflows/deploy.yml`. The
workflow SSHes in and runs the same steps as the old manual process:

```
sudo bash -c 'cd /root/app/portal && git pull && bash deploy/remote_run.sh'
```

The checkout lives under **root's** home directory (`/root/app/portal`), not the
SSH login user's — because the old manual process ran `sudo su` (becoming root)
before `cd ~/app/portal`, so `~` resolved to `/root`. The workflow runs the
whole sequence inside one `sudo bash -c '...'` shell so both `git pull` and
`remote_run.sh` (which sources `.env` via a relative path) execute with the
correct working directory. Two separate `sudo` invocations don't work here:
`remote_run.sh` needs to actually run *from* `/root/app/portal`, not just be
invoked by absolute path.

## Triggering a deploy manually

Without pushing a new commit, trigger a re-deploy from the Actions tab:
GitHub repo → Actions → "Deploy" workflow → "Run workflow" → select `master`.

Or via the CLI:

```bash
gh workflow run deploy.yml --ref master
```

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
   ```bash
   ssh-keygen -t ed25519 -f ~/petanque-deploy-key -C "github-actions-deploy" -N ""
   ```
2. Add the public key to the server:
   ```bash
   ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -o 'IdentitiesOnly yes' -p 22 admin@52.59.170.52 \
     "cat >> ~/.ssh/authorized_keys" < ~/petanque-deploy-key.pub
   ```
3. Set the three secrets from the table above:
   ```bash
   gh secret set DEPLOY_HOST --body "52.59.170.52"
   gh secret set DEPLOY_USER --body "admin"
   gh secret set DEPLOY_SSH_KEY < ~/petanque-deploy-key
   ```
4. Grant `admin` scoped passwordless sudo for exactly the deploy commands.
   SSH into the server, then `sudo visudo -f /etc/sudoers.d/deploy` and add
   (confirm the real path to `git` on the server first with `which git`):
   ```
   admin ALL=(root) NOPASSWD: /bin/bash -c "cd /root/app/portal && git pull && bash deploy/remote_run.sh"
   ```
   The workflow invokes this exact `bash -c "..."` string, so the sudoers
   entry must match it literally — verify with `sudo -l -U admin` or by
   running the exact command as `admin` and confirming it doesn't prompt for
   a password. Do not grant blanket `NOPASSWD: ALL` — scope it to just this
   one command.
5. Confirm `/root/app/portal` on the server has its git remote pointed at
   GitHub, not Bitbucket (requires `sudo`, since the checkout is under root's
   home):
   ```bash
   ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -p 22 admin@52.59.170.52 \
     "sudo git -C /root/app/portal remote -v"
   ```
   If it still points at `bitbucket.org`, update it:
   ```bash
   ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -p 22 admin@52.59.170.52 \
     "sudo git -C /root/app/portal remote set-url origin git@github.com:andreyvoloshko/petanque-portal.git"
   ```
   The server also needs the GitHub deploy key (or a separate read key) able
   to `git pull` from the GitHub repo — add a deploy key under repo Settings
   → Deploy keys, or reuse an existing key already authorized on GitHub.
   Since the workflow's `git pull` runs inside `sudo bash -c '...'`, it
   executes as **root**, so the deploy key, SSH config, and `known_hosts`
   entry for `github.com` must be set up under `/root/.ssh/` (not just
   `admin`'s) — otherwise the first automated pull fails on host-key
   verification or authentication.

## Failure handling

`remote_run.sh` already has `set -e`, so a failed build/collectstatic/up
step aborts the script and the SSH action step fails. The Actions run shows
red in GitHub, and GitHub's default email notifications alert the pusher and
repo watchers — no extra notification integration is configured.

## Rollback / manual fallback

The manual process still works if the workflow needs to be bypassed:

```bash
ssh -i ~/Work/petanque/ssh/thatsit-keypair1.pem -o 'IdentitiesOnly yes' -p 22 admin@52.59.170.52
sudo su
cd ~/app/portal/
git pull
bash deploy/remote_run.sh
```
