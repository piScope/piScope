from __future__ import print_function
import ifigure.widgets.canvas.custom_picker as cpicker


class event(object):
    pass


def dnd_sp(x, y, canvas):
    # figure : matplot figure
    # print x,y,figure

    figure = canvas._figure
    dx, dy = canvas.canvas.get_width_height()
    evt = event()
    evt.xdata = x/float(dx)
    evt.ydata = y/float(dy)
    evt.x = x
    evt.y = y

    page = figure.figobj

    for axes in reversed(figure.axes):
        hit, extra = cpicker.axes_picker(axes, evt,
                                         canvas=canvas.canvas)
        print((hit, extra))


#    except Exception:
#       pass
