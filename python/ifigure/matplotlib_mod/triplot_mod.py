# triplot_mod
###
# modified to return artists

from matplotlib.cbook import ls_mapper
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.tri import Triangulation
import numpy as np


def _process_plot_format(fmt):
    """
    Process a MATLAB style color/line style format string.  Return a
    (*linestyle*, *color*) tuple as a result of the processing.  Default
    values are ('-', 'b').  Example format strings include:

    * 'ko': black circles
    * '.b': blue dots
    * 'r--': red dashed lines

    .. seealso::

        :func:`~matplotlib.Line2D.lineStyles` and
        :func:`~matplotlib.pyplot.colors`
            for all possible styles and color format string.
    """
    import matplotlib
    rcParams = matplotlib.rcParams

    import matplotlib.colors as mcolors

    linestyle = None
    marker = None
    color = None

    # Is fmt just a colorspec?
    try:
        color = mcolors.colorConverter.to_rgb(fmt)

        # We need to differentiate grayscale '1.0' from tri_down marker '1'
        try:
            fmtint = str(int(fmt))
        except ValueError:
            return linestyle, marker, color  # Yes
        else:
            if fmt != fmtint:
                # user definitely doesn't want tri_down marker
                return linestyle, marker, color  # Yes
            else:
                # ignore converted color
                color = None
    except ValueError:
        pass  # No, not just a color.

    # handle the multi char special cases and strip them from the
    # string
    if fmt.find('--') >= 0:
        linestyle = '--'
        fmt = fmt.replace('--', '')
    if fmt.find('-.') >= 0:
        linestyle = '-.'
        fmt = fmt.replace('-.', '')
    if fmt.find(' ') >= 0:
        linestyle = 'None'
        fmt = fmt.replace(' ', '')

    chars = [c for c in fmt]

    for c in chars:
        if c in mlines.lineStyles:
            if linestyle is not None:
                raise ValueError(
                    'Illegal format string "%s"; two linestyle symbols' % fmt)
            linestyle = c
        elif c in mlines.lineMarkers:
            if marker is not None:
                raise ValueError(
                    'Illegal format string "%s"; two marker symbols' % fmt)
            marker = c
        elif c in mcolors.colorConverter.colors:
            if color is not None:
                raise ValueError(
                    'Illegal format string "%s"; two color symbols' % fmt)
            color = c
        else:
            raise ValueError(
                'Unrecognized character %c in format string' % c)

    if linestyle is None and marker is None:
        linestyle = rcParams['lines.linestyle']
    if linestyle is None:
        linestyle = 'None'
    if marker is None:
        marker = 'None'

    return linestyle, marker, color


def triplot(ax, *args, **kwargs):
    """
    Draw a unstructured triangular grid as lines and/or markers to
    the :class:`~matplotlib.axes.Axes`.

    The triangulation to plot can be specified in one of two ways;
    either::

      triplot(triangulation, ...)

    where triangulation is a :class:`~matplotlib.tri.Triangulation`
    object, or

    ::

      triplot(x, y, ...)
      triplot(x, y, triangles, ...)
      triplot(x, y, triangles=triangles, ...)
      triplot(x, y, mask=mask, ...)
      triplot(x, y, triangles, mask=mask, ...)

    in which case a Triangulation object will be created.  See
    :class:`~matplotlib.tri.Triangulation` for a explanation of these
    possibilities.

    The remaining args and kwargs are the same as for
    :meth:`~matplotlib.axes.Axes.plot`.

    **Example:**

        .. plot:: mpl_examples/pylab_examples/triplot_demo.py
    """
    import matplotlib.axes
    tri, args, kwargs = Triangulation.get_from_args_and_kwargs(*args, **kwargs)

    x = tri.x
    y = tri.y
    edges = tri.edges

    # If draw both lines and markers at the same time, e.g.
    #     ax.plot(x[edges].T, y[edges].T, *args, **kwargs)
    # then the markers are drawn more than once which is incorrect if alpha<1.
    # Hence draw lines and markers separately.

    # Decode plot format string, e.g. 'ro-'
    fmt = ''
    if len(args) > 0:
        fmt = args[0]

#   _process_plot_format moves around so I made copy here.
#   not a best solution...;D
#    linestyle, marker, color = matplotlib.axes._process_plot_format(fmt)
    linestyle, marker, color = _process_plot_format(fmt)

    # Draw lines without markers, if lines are required.
    a = []
    if linestyle is not None and linestyle != 'None':
        kw = kwargs.copy()
        kw.pop('marker', None)     # Ignore marker if set.
        kw['linestyle'] = ls_mapper[linestyle]
        kw['edgecolor'] = color
        kw['facecolor'] = None

        vertices = np.column_stack((x[edges].flatten(), y[edges].flatten()))
        codes = ([Path.MOVETO] + [Path.LINETO])*len(edges)

        path = Path(vertices, codes)
        pathpatch = PathPatch(path, **kw)

        ax.add_patch(pathpatch)
        a.append(pathpatch)

    # Draw markers without lines.
    # Should avoid drawing markers for points that are not in any triangle?
    kwargs['linestyle'] = ''

    # without hiding points explicitly, marker would expose hidden points.
    idx = np.unique(edges.flatten())
    l = ax.plot(x[idx], y[idx], *args, **kwargs)
    a = l+a
    return a
