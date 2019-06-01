from __future__ import print_function
import numpy as np
import matplotlib


from matplotlib.widgets import Button
import matplotlib.gridspec as gridspec


class color(object):
    def __init__(self, fig):
        self.color = ''
        self.collist = ['blue', 'green', 'red',
                        'cyan', 'magenta', 'yellow',
                        'black', 'white']
        self.r = 2
        self.c = 5
        self.fig = fig

    def build_interface(self, spec):
        gs0 = gridspec.GridSpecFromSubplotSpec(
            self.r, self.c,
            subplot_spec=spec)

        k = 0
        for i in range(1, self.c):
            for j in range(0, self.r):
                ax = self.fig.add_subplot(gs0[j, i])
                bt = Button(ax, self.collist[k])
                bt.on_clicked(self.hndl_event)
                k = k+1

    def get_size(self):
        pass

    def get_value(self):
        pass

    def set_value(self):
        pass

    def hndl_event(self, event):
        exit
        print(event)


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    fig = plt.figure()
    pl = color(fig)

    gs = gridspec.GridSpec(1, 1, left=0, bottom=0, right=1, top=0.2)
    subplot_spec = gs.new_subplotspec([0, 0])
    pl.build_interface(subplot_spec)

    plt.show()
