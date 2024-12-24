'''
     routines for range adjustment

     purpose: create a array of actions when axes range was
              changed through GUI

              originally range adjustment action was done by
              parasit-style programming, which is difficult
              to grasp which part of program is called.
  
              idea is to orgnized the event handling in following
              steps.

                1) diagnose what event was happend and
                   construct action array directly induced
                   by the action

                   case 1 : pan: read range data from artist
                   case 2 : zoom: compute zoom from mouse event
                   case 3 : same x,y,,,
                   case 4 : auto x,y,,,
 
                   Diagnosis is done in event handler.

                   Actions are constructed by FigAxes:get_axrange_update_action,
                   which returns an array of action, and where the
                   next indirect action shold happen


                2) construct action array triggerd by the
                   direct action
                   
                   case1 : range change in colorbar should
                           change c-axes of main axes
               
                   This is done by FigAxes:get_axrange_update_action_i


                3) in multipage mode, do 1 and 2 as if the 
                   event happens in all pages.

                4) set it to history

              
    improvements
        re-computing range which was previously performed 
        everytime undo/redo is done is eliminated
 
        implementation of finish action in undo_redo_history
        is simplefied.
        
        

    keep methods:
        fig_axes.call_handle_axes_change:
        fig_obj::handle_axes_change
             a method which should be called after range parameters
             are all changed
             complication is FigColorbar is a child of main axes
        fig_axes.adjust_axes_range

    note:
        fig_axes can have two artists (more), multiple color bars
        axis_param is the place to store the data....

'''


import weakref
import numpy as np
# request builder


