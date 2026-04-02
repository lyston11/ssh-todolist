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

- Keep the project modular. Avoid coupling storage, transport, UI rendering, and synchronization logic into one undifferentiated flow.
- Prefer clear boundaries between data layer, API layer, realtime sync layer, and frontend state/UI logic.
- When a file starts carrying multiple responsibilities, split it before it turns into a maintenance problem.
- New features must extend existing abstractions or introduce small focused modules instead of stacking special cases into large functions.
- Prioritize readable control flow, explicit data contracts, and low-ceremony structure over quick but brittle patches.

## Change Discipline

- Make incremental changes that preserve working behavior.
- Keep verification steps scoped to the feature being changed.
- If a temporary workaround is necessary, mark it clearly and remove it once the proper implementation exists.
