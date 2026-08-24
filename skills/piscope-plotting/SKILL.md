---
name: piscope-plotting
description: "Use when the user wants to visualize data in piScope, especially for requests like 'show data in line plot', 'plot x vs y', 'make a scatter plot', or 'create a histogram'. This skill knows the piScope remote client API and should prefer plotting through ifigure.client instead of raw matplotlib calls."
---

# piScope plotting skill

Use this skill whenever the user wants to create, show, or update a plot in
piScope from a Python environment that can access the running piScope server.

## Core behavior

- Prefer piScope's client API over direct matplotlib commands.
- Use the remote plotting API exposed by `ifigure.client`.
- Treat the user request as a plotting command, not as a generic Python script.
- If the user says "show data in line plot", translate it to `plot(data)` or
  `plot(x, y)` using piScope semantics.
- Map visualization requests to the actual client names defined in
  `ifigure/client.py`.

## API to use

When plotting from an external Python interpreter, use:

```python
from ifigure.client import *
```

### Using the client in a plotting script

Import the client directly when writing a script:

```python
from ifigure.client import figure, plot

figure()
plot([1, 2, 3, 2, 1.0])
```

On Python 3.13 and later, importing the client warns that `async_print` uses
CPython's private `_pyrepl` API to preserve typed input during asynchronous
piScope output. Set `PYTHON_BASIC_REPL=1` before starting Python to use the
legacy readline REPL instead.

### Persistent session

To send multiple commands to the same piScope window, start the supplied
command server as a detached background process:

```bash
python -m ifigure.llm.session --id demo
```

Starting a session ID that is already active fails. Send each piScope expression
through its companion CLI using the same ID. IDs contain 1-64 letters, digits,
underscores, or hyphens:

```bash
python -m ifigure.llm.send --id demo "plot([1, 2, 3, 2, 1.0])"
```

The server keeps the window and piScope shell namespace alive.
`ifigure.llm.send` executes its command argument in that shell, so variables
persist between commands:

```bash
python -m ifigure.llm.send --id demo "import numpy as np; data = np.arange(30)"
python -m ifigure.llm.send --id demo "plot(data)"
```

The client exposes the piScope plotting surface as a flat command list. Use the
following routines when appropriate:

### Figure and axes management

- `figure`, `showpage`, `cla`, `cls`, `clf`, `subplot`, `isec`, `isection`
- `addpage`, `delpage`, `title`, `suptitle`, `xlabel`, `ylabel`, `zlabel`,
  `clabel`
- `xlog`, `ylog`, `zlog`, `clog`, `xlinear`, `ylinear`, `zlinear`, `clinear`
- `xlim`, `ylim`, `zlim`, `clim`, `xauto`, `yauto`, `zauto`, `cauto`
- `twinx`, `twiny`, `cbar`, `view`, `threed`, `lighting`

### 2D plotting

- `plot`, `oplot`, `loglog`, `semilogx`, `semilogy`, `timetrace`, `plotc`
- `scatter`, `hist`, `errorbar`, `oerrorbar`, `errorbarc`
- `triplot`, `ispline`, `contour`, `contourf`, `quiver`, `quiver3d`
- `image`, `specgram`, `spec`, `tripcolor`, `tricontour`, `tricontourf`
- `axline`, `axlinec`, `axspan`, `axspanc`, `fill`, `fill_between`,
  `fill_betweenx`
- `text`, `figtext`, `arrow`, `figarrow`, `legend`

### 3D plotting

- `surf`, `surface`, `revolve`, `solid`, `trisurf`

### Annotation and output

- `property`, `savefig`, `savedata`

These commands correspond to the interactive entry points in
`ifigure.widgets.book_viewer_interactive.BookViewerInteractive` and the
wrappers in `ifigure.interactive`.

## Natural-language mapping

- "show data in line plot" -> `plot(data)`
- "show x and y in line plot" -> `plot(x, y)`
- "plot this data" -> `plot(data)`
- "show me a scatter of x and y" -> `scatter(x, y)`
- "make a histogram of values" -> `hist(values)`
- "plot with log scaling" -> `loglog(x, y)`, `semilogx(x, y)`, or
  `semilogy(x, y)`
- "draw a contour plot" -> `contour(x, y, z)` or `contourf(x, y, z)`
- "show an image" -> `image(z)` or `image(x, y, z)`
- "add a label" -> `text(x, y, s)` or `figtext(x, y, s)`
- "surface plot" -> `surf(x, y, z)` or `surface(x, y, z)`
- "3D view" -> `threed('on')`, then `surf(...)` or `quiver3d(...)`
- "save the figure" -> `savefig(filename)`

## Important constraints

- Do not bypass the client/server layer with raw `matplotlib.pyplot.plot(...)`
  for piScope visualizations.
- Prefer names and data already available in the active Python namespace.
- If a variable name is not obvious, inspect the current namespace and choose
  the most relevant array-like object.
- When no explicit x/y pair is named, plot a single array with `plot(data)`.
- Use exact client names from the repository; do not invent names outside this
  surface.

## Output expectation

When the request is a visualization request, produce a Python snippet that
invokes the correct piScope client function. If relevant data is not yet in
scope, first identify the variable and then use the piScope client call.