class RangeRequestMaker(object):
    '''
    routines for canvas
    '''
    @staticmethod
    def make_range_request_pan(fig_ax, auto=True, requests=None):
        #
        #  called from pan mode
        #
        #  fig_ax.call_handle_axes_change needs to be called
        #  after performing this request
        #
        actions = []
        arr = fig_ax._xaxis+fig_ax._yaxis
        if fig_ax._3D:
            arr.extend(fig_ax._zaxis)

        if requests is None:
            requests = {}
        if not fig_ax in requests:
            requests[fig_ax] = []

        for x in arr:
            for a in fig_ax.get_axes_artist_by_name(x.name):
                value = x.get_rangeparam()
                value[1] = auto
                value[2] = x.get_mpl_range(a)
                value[6] = False
                value[7] = False
                value[8] = False
                requests[fig_ax].append((x.name, value))
        return requests

    @staticmethod
    def make_range_request_zoom(fig_ax, direction, range, auto, ax, requests=None):
        #
        #  called from zoom mode
        #
        #
        #  fig_ax.call_handle_axes_change needs to be called
        #  after performing this request
        #

        if direction == 'x':
            arr = fig_ax._xaxis
        elif direction == 'y':
            arr = fig_ax._yaxis
        elif direction == 'z':
            arr = fig_ax._zaxis
        if requests is None:
            requests = {}

        if not fig_ax in requests:
            requests[fig_ax] = []
        for x in arr:
            if not ax in fig_ax.get_axes_artist_by_name(x.name):
                continue
            value = x.get_rangeparam()
            value[1] = auto
            value[2] = range
            value[6] = False
            value[7] = False
            value[8] = False
            requests[fig_ax].append((x.name, value))
        return requests

    @staticmethod
    def make_xyauto_request(fig_ax, direction, requests=None, scale='default'):
        # direction should be name[0]
        # if auto : call adjust_axes_range after this
        # scale default : no change

        attr = '_'+direction+'axis'
        g = getattr(fig_ax, attr)
        if requests is None:
            requests = {}
        if not fig_ax in requests:
            requests[fig_ax] = []
        for x in g:
            value = x.get_rangeparam()
            value[1] = True
            if scale != 'default':
                value[3] = scale
            requests[fig_ax].append((x.name, value))
        return requests

    @staticmethod
    def make_samexy_request(fig_ax, direction, auto, mode=1, requests=None):
        # direction should be name[0]
        # if auto : call adjust_axes_range after this
        #    not auto: call call_handle_axes_change after this
        # this should be called for each axes.
        attr = '_'+direction+'axis'
        if not hasattr(fig_ax, attr):
            return {}
        g = getattr(fig_ax, attr)

        ranges = [x.get_rangeparam()[2] for x in g]

        f_page = fig_ax.get_parent()
        if requests is None:
            requests = {}
        for f_ax in f_page.walk_axes():
            # if f_ax is fig_ax and mode == 1: continue
            if not hasattr(f_ax, attr):
                continue
            if not f_ax in requests:
                requests[f_ax] = []
            axparams = getattr(f_ax, attr)
            for i, g in enumerate(axparams):
                p = g.get_rangeparam()
                if i < len(ranges):
                    r = ranges[i]
                else:
                    r = ranges[-1]
                p[1] = auto
                if mode == 1:
                    p[2] = r
                requests[f_ax].append((g.name, p))
        # print requests
        if auto:
            for key in requests:
                requests[key] = key.compute_new_range(request=requests[key])
        return requests

    def make_autox_autoy_request(self, fig_ax):
        f_page = fig_ax.get_parent()
        requests = {}
        for f_ax in f_page.walk_axes():
            # if f_ax is fig_ax and mode == 1: continue
            requests[f_ax] = []
            axparams = getattr(f_ax, '_xaxis')
            for i, g in enumerate(axparams):
                p = g.get_rangeparam()
                p[1] = True
                requests[f_ax].append((g.name, p))
            ayparams = getattr(f_ax, '_yaxis')
            for i, g in enumerate(ayparams):
                p = g.get_rangeparam()
                p[1] = True
                requests[f_ax].append((g.name, p))

        for key in requests:
            requests[key] = key.compute_new_range(request=requests[key])
        return requests

    def make_samex_autoy_request(self, fig_ax):
        # direction should be name[0]
        # if auto : call adjust_axes_range after this
        #    not auto: call call_handle_axes_change after this
        # this should be called for each axes.
        g = getattr(fig_ax, '_xaxis')
        ranges = [x.get_rangeparam()[2] for x in g]

        f_page = fig_ax.get_parent()
        requests = {}
        for f_ax in f_page.walk_axes():
            # if f_ax is fig_ax and mode == 1: continue
            requests[f_ax] = []
            axparams = getattr(f_ax, '_xaxis')
            for i, g in enumerate(axparams):
                p = g.get_rangeparam()
                if i < len(ranges):
                    r = ranges[i]
                else:
                    r = ranges[-1]
                p[1] = False
                p[2] = r
                requests[f_ax].append((g.name, p))
            ayparams = getattr(f_ax, '_yaxis')
            for i, g in enumerate(ayparams):
                p = g.get_rangeparam()
                p[1] = True
                requests[f_ax].append((g.name, p))

        # print requests
        for key in requests:
            requests[key] = key.compute_new_range(request=requests[key])
        return requests

    @staticmethod
    def _add_induced_range_request(requests):
        irequests = {}
        for key in requests:
            d = key.get_induced_range_request(requests[key])
            for key2 in d:
                irequests[key2] = d[key2]
        for key in irequests:
            if not key in requests:
                requests[key] = []
            requests[key].extend(irequests[key])
        return requests

    def _create_multipage_rangerequest(self, requests):
        page = self._figure.figobj
        book = self._figure.figobj.get_figbook()

        mrequests = {}
        for p in book.walk_page():
            #            print requests
            for key in requests:
                iax = page.get_iaxes(key)
                ax = p.get_axes(iax)
                if ax is None:
                    continue

                mrequests[ax] = requests[key]
        return mrequests

    def expand_requests(self, requests):
        window = self.GetTopLevelParent()
        if window._use_samerange:
            mrequests = self._create_multipage_rangerequest(requests)

        requests = self._add_induced_range_request(requests)
        if window._use_samerange:
            mrequests = self._add_induced_range_request(mrequests)
            for key in mrequests:
                requests[key] = mrequests[key]
        return requests

    def send_range_action(self, requests, menu_name='edit', extra_actions=None):
        from ifigure.widgets.undo_redo_history import GlobalHistory

        a = []
        f = []
        for key in requests:
            if len(requests[key]) > 0:
                a.extend(key.make_range_actions(requests[key]))
                name = requests[key][0][0]
                f.append((weakref.ref(key), 'call_handle_axes_change', (name,)))
#            f.append((ifigure.events, 'SendRangeChangedEvent', (key,)))
        if len(a) == 0:
            return
        if extra_actions is not None:
            a.extend(extra_actions)
        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(
            a, finish_action=f, menu_name=menu_name)


class AdjustableRangeHolder(object):
    '''
    a class to be inheriged by FigAxes
    '''

    def make_range_actions(self, request):
        from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

        actions = []
        for x in request:
            p = self.get_axis_param(x[0])
            if not self.isempty():
                if p is None:
                    continue
                a = self.get_axes_artist_by_name(x[0])[0]
                actions.append(p.make_rangeparam_action(a,  x[1]))
            else:
                action = UndoRedoFigobjMethod(None,
                                              'axrangeparam', x[1], figobj=self)
                action.set_extrainfo(x[0])
                actions.append(action)
