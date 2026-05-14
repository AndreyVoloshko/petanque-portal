# Task 001: Local Reproducibility

## Goal

Make the repository easy to run locally in a predictable way.

## Why This Matters

Every future change depends on being able to boot the app, run migrations, access pages, and reproduce bugs. Without this, security fixes and refactors are slower and riskier.

## Scope

- Create a local `.env` example that works with Docker Compose.
- Document startup commands.
- Verify web app, database, Nginx, and Adminer.
- Document how to run migrations and create a superuser.
- Decide how local static/media should work.

## Acceptance Criteria

- A developer can run one documented command and start the app.
- The homepage loads locally.
- Django admin login page loads locally.
- Database connection works.
- Setup steps are documented.

## Complexity

M

## Risk

Medium

## Big Win

High
