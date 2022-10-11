import ifigure.utils.cbook as cbook
import ifigure.events
from ifigure.mto.fig_axes import FigAxes, FigInsetAxes
from ifigure.widgets.canvas.custom_picker import linehit_test, abs_d
from ifigure.widgets.undo_redo_history import GlobalHistory, UndoRedoArtistProperty, UndoRedoFigobjProperty, UndoRedoFigobjMethod
import weakref
import ifigure.utils.pickle_wrapper as pickle
import numpy as np

'''
 GenericPointHolder
 GenericPoint

 classes to handle (x. y) points which is expressed
 in various coordinate system.

 it provides...
     interface to change setting
     routine to convert coords

'''


class GenericPointsHolder(object):
    def __init__(self, num=0, **kywds):
        self._gp_points = []
        trans = self.getvar('trans')
        transaxes = self.getvar('transaxes')
        if num != 0:
            for k in range(num):
                self.add_gp(GenericPoint(0, 0))

    def set_parent(self, parent):
        self.set_gp_figpage()
        for gp in self._gp_points:
            if hasattr(gp, '_d_bk'):
                #                print self.get_figpage()._artists
                gp.dict_to_gp(gp._d_bk, self)

    def destroy(self):
        for p in self._gp_points:
            self.rm_gp(p)

    def add_gp(self, gp):
        self._gp_points.append(gp)
        return len(self._gp_points)-1

    def rm_gp(self, gp):
        self._gp_points.remove(gp)

    def get_gp(self, i):
        return self._gp_points[i]

    def num_gp(self):
        return len(self._gp_points)

    def set_gp_by_vars(self):
        trans = self.getvar('trans')
        transa = self.getvar('transaxes')
        for k, gp in enumerate(self._gp_points):
            transaxes = transa[k]
            if trans is not None:
                gp.set_trans(trans[k*2:(k+1)*2])
            if transaxes is None:
                ax = None
            elif transaxes == 'default':
                ax = self.get_figaxes()
            else:
                try:
                    ax = find_by_full_path(transaxes)
                except:
                    ax = None
            if ax is not None:
                self.set_gp_figaxes(gp, ax, no_conversion=True)

    def set_gp_figpage(self):
        figpage = self.get_figpage()
        if figpage is None:
            return
        for gp in self._gp_points:
            gp.set_figpage(figpage)
            if gp.trans is None:
                figaxes = self.get_figaxes()
                if figaxes is None:
                    gp.set_trans(['figure', 'figure'])
                else:
                    gp.set_trans(['axes', 'axes'])
                    gp.set_figaxes(figaxes)

    def set_gp_figaxes(self, p, figaxes, no_conversion=False):
        '''
        change figaxes used for transform of gp
        '''
        if figaxes is None:
            return
        if isinstance(p, GenericPoint):
            gp = p
        else:
            gp = self.get_gp(p)
        # print gp.get_figaxes(), gp.get_figaxes()
        if gp.get_figaxes() is not None:
            t_from = gp.get_gp_transform(dir='both')  # <-it should be here?
        else:
            no_conversion = True
        old_figaxes = gp.get_figaxes()
        if old_figaxes is not None:
            old_figaxes.remove_update_client(self)
        gp.set_figaxes(figaxes)
        figaxes.add_update_client(self)
        if len(figaxes._artists) == 0:
            return
        if no_conversion:
            return
        t_to = gp.get_gp_transform(dir='both')
