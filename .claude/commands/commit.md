Analyze the current git changes and create a conventional commit.

Steps:
1. Run `git status` and `git diff HEAD` to understand what changed.
2. If there are no changes at all, tell the user and stop.
3. Stage everything that isn't already staged: `git add -A` — but first check `git status` to make sure no secrets or unintended files (like `.env`) are about to be included. If you spot anything suspicious, warn the user and stop.
4. Determine the conventional commit type based on the actual changes:
   - `feat` — new user-facing feature
   - `fix` — bug fix
   - `docs` — documentation only
   - `chore` — tooling, config, dependencies, CI, scripts
   - `refactor` — code restructuring without behavior change
   - `style` — formatting only
   - `test` — adding or updating tests
   - `perf` — performance improvement
5. Write a concise commit message: `type(optional-scope): short description` — lowercase, no period, imperative mood, under 72 characters. Add a body only if something non-obvious needs explaining.
6. Commit using a heredoc to preserve formatting.
7. Show the final `git log --oneline -1` so the user can confirm.
