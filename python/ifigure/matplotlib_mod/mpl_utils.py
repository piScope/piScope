from pkg_resources import parse_version
import matplotlib as mpl
mpl_version = mpl.__version__


def get_color_cycle(axes):
    if parse_version(mpl_version) >= parse_version('1.5'):
        return axes._get_lines.prop_cycler
    else:
        return axes._get_lines.color_cycle


def reset_color_cycle(axes):
    if parse_version(mpl_version) >= parse_version('1.5'):
        axes.set_prop_cycle(None)  # this reset color cycle
    else:
        pass
        #cycle = get_color_cycle(axes)
        #i = 0
        # while i < 50:
        #    c = cycle.next()
        #    if c == color_cycle[-1]: break
        #    i = i + 1


def get_color_cycle_list(axes):
    if parse_version(mpl_version) >= parse_version('1.5'):
        return [x['color'] for x in mpl.rcParams['axes.prop_cycle']]
    else:
        import six
        color = [six.next(get_color_cycle(axes))
                 for i in range(nx)]


def call_savefig_method(ifigure_canvas, name, *args, **kargs):
    '''
    print_pdf, and so on has gone in version 1.4
    this function is to absorb this issue.
    '''
    canvas = ifigure_canvas.canvas
    figure = ifigure_canvas._figure
    if hasattr(canvas, name):
        m = getattr(canvas, name)
        return m(*args, **kargs)
    else:
        return figure.savefig(*args, **kargs)