#        t_from = gp.get_gp_transform(dir='both')
        gp.x, gp.y = gp.convert_trans_p((gp.x, gp.y), t_from, t_to)

    def move_gp_points(self, index, dx, dy, action=True):
        gp = self.get_gp(index)
        new_x, new_y = gp.calc_new_points(dx, dy)
        if action:
            action1 = UndoRedoFigobjMethod(self._artists[0],
                                           'gppoint'+str(index),
                                           (new_x, new_y))
            return action1
        else:
            m = getattr(self, 'set_'+name1)
            m((new_x, new_y))

    def get_device_point(self, index):
        return self._gp_points[index].get_device_point()

    def set_device_point(self, index, x, y):
        return self._gp_points[index].set_device_point(x, y)

    def set_gppoint0(self, xy, a):
        self.set_gp_point(0, xy[0], xy[1])
        self.set_update_artist_request()

    def set_gppoint1(self, xy, a):
        self.set_gp_point(1, xy[0], xy[1])
        self.set_update_artist_request()

    def set_gppoint2(self, xy, a):
        self.set_gp_point(2, xy[0], xy[1])
        self.set_update_artist_request()

    def set_gppoint3(self, xy, a):
        self.set_gp_point(3, xy[0], xy[1])
        self.set_update_artist_request()

    def get_gppoint0(self, a):
        return self.get_gp_point(0)

    def get_gppoint1(self, a):
        return self.get_gp_point(1)

    def get_gppoint2(self, a):
        return self.get_gp_point(2)

    def get_gppoint3(self, a):
        return self.get_gp_point(3)

    def get_gp_point(self, i):
        return self._gp_points[i].x, self._gp_points[i].y

    def set_gp_point(self, i, x, y, trans=None):
        if trans is not None:
            self._gp_points[i].trans = trans
        self._gp_points[i].x = x
        self._gp_points[i].y = y

    def change_gp_trans(self, gp, i0, value):
        '''
        change transform method of gp
        '''
        gp.change_trans(i0, value)

    def gp_hittest_p(self, evt, gp):
        x1, y1 = gp.get_device_point()
        return abs_d(x1, y1, evt.x, evt.y) < 9

    def gp_hittest_rect(self, evt, gp1, gp2):
        x1, y1 = gp1.get_device_point()
        x2, y2 = gp2.get_device_point()

        if abs_d(x1, y1, evt.x, evt.y) < 9:
            return 1
        if abs_d(x2, y1, evt.x, evt.y) < 9:
            return 2
        if abs_d(x2, y2, evt.x, evt.y) < 9:
            return 3
        if abs_d(x1, y2, evt.x, evt.y) < 9:
            return 4

#        print (linehit_test(evt.x, evt.y, x1, y1, x2, y2),
#            evt.x >= min([x1, x2]),
#            evt.y >= min([y1, y2]),
#            evt.x <= max([x1, x2]),
#            evt.y <= max([y1, y2]))

        if (linehit_test(evt.x, evt.y, x1, y1, x2, y2) and
            evt.x >= min([x1, x2])-2 and
            evt.y >= min([y1, y2])-2 and
            evt.x <= max([x1, x2])+2 and
                evt.y <= max([y1, y2])+2):
            hit = True
            return 5
        return 0

    def gp_hittest_line(self, evt, gp1, gp2):
        x1, y1 = gp1.get_device_point()
        x2, y2 = gp2.get_device_point()
        v1 = (x2 - x1, y2 - y1)
        v2 = (evt.x - x1, evt.y - y1)
        l1 = np.sqrt(v1[0]*v1[0]+v1[1]*v1[1])
        l2 = np.sqrt(v2[0]*v2[0]+v2[1]*v2[1])
        d = abs(v1[0]*v2[1] - v1[1]*v2[0])/l1     # distance
        d2 = (v1[0]*v2[0] + v1[1]*v2[1])/l1/l1  # ratio
        # print d, d2

        if (0 < d2 < 1) and d < 5:
            return 1
        return 0

    def set_gp_trans(self, value, a=None):
        i = value[0][0]
        idx = value[0][1]
        v = value[1]
        gp = self.get_gp(i)
        self.change_gp_trans(gp, idx, v)

    def get_gp_trans(self, a=None, extra=None):
        i = extra[0]
        idx = extra[1]
        gp = self.get_gp(i)
        return gp.trans[idx]

    def gp_canvas_menu(self, gp):
        return gp.make_canvas_menu(self)

    def gp_holder_canvas_menu(self):
        '''
        provide simple version of gp menu
        allow to change the setting of all gp points
        at once
        '''
        a0 = ['figure', 'axes', 'data']
        funcs = [None]*3
        for k in range(3):
            def func(evt, value=a0[k], holder=self):
                ac = []
                for i in range(holder.num_gp()):
                    action1 = UndoRedoFigobjMethod(self._artists[0],
                                                   'gp_trans', value)
                    action1.set_extrainfo((i, 0))
                    action2 = UndoRedoFigobjMethod(self._artists[0],
                                                   'gp_trans', value)
                    action2.set_extrainfo((i, 1))
                    ac.append(action1)
                    ac.append(action2)