#        x = request[-1]
#        p = self.get_axis_param(x[0])
#        a = self.get_axes_artist_by_name(x[0])[0]
#        actions.append(p.make_rangeparam_action0(a,  x[1]))
        return actions

    def perform_range_request(self, request):
        if len(request) == 0:
            return
        for x in request:
            self.set_axrangeparam(x)

        # if artist is not realized, do not call handle_axes_change
        if self.isempty():
            return
        for child in self.walk_tree():
            if child is not self:
                child.handle_axes_change({'td': self, 'name': x[0]})

#        self.set_axrangeparam0(request[-1][0])

    def get_induced_range_request(self, request):
        return {}

    def adjust_axes_range(self, get_action=False):
        use_auto = True
        try:
            if self.get_figbook()._lock_scale:
                use_auto = False
        except:
            pass
        request = self.compute_new_range(use_auto=use_auto)

        if get_action:
            actions = self.make_range_actions(request)
            return actions
        else:
            self.perform_range_request(request)

    def compute_new_range(self, request=None, use_auto=True):
        def en_int(range0):
            import numpy as np
            a = range0[0]
            b = range0[1]
            if a != 0:
                si = a/abs(a)
                ex = int(np.log10(abs(a)))
#               if (a/(10.**ex) % 1)== 0.:
                ai = (np.floor(a/(10.**ex)))*10.**ex
