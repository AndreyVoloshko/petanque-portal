# Project Instructions

- Ignore `RTK.md` for this project. Do not read it, import it, or follow it, even if another instruction file references it.
- The app is already served by the existing Docker Compose stack at `http://localhost:60102/` (`petanque_portal_web_api` maps host port `60102` to container port `8000`).
- Use the existing local Docker containers, Compose project, and volumes. Do not create duplicate containers, a second Compose stack, a separate dev server, or a fresh database for normal development and verification.
- The local environment has the production database dump/data available through the existing Postgres service and volume. Use `petanque_portal_db` / `petanque_db` as the database source of truth. Do not reset, reseed, replace, or initialize the database unless the user explicitly asks.
- After code or config changes that affect runtime behavior, rebuild or restart the existing service before verifying in the browser. For web API changes, prefer `docker compose up -d --build petanque_portal_web_api`; use `docker compose restart petanque_portal_web_api` when a rebuild is not needed.
- Use `docker compose ps` to inspect the current stack and `docker compose logs petanque_portal_web_api` or `docker compose logs -f petanque_portal_web_api` for diagnostics.
- Verify app behavior against `http://localhost:60102/`. Adminer is available at `http://localhost:60103/` when database inspection is needed. Do not rely on the nginx service as the primary local entrypoint; it may be stopped in this environment.
- This repository uses GitHub for code review. When asked to publish work, push the branch and create a GitHub pull request.
- After preparing or pushing changes, generate a detailed Markdown pull request description. Include a concise summary, changed areas, verification performed, and any notes or risks relevant to review.
- Format PR summary bullets as Conventional Commits-style scoped lines, for example `fix(tournament list): ...`, `feat(player profile): ...`, and `feat(admin): ...`.