#                    gp = holder.get_gp(i)
#                    holder.change_gp_trans(gp, 0, value)
#                    holder.change_gp_trans(gp, 1, value)
                window = evt.GetEventObject().GetTopLevelParent()
                hist = GlobalHistory().get_history(window)
                hist.make_entry(ac, menu_name='change trans')
            funcs[k] = func

        value = []
        for i in range(self.num_gp()):
            value = value + self.get_gp(i).trans
#        flag = True
#        for i in range(len(value)):
#            if value[i] != value[0]: flag = False
        m = ["*figure", "*axes", "*data"]
        if 'figure' in value:
            m[0] = '^figure'
        if 'axes' in value:
            m[1] = '^axes'
        if 'data' in value:
            m[2] = '^data'

        menu = [("+Coods...", None, None),
                (m[0], funcs[0], None),
                (m[1],  funcs[1], None),
                (m[2],  funcs[2], None),
                ("!",  None, None), ]
        if self.get_figaxes() is None:
            menu.extend([
                ("Select Axes...", self.onSelTransaxes_all, None), ])
        return menu

    def onSelTransaxes_all(self, evt):
        def onSelTransaxes_cb(figaxes, holder=self):
            for gp in self._gp_points:
                holder.onSelTransaxes_cb(figaxes, gp)

        if self.num_gp() == 0:
            return
        gp = self.get_gp(0)
        ifigure.events.SendInteractiveAxesSelection(self, w=evt.GetEventObject(),
                                                    callback=onSelTransaxes_cb,
                                                    figaxes=gp.get_figaxes(),
                                                    handler=evt.GetEventObject())

    def onSelTransaxes(self, evt, gp):
        def onSelTransaxes_cb(figaxes, gp0=gp):
            self.onSelTransaxes_cb(figaxes, gp0)
        ifigure.events.SendInteractiveAxesSelection(self,
                                                    w=evt.GetEventObject(),
                                                    callback=onSelTransaxes_cb,
                                                    figaxes=gp.get_figaxes(),
                                                    handler=evt.GetEventObject())

    def onSelTransaxes_cb(self, figaxes, gp):
        #        print figaxes.get_full_path()
        self.set_gp_figaxes(gp, figaxes)

    def save_data(self, fid=None):
        data = []
        for gp in self._gp_points:
            data.append(gp.gp_to_dict())
        pickle.dump(data, fid)

    def save_data2(self, data):
        #        import traceback
        #        traceback.print_stack()
        try:
            # if target axes was destroyed already
            # this step fails
            # this happens when closing window,, and so on???
            if hasattr(self, "_loaded_gp_data"):
                d = self._loaded_gp_data
            else:
                d = [gp.gp_to_dict() for gp in self._gp_points]
        except:
            d = []
        data['GenericPointsHolder'] = (1, d)
        return data

    def load_data(self, fid=None):
        h2 = pickle.load(fid)
        if self.hasp("loaded_property"):
            lp = self.getp("loaded_property")
        else:
            lp = []
        lp.append(h2)
        self.setp("loaded_property", lp)

    def load_data2(self, data):
        if not 'GenericPointsHolder' in data:
            return
        h2 = data['GenericPointsHolder'][1]
        if len(h2) > len(self._gp_points):
            for k in range(len(h2) - len(self._gp_points)):
                self.add_gp(GenericPoint(0, 0))
        elif len(h2) < len(self._gp_points):
            for k in range(-len(h2) + len(self._gp_points)):
                self._gp_points.remove(self._gp_points[-1])
#        for k, gp in enumerate(self._gp_points):
#            gp.dict_to_gp(h2[k], self)

        self._loaded_gp_data = h2


