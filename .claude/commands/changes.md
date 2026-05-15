Explain the current uncommitted changes in plain language.

Steps:
1. Run `git diff HEAD` to see all unstaged and staged changes. Also run `git status` to get the full picture (new/deleted/renamed files).
2. Group the changes by theme or area — don't just list files mechanically.
3. For each group, explain **what changed and why it matters** in 2–4 sentences. Focus on intent and effect, not line-by-line narration.
4. Flag anything that looks risky, incomplete, or worth double-checking (e.g. a migration without a corresponding model change, a removed safety check, debug code left in).
5. End with a one-sentence overall summary of what this changeset does.

Keep the tone concise and technical. No bullet-point laundry lists of filenames.
