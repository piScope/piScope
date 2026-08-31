---
name: piscope-plotting
description: "Use when the user asks for plotting in piScope (line plot, scatter, histogram, contour, image, 3D surface). Prefer ifigure plotting commands over raw matplotlib."
---

# piScope plotting skill

Use this skill when the user wants to create, update, or save a plot in piScope. 

## Core rules

- Use piScope plotting commands, not `matplotlib.pyplot`.
- Use persistent session, discussed below, to visualize data.
- Use the following import to visualize data when generating a non-interactive script.
```python
from ifigure.interactive import *
```
- Treat requests as plotting intent and map them to piScope commands.
- Keep snippets short and executable.
- Make sure to use correct Python exectuable. If you are inside virtual environment, use
the environment.

## Quick mapping

- line plot -> `plot(data)` or `plot(x, y)`
- scatter -> `scatter(x, y)`
- histogram -> `hist(values)`
- contour -> `contour(x, y, z)` or `contourf(x, y, z)`
- image -> `image(z)` or `image(x, y, z)`
- 3D surface -> `threed('on')` then `surf(x, y, z)`
- save figure -> `savefig(filename)`

## Persistent session workflow

When running commands from an external Python process, keep one persistent piScope session and
send multiple commands to it.
Always call scripts by absolute installed path. Do not use python command itself. Use llmrun,
in order to run the script in proper PYTHONPATH

```bash
llmrun /absolute/path/to/piscope-plotting/scripts/launch.py
llmrun /absolute/path/to/piscope-plotting/scripts/send.py --port "$PORT" "plot([1,2,3])"
```
The launcher returns two values. The first value is `PORT`.
Treat the second value as `PID`.
Use the same absolute `send.py` path repeatedly so variables persist in the same piScope shell session.

## Plotting command

### Figure and axes management
- `figure`, `showpage`, `cla`, `cls`, `clf`, `subplot`, `isec`, `isection`
- `addpage`, `delpage`, `title`, `suptitle`, `xlabel`, `ylabel`, `zlabel`, `clabel`
- `xlog`, `ylog`, `zlog`, `clog`, `xlinear`, `ylinear`, `zlinear`, `clinear`
- `xlim`, `ylim`, `zlim`, `clim`, `xauto`, `yauto`, `zauto`, `cauto`
- `twinx`, `twiny`, `cbar`, `view`, `threed`, `lighting`

### 2D plotting
- `plot`, `oplot`, `loglog`, `semilogx`, `semilogy`, `timetrace`, `plotc`
- `scatter`, `hist`, `errorbar`, `oerrorbar`, `errorbarc`
- `triplot`, `ispline`, `contour`, `contourf`, `quiver`, `quiver3d`
- `image`, `specgram`, `spec`, `tripcolor`, `tricontour`, `tricontourf`
- `axline`, `axlinec`, `axspan`, `axspanc`, `fill`, `fill_between`, `fill_betweenx`
- `text`, `figtext`, `arrow`, `figarrow`, `legend`

### 3D plotting
- `surf`, `surface`, `revolve`, `solid`, `trisurf`

### Output

- `property`, `savefig`, `savedata`

## Natural-language mapping
- "show data in line plot" -> `plot(data)`
- "show x and y in line plot" -> `plot(x, y)`
- "plot this data" -> `plot(data)`
- "show me a scatter of x and y" -> `scatter(x, y)`
- "make a histogram of values" -> `hist(values)`
- "plot with log scaling" -> `loglog(x, y)`, `semilogx(x, y)`, or `semilogy(x, y)`
- "draw a contour plot" -> `contour(x, y, z)` or `contourf(x, y, z)`
- "show an image" -> `image(z)` or `image(x, y, z)`
- "add a label" -> `text(x, y, s)` or `figtext(x, y, s)`
- "surface plot" -> `surf(x, y, z)` or `surface(x, y, z)`
- "3D view" -> `threed('on')`, then `surf(...)` or `quiver3d(...)`
- "save the figure" -> `savefig(filename)`

## Output expectation

Return a minimal Python snippet that uses piScope commands directly. If variables are missing, first create or identify them, then plot.