class GenericPoint(object):
    def __init__(self, x=0, y=0, trans=['figure']*2,
                 figaxes=None, figpage=None):
        object.__init__(self)
        self.x = x
        self.y = y
        self.trans = trans  # 'figure', 'axes', 'points'

        self.set_figpage(figpage)
        self.set_figaxes(figaxes)

    def __repr__(self):
        return 'GenericPoint('+str(self.x) + ',' + str(self.y) + ':'+','.join(self.trans)+')'

    def gp_to_dict(self):
        if self.figaxes() is not None:
            xy = self.figaxes().get_rect()
            ax = ((xy[0]+xy[2])/2, (xy[1]+xy[3])/2)
        else:
            ax = None
        d = {"x": self.x,
             "y": self.y,
             "trans": self.trans,
             "ax": ax}
        return d

    def dict_to_gp(self, d, holder):
        self.x = d["x"]
        self.y = d["y"]
        self.trans = d["trans"]

        if d["ax"] is None:
            self.set_figaxes(None)
        else:
            rect = []
            if holder.get_figpage() is None:
                # if parent is not yet given
                # this should be postponed.
                # till next set_parent is called
                self._d_bk = d
                return

            for td in holder.get_figpage().walk_tree():
                if isinstance(td, FigAxes):
                    rect.append((td, td.get_rect()))

            # set reference axes to the closest axes
            area = [abs((xy[1][2]-xy[1][0])*(xy[1][3]-xy[1][1]))
                    for xy in rect]

            idx = [x[0] for x in sorted(enumerate(area), key=lambda x:x[1])]
            dist = [np.sqrt((d["ax"][0] - (rect[i][1][0] + rect[i][1][2])/2.)**2 +
                            (d["ax"][1] - (rect[i][1][1] + rect[i][1][3])/2.)**2) for i in idx]

            i = np.argmin(dist)

            holder.set_gp_figaxes(self, rect[idx[i]][0])
            self.x = d["x"]
            self.y = d["y"]

            if hasattr(self, '_d_bk'):
                del self._d_bk
        return self

    def set_figaxes(self, figaxes=None):
        #        print 'setting figaxes', figaxes
        #        import traceback
        #        traceback.print_stack()
        if figaxes is not None:
            self.figaxes = weakref.ref(figaxes, self.lost_figaxes)
        else:
            self.figaxes = cbook.WeakNone()

    def get_figaxes(self):
        return self.figaxes()

    def set_figpage(self, figpage=None):
        if figpage is not None:
            self.figpage = weakref.ref(figpage, self.lost_figaxes)
        else:
            self.figpage = cbook.WeakNone()

    def get_figpage(self):
        return self.figpage()

    def change_trans(self, i0, value):
        '''
        change transform method of gp
        '''
        trans = [name for name in self.trans]
        trans[i0] = value
        t_from = self.get_gp_transform(dir='both')
        t_to = self.get_gp_transform(dir='both', name=trans)
        self.x, self.y = self.convert_trans_p((self.x, self.y), t_from, t_to)
        self.trans = trans

    def change_trans_figaxes(self, gp, figaxes):
        '''
        change figaxes used for transform of gp
        '''
        t_from = gp.get_gp_transform(dir='both')
        self.set_figaxes(figaxes)  # ?
        t_to = gp.get_gp_transform(dir='both')
        gp.x, gp.y = gp.convert_trans_p((gp.x, gp.y), t_from, t_to)

    def lost_figaxes(self, ref):
        pass
        # print 'referred axes is deleted'

    def set_trans(self, value):
        self.trans = value

    def get_gp_transform(self, dir='both', name=None):
        ''' 
        get transform of genericpoint
        '''
        def get_transform(figaxes, figpage, n):
            if figaxes is None:
                t = figpage._artists[0].transFigure
            elif n == 'data':
                t = figaxes._artists[0].transData
            elif n == 'axes':
                t = figaxes._artists[0].transAxes
            elif n == 'figure':
                t = figpage._artists[0].transFigure
            return t

        ans = []
        if dir == 'x' or dir == 'both':
            if name is None:
                n = self.trans[0]
            else:
                try:
                    n = name[0]
                except Exception:
                    n = name
            ans.append(get_transform(self.figaxes(), self.figpage(), n))
        if dir == 'y' or dir == 'both':
            if name is None:
                n = self.trans[1]
            else:
                try:
                    n = name[1]
                except Exception:
                    n = name
            ans.append(get_transform(self.figaxes(), self.figpage(), n))
        return ans

    def make_canvas_menu(self, holder):
        def make_menu_str(i):
            trans = self.trans[i]
            a0 = ['figure', 'axes', 'data']
            a = ['figure', 'axes', 'data']
            funcs = [None]*3
            for k in range(3):
                if a[k] == trans:
                    a[k] = '^'+a[k]
                else:
                    a[k] = '*'+a[k]

                def func(evt, value=a0[k], i0=i, h=holder, gp=self):
                    id = h._gp_points.index(gp)
                    action1 = UndoRedoFigobjMethod(h._artists[0],
                                                   'gp_trans', value)
                    action1.set_extrainfo((id, i0))
                    window = evt.GetEventObject().GetTopLevelParent()
                    hist = GlobalHistory().get_history(window)
                    hist.make_entry([action1], menu_name='change trans')

                funcs[k] = func
            return a, funcs

        def make_menu_list(dir, a, funcs):
            m1 = [("+"+dir+" Coords",  None, None),
                  (a[0],  funcs[0], None),
                  (a[1],  funcs[1], None),
                  (a[2],  funcs[2], None),
                  ("!",  None, None)]
            return m1

        a, funcs = make_menu_str(0)
        m1 = make_menu_list('X', a, funcs)
        a, funcs = make_menu_str(1)
        m2 = make_menu_list('Y', a, funcs)
        m = m1 + m2
        if self.figpage() is not None:
            def onSelTransaxes(evt, obj=holder, gp=self):
                obj.onSelTransaxes(evt, gp)
            if holder.get_figaxes() is None:
                m.extend([("Select Axes...", onSelTransaxes, None), ])
