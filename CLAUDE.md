# Project Rules

## Environment

- All development, testing, and tooling must run inside the `conda` environment `ssh-todolist`.
- Do not install dependencies into `base`.
- Prefer `conda run -n ssh-todolist ...` when a shell is not already activated.

## Temporary Files

- Temporary scripts, smoke-test files, scratch notes, exported debug data, and one-off verification artifacts must be deleted after use.
- Generated caches and transient build artifacts must not be left in the project unless the user explicitly wants them kept.
- Before finishing a task, clean up obvious temporary outputs created during debugging or validation.

## Architecture

- Keep the service modular. Avoid coupling storage, HTTP handling, authentication, realtime transport, and business rules into one file.
- Maintain explicit contracts between API, auth, store, and realtime layers.
- New features must extend existing abstractions instead of introducing hidden side effects across modules.

## Change Discipline

- Make incremental changes that preserve working behavior.
- Keep verification steps scoped to the feature being changed.
