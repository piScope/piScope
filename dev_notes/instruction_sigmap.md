# SigMap Developer Workflow

SigMap generates a compact map of the repository for coding assistants.  Its
default output in this project is `.github/copilot-instructions.md`.

## Everyday Use

Regenerate the map after meaningful source changes:

```bash
sigmap
```

Before investigating a code task, ask SigMap for relevant context:

```bash
sigmap ask "How is script-editor completion implemented?"
```

For a file-oriented ranking instead, use:

```bash
sigmap --query "script editor completion"
```

After changing SigMap configuration or source directories, validate the
configuration:

```bash
sigmap validate
```

## Optional Automatic Regeneration

For live updates during a development session, run the watcher in a terminal:

```bash
sigmap --watch
```

Alternatively, start the detached watcher:

```bash
sigmap daemon start
```

Check or stop it with:

```bash
sigmap daemon status
sigmap daemon stop
```

Do not start a watcher automatically from an agent instruction: multiple
developers or agents can otherwise create duplicate watchers.  Start one only
when it is useful for the current development session.

## One-Time Setup

`sigmap --setup` regenerates context and may install repository integration
such as a Git hook and watcher configuration.  Run it deliberately during
developer setup, review the resulting changes, and do not put it in an
automatic agent workflow.