#            m = m + [("Select Axes...",  onSelTransaxes, None)]
        return m

    def get_device_point(self):
        t = self.get_gp_transform(dir='both')
        x1, y1 = self.convert_trans_p((self.x, self.y), t, None)
        return int(x1), int(y1)

    def calc_new_points(self, dx, dy):
        '''
        calculate new x, y for transport of dx, dy
        '''
        x_old = self.x
        y_old = self.y
        x1, y1 = self.get_device_point()
        self.set_device_point(x1+dx, y1+dy)
        x_new = self.x
        y_new = self.y
        self.x = x_old
        self.y = y_old
        return x_new, y_new

    def set_device_point(self, x1, y1):
        t = self.get_gp_transform(dir='both')
        self.x, self.y = self.convert_trans_p((x1, y1), None, t)

    def convert_trans_rect(self, r, t1=None, t2=None):
        n1 = self.convert_trans_p([r[0], r[1]], t1, t2)
        n2 = self.convert_trans_p([r[0]+r[2], r[1]+r[2]], t1, t2)

        w = n2[0][0]-n1[0][0]
        h = n2[0][1]-n1[0][1]
        rect = [n1[0][0], n1[0][1], w, h]
        return rect

    def convert_trans_p(self, p, t1=None, t2=None):
        '''
        it dose 
        1) transfomr to device using t1
        2) transform to new coord by t2.inverted()
        '''
        n1 = np.array([p[0], p[1]]).reshape(1, 2)
        if t1 is not None:
            n1_new1 = t1[0].transform(n1)
            if t1[0] != t1[1]:
                n1_new2 = t1[1].transform(n1)
                n1 = np.array([n1_new1[0][0], n1_new2[0][1]]).reshape(1, 2)
            else:
                n1 = n1_new1
        if t2 is not None:
            n1_new1 = t2[0].inverted().transform(n1)
            if t2[0] != t2[1]:
                n1_new2 = t2[1].inverted().transform(n1)
                n1 = np.array([n1_new1[0][0], n1_new2[0][1]]).reshape(1, 2)
            else:
                n1 = n1_new1
        return n1[0][0], n1[0][1]
