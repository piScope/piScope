#
#  user of cb (color zaxis)
#
import weakref
import ifigure


def get_axisparam(figaxes, axlist, figobj, func, cidx=0):
    for ax in axlist:
        if hasattr(ax, "_loaded_member"):
            if len(ax._loaded_member) == 0:
                del ax._loaded_member
                continue

            p = figaxes.get_td_path(figobj)[1:]
#           p = figaxes.get_relative_path(figobj)
            members = ax._loaded_member

            for m in members:
                if m == p:
                    #                 print 'found in loaded member'
                    func(ax)
                    ax._loaded_member = [t for t in members if t != p]
                    if len(ax._loaded_member) == 0:
                        del ax._loaded_member
                    return
    for a in axlist:

        if cidx in a._ax_idx:
            #      if len(a._member) == 0:
            func(a)
            return
    func(axlist[-1])


class XUser(object):
    def __init__(self):
        self._ax = None

    def get_xaxisparam(self):
        if self._ax is None:
            # create colorbar
            figaxes = self.get_figaxes()
            if figaxes is None:
                return None
            if len(figaxes._xaxis) == 0:
                figaxes.add_axis_param(dir='x')
            get_axisparam(figaxes, figaxes._xaxis, self,
                          self.set_ax, self._container_idx)
#           for ax in figaxes._xaxis:
#               if hasattr(ax, "_loaded_member"):
#                   members = ax["_loaded_member")]
#                   for m in members:
#                       if m == p:
#                           print 'found in loaded member'
#                           self.set_ax(ax)
#                           del members[m]
#                           return self._ax()
#           self.set_ax(figaxes._xaxis[0])
        return self._ax()

    def _ax_dead(self, ref):
        self._ax = None

    def set_ax(self, cb):
        self._ax = weakref.ref(cb, self._ax_dead)
        self._ax().add_member(self)

    def unset_ax(self):
        if self._ax is not None:
            self._ax().rm_member(self)
            self._ax = None


class YUser(object):
    def __init__(self):
        self._ay = None

    def get_yaxisparam(self):
        if self._ay is None:
            # create colorbar
            figaxes = self.get_figaxes()
            if figaxes is None:
                return None
            if len(figaxes._yaxis) == 0:
                figaxes.add_axis_param(dir='y')
            get_axisparam(figaxes, figaxes._yaxis, self,
                          self.set_ay, self._container_idx)
#           self.set_ay(figaxes._yaxis[0])
        return self._ay()

    def _ay_dead(self, ref):
        self._ay = None

    def set_ay(self, cb):
        self._ay = weakref.ref(cb, self._ay_dead)
        self._ay().add_member(self)

    def unset_ay(self):
        if self._ay is not None:
            self._ay().rm_member(self)
            self._ay = None


class ZUser(object):
    def __init__(self):
        self._az = None

    def get_zaxisparam(self):
        if self._az is None:
            # create colorbar
            figaxes = self.get_figaxes()
            if figaxes is None:
                return None
            if len(figaxes._zaxis) == 0:
                figaxes.add_axis_param(dir='z')
            get_axisparam(figaxes, figaxes._zaxis, self,
                          self.set_az, self._container_idx)
        return self._az()

    def _az_dead(self, ref):
        self._az = None

    def set_az(self, cb):
        self._az = weakref.ref(cb, self._az_dead)
        self._az().add_member(self)

    def unset_az(self):
        if self._az is not None:
            self._az().rm_member(self)
            self._az = None


class CUser(object):
    def __init__(self):
        self._ac = None

    def get_caxisparam(self):
        if self._ac is None:
            # create colorbar
            figaxes = self.get_figaxes()
            if figaxes is None:
                return None
            if len(figaxes._caxis) == 0:
                figaxes.add_axis_param(dir='c')
            get_axisparam(figaxes, figaxes._caxis, self,
                          self.set_ac, self._container_idx)
        return self._ac()

    def get_caxis_choices(self):
        figaxes = self.get_figaxes()
        if figaxes is None:
            return []
        return [c.name for c in figaxes._caxis]

    def set_selected_caxis(self, value, a):
        oc = self._ac()
        figaxes = self.get_figaxes()
        for c in figaxes._caxis:
            if c.name == value:
                break
        self.unset_ac()
        self.set_ac(c)
        if oc is not c:
            c.set_crangeparam_to_artist(a)

    def get_selected_caxis(self, a):
        return self._ac().name

    def _ac_dead(self, ref):
        self._ac = None

    def set_ac(self, cb):
        self._ac = weakref.ref(cb, self._ac_dead)
        self._ac().add_member(self)

    def unset_ac(self):
        if self._ac is not None:
            self._ac().rm_member(self)
            self._ac = None

    def has_cbar(self):
        figaxes = self.get_figaxes()
        if self._ac is None:
            False
        if figaxes is None:
            False
        ac = self._ac()
        return ac.has_cbar()

    def show_cbar(self):
        figaxes = self.get_figaxes()
        if self._ac is None:
            return
        if figaxes is None:
            return
        ac = self._ac()
        ac.show_cbar(figaxes)

    def hide_cbar(self):
        figaxes = self.get_figaxes()
        if self._ac is None:
            return
        if figaxes is None:
            return
        ac = self._ac()
        ac.hide_cbar()

    def onShowCB1(self, event):
        new_cb = False
        if self.has_cbar():
            new_cb = True
        self.show_cbar()
        canvas = event.GetEventObject()
        canvas.draw()
        ifigure.events.SendChangedEvent(self.get_figaxes(),
                                        w=canvas)
        return 1

    def onHideCB1(self, event):
        self.hide_cbar()
        canvas = event.GetEventObject()
        canvas.draw()
        ifigure.events.SendChangedEvent(self.get_figaxes(),
                                        w=canvas)
        return 1