#               else:
#                  ai = (np.floor(a/(10.**ex))-si)*10.**ex
            else:
                ai = 0.
            if b != 0:
                si = b/abs(b)
                ex = int(np.log10(abs(b)))
                if (b/(10.**ex) % 1) == 0.:
                    bi = (np.floor(b/(10.**ex)))*10.**ex
                else:
                    bi = (np.floor(b/(10.**ex))+1)*10.**ex
            else:
                bi = 0.
            return ai, bi

        def en_sym(range0):
            a = range0[0]
            b = range0[1]
            if abs(a) > abs(b):
                return (-abs(a), abs(a))
            else:
                return (-abs(b), abs(b))

        def en_int_sym(range, mode):
            if range[0] is not None:
                if np.iscomplex(range[0]):
                    range = sorted([float(np.real(range[0])),
                                    float(np.real(range[1]))])
                if mode[2]:
                    d = abs(float(range[0])-float(range[1]))
                    if range[1] > range[0]:
                        range[1] = range[1]+d/10.
                        range[0] = range[0]-d/10.
                    else:
                        range[1] = range[1]-d/10.
                        range[0] = range[0]+d/10.
            if (mode[0] and range[0] is not None and
                    range[1] is not None):
                range = en_int(range)
            if (mode[1] and range[0] is not None and
                    range[1] is not None):
                range = en_sym(range)
            return range

        def _value2param(value):
            return (value[0], value[1], value[2], value[3], value[4], value[5],
                    (value[6], value[7], value[8]))

        def _a2param(ax):
            return (ax.base, ax.auto, ax.range, ax.scale, ax.symloglin,
                    ax.symloglinscale, ax.mode)

        data = []
        newrange = {}

        max_range_width = 0.0
        # 0) first do xrange
        for ax in self._xaxis:
            base, auto, range, scale, symloglin, symscale, mode = _a2param(ax)
            if request is not None:
                for name, value in request:
                    if name == ax.name:
                        base, auto, range, scale, symloglin, symscale, mode = _value2param(
                            value)
                        break
            if (auto and use_auto) or range is None:
                range = [None]*2
                for m in ax.walk_member():
                    if m.is_suppress():
                        continue
                    range = m.get_xrange(range, scale=scale)
                range = en_int_sym(range, mode)
                if (range[0] is None or
                        range[1] is None):
                    range = (0, 1)
                if (range[0] == range[1]):
                    range = (range[0]-0.5, range[0]+0.5)
            p = [base, auto, range, scale, symloglin, symscale, ] + list(mode)
            newrange[ax] = range

            max_range_width = max(max_range_width, abs(range[1]-range[0]))
            data.append((ax.name, p))
        # 1) second do yrange
        for ay in self._yaxis:
            base, auto, range, scale, symloglin, symscale, mode = _a2param(ay)
            if request is not None:
                for name, value in request:
                    if name == ay.name:
                        base, auto, range, scale, symloglin, symscale, mode = _value2param(
                            value)
                        break
            if (auto and use_auto) or range[0] is None:
                range = [None]*2
                for m in ay.walk_member():
                    if m.is_suppress():
                        continue
                    ax = m.get_xaxisparam()
                    if ax in newrange:
                        xrange = newrange[ax]
                    else:
                        xrange = ax.range
                    range = m.get_yrange(range,
                                         xrange=xrange, scale=scale)
                range = en_int_sym(range, mode)
                if (range[0] is None or
                        range[1] is None):
                    range = (0, 1)
                if (range[0] == range[1]):
                    range = (range[0]-0.5, range[0]+0.5)
            p = [base, auto, range, scale, symloglin, symscale, ] + list(mode)
            newrange[ay] = range

            max_range_width = max(max_range_width, abs(range[1]-range[0]))
            data.append((ay.name, p))
        # 2-1) third do zrange
        for az in self._zaxis:
            base, auto, range, scale, symloglin, symscale, mode = _a2param(az)
            if request is not None:
                for name, value in request:
                    if name == az.name:
                        base, auto, range, scale, symloglin, symscale, mode = _value2param(
                            value)
                        break
            if (auto and use_auto) or range[0] is None:
                range = [None]*2
                for m in az.walk_member():
                    if m.is_suppress():
                        continue
                    ax = m.get_xaxisparam()
                    ay = m.get_yaxisparam()
                    if ax in newrange:
                        xrange = newrange[ax]
                    else:
                        xrange = ax.range
                    if ay in newrange:
                        yrange = newrange[ay]
                    else:
                        yrange = ay.range
                    range = m.get_zrange(range, xrange=xrange,
                                         yrange=yrange, scale=scale)
                range = en_int_sym(range, mode)
                if (range[0] is None or
                        range[1] is None):
                    range = (0, 1)
                if (range[0] == range[1]):
                    #range = (range[0]-0.5, range[0]+0.5)
                    range = (range[0]-max_range_width/2.,
                             range[0]+max_range_width/2.)
            p = [base, auto, range, scale, symloglin, symscale] + list(mode)
            data.append((az.name, p))
        # 2-2) third do crange
        for ac in self._caxis:
            base, auto, range, scale, symloglin, symscale, mode = _a2param(ac)
            if request is not None:
                for name, value in request:
                    if name == ac.name:
                        base, auto, range, scale, symloglin, symscale, mode = _value2param(
                            value)
                        break

            if (auto and use_auto) or range[0] is None:
                range = [None]*2
                for m in ac.walk_member():
                    if m.is_suppress():
                        continue
                    ax = m.get_xaxisparam()
                    ay = m.get_yaxisparam()
                    if ax in newrange:
                        xrange = newrange[ax]
                    else:
                        xrange = ax.range
                    if ay in newrange:
                        yrange = newrange[ay]
                    else:
                        yrange = ay.range
                    range = m.get_crange(range, xrange=xrange,
                                         yrange=yrange,
                                         scale=scale)
                range = en_int_sym(range, mode)
                if (range[0] is None or
                        range[1] is None):
                    range = (0, 1)
                if (range[0] == range[1]):
                    if range[0] == 0:
                        delta = 1 - np.nextafter(1.0, 0.0)
                        range = (-abs(delta), abs(delta))
                    else:
                        range = (range[0]-abs(range[0])/10,
                                 range[0]+abs(range[0])/10)
            p = [base, auto, range, scale, symloglin, symscale, ] + list(mode)
            data.append((ac.name, p))
        return data


class AdjustableRangeHolderCbar(AdjustableRangeHolder):
    '''
    routie for cbar
    '''

    def get_induced_range_request(self, request):
        '''
        range change in cbar will make additional
        request in main axes
        '''

        if self.getp("cdir") == 'v':
            self._artists[0].set_xlim((0, 1))
            for name, value in request:
                if name.startswith('y'):
                    cmin, cmax = value[2]
        else:
            self._artists[0].set_ylim((0, 1))
            for name, value in request:
                if name.startswith('x'):
                    cmin, cmax = value[2]

        # ifigure.events.SendIdleEvent(self)
        value = self._caxis_param().get_rangeparam()

#        if (value[2][0] != cmin or
#            value[2][1] != cmax):
        value[1] = False
        value[2] = [cmin, cmax]
        return {self.get_parent():
                [(self._caxis_param().name, value), ]}

#        return {}
