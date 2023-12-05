from __future__ import print_function

import matplotlib
try:
    # matplotlib3 has this option
    matplotlib.set_loglevel("error")
except:
    pass

import ifigure
import matplotlib.cm
import weakref
import shutil
from ifigure.widgets.dlg_preference import PrefComponent
import tempfile
from ifigure.utils.cbook import register_idl_colormaps
from ifigure.utils.pid_exists import pid_exists
import sys
import site
from ifigure.utils.get_username import get_username
from matplotlib.lines import Line2D
from matplotlib.path import Path
from matplotlib.collections import PathCollection
import matplotlib
import re
import os
from os.path import expanduser
import traceback
from distutils.version import LooseVersion

from matplotlib.artist import ArtistInspector

from ifigure.utils.setting_parser import iFigureSettingParser as SP
import ifigure.utils.debug as debug

dprint1, dprint2, dprint3 = debug.init_dprints('ifiure_config')


isMPL2 = LooseVersion(matplotlib.__version__) >= LooseVersion("2.0")
isMPL33 = LooseVersion(matplotlib.__version__) >= LooseVersion("3.3")

if isMPL2:
    # let's use classic for now.
    import matplotlib.pyplot
    matplotlib.pyplot.style.use('classic')

pickle_protocol = 2    

def artist_property_checker(obj, prop, values=None):
    #print('inspecting', obj, prop)
    if values is None:
        values = ArtistInspector(obj).get_valid_values(prop)
    matches = re.findall(r"\'(.+?)\'", values)
    #print('inspector returns ', values)
    #print('checking ...', matches)
    setter = getattr(obj, 'set_'+prop)
    getter = getattr(obj, 'get_'+prop)

    values = []
    matches_ans = []
    for i, p in enumerate(matches):
        try:
            setter(p)
            x = getter()
            values.append(x)
            matches_ans.append(p)
        except:
            dprint2(str(obj)+'do not know how to set ' +
                    prop + ' to ' + p.__repr__())
    #print('object returns...', values)
    return matches_ans, values


ifiguredir = ifigure.__path__[0]
#resourcedir= os.path.join(os.path.dirname(os.path.dirname(ifigure.__path__[0])), 'resources')
resourcedir = os.path.join(ifigure.__path__[0], 'resources')
icondir = os.path.join(resourcedir, 'icon')
home = expanduser("~")
usr = get_username()

rcdir = os.getenv("PISCOPERC", default="")
if rcdir == '':
    rcdir = os.path.join(home, '.ifigure_rc')

# piscope's own package site
# made in .ifigure_rc
# this directory is used to store package/modules used from
# simulation modules

site.USER_SITE = os.path.join(rcdir, '.local', 'site-packages')
site.USER_BASE = os.path.join(rcdir, '.local')
if not os.path.exists(rcdir):
    os.mkdir(rcdir)
if not os.path.exists(site.USER_BASE):
    os.mkdir(site.USER_BASE)
if not os.path.exists(site.USER_SITE):
    os.mkdir(site.USER_SITE)
sys.path.insert(0, site.USER_SITE)
file = os.path.join(site.USER_SITE, '__init__.py')
if not os.path.exists(file):
    fid = open(file, 'w')
    fid.close()
file = os.path.join(site.USER_SITE, 'piscopelib')
if not os.path.exists(file):
    os.mkdir(file)
    file = os.path.join(file, '__init__.py')
    fid = open(file, 'w')
    fid.close()

geom_file = os.path.join(rcdir, 'gui_geom')

usr_template_dir = os.path.join(rcdir, 'template')
if not os.path.exists(usr_template_dir):
    os.mkdir(usr_template_dir)
usr_script_template_dir = os.path.join(usr_template_dir, 'script')
if not os.path.exists(usr_script_template_dir):
    os.mkdir(usr_script_template_dir)

p = SP()
s = p.read_setting('pref.general_config')
if s['root_work_directory'] == '\'default\'':
    #    tempdir_base=os.path.join(tempfile.gettempdir(), 'piscope_'+os.getenv('USER'))
    tempdir_base = os.path.join(tempfile.gettempdir(), 'piscope_'+usr)
    if not os.path.exists(tempdir_base):
        os.makedirs(tempdir_base)
#    tempdir_base=os.path.join(tempdir_base, os.getenv('USER'))
#    if not os.path.exists(tempdir_base):
#        os.mkdir(tempdir_base)
else:
    tempdir_base = os.path.expanduser(s['root_work_directory'])
    tempdir_base = os.path.join(tempdir_base, 'piscope_'+usr)
    if not os.path.exists(tempdir_base):
        os.makedirs(tempdir_base)


crashed_process = []


#
# temporary directory is <hostname>.PID_xxxx
#    we add hostname to the temporary file,
#    in order to avoid deleteing the work directory
#    when the tmporary directory is on the share drive
#    and when a user opens the same project file from
#    more than two different computers
#
#    hostname is taken by using socket.gethostname()
#    if it fails
#    we use a nominal hostname = "HOST"
#
for item0 in os.listdir(tempdir_base):
    item = item0.split('.')[-1]
    if item.startswith('pid'):
        pid = int(item[3:])
        if not pid_exists(pid):
            try:
                dname = os.path.join(tempdir_base, item0)
                for item2 in os.listdir(dname):
                    if item2.startswith('###untitled_') or item2.startswith('.###ifigure_'):
                        f = os.path.join(tempdir_base, item0, item2)
                        shutil.rmtree(f)
                if len(os.listdir(dname)) == 0:
                    try:
                        print(('removing past crush dir', dname))
                        shutil.rmtree(dname)
                    except:
                        print('Failed to remove crush dir')
            except:
                pass

try:
    import socket
    name = socket.gethostname().split('.')[0]
except:
    name = "HOST"
tempdir = os.path.join(tempdir_base, name + '.pid'+str(os.getpid()))

if os.path.exists(tempdir) == False:
    os.mkdir(tempdir)


def tempdir_clean(obj):
    if os.path.exists(tempdir):
        print(('removing tempdir ', tempdir))
        shutil.rmtree(tempdir)


scratch = os.path.join(rcdir, 'ifigure_scratch')
canvas_scratch = os.path.join(rcdir, 'canvas_scratch')
if os.path.exists(canvas_scratch) == False:
    os.mkdir(canvas_scratch)
canvas_scratch_page = os.path.join(rcdir, 'canvas_scratch_page')
if os.path.exists(canvas_scratch_page) == False:
    os.mkdir(canvas_scratch_page)
canvas_scratch_axes = os.path.join(rcdir, 'canvas_scratch_axes')
if os.path.exists(canvas_scratch_axes) == False:
    os.mkdir(canvas_scratch_axes)
vv_scratch = os.path.join(rcdir, 'vv_scratch')
st_scratch = os.path.join(rcdir, 'ifigure_subtree')
pick_r = 10

print('reading extra color maps')
register_idl_colormaps()

#
#   palette data
#
collist = ['blue', 'g', 'red',
           'cyan', 'magenta', 'yellow',
           'black', 'white', 'none', 'grey', 'darkgrey', 'lightgrey']
# collist=['b', 'g', 'r',
#         'c', 'm', 'y',
#         'k', 'w', 'none', 'grey', 'darkgrey' , 'lightgrey']
collistf = ['blue', 'green', 'red',
            'cyan', 'magenta', 'yellow',
            'black', 'white', 'grey', 'darkgrey', 'lightgrey']
markerlist = ['None', '.', ',', 'o', 'v', '^', '<', '>',
              '1', '2', '3', '4', 's', 'p', '*', 'h', 'H', '+', 'x', 'D', 'd',
              '|', '_']
markernames = ['None', 'pint', 'pixel', 'o', 'triangle_down',
               'triangle_up', 'triangle_left', 'triangle_right',
               '1', '2', '3', '4', 's', 'p', '*', 'h', 'H', 'plus', 'x', 'D', 'd',
               'vline', 'hline']

linestylelist = ['None', '-', '--', '-.', ':']
linestylenames = ['None', '-', '--', '-.', 'colon']

linewidthlist = ['1.0', '1.5', '2.0', '2.5', '3.0']

arrowstylename = ["Curve", "CurveB", "BracketB",
                  "CurveFilledB", "CurveA", "CurveAB", "CurveFilledA",
                  "CurveFilledAB", "BracketA", "BracketAB", "Fancy",
                  "Simple", "Wedge", "BarAB"]
arrowstylelist = ["-", "->", "-[", "-|>", "<-", "<->",
                  "<|-", "<|-|>", "]-", "]-[", "fancy",
                  "simple", "wedge", "|-|"]

colormap_from_reference =  [('Perceptually Uniform Sequential', [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis']),
         ('Sequential', [
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']),
         ('Sequential (2)', [
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper']),
         ('Diverging', [
            'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']),
         ('Cyclic', ['twilight', 'twilight_shifted', 'hsv']),
         ('Qualitative', [
            'Pastel1', 'Pastel2', 'Paired', 'Accent',
            'Dark2', 'Set1', 'Set2', 'Set3',
            'tab10', 'tab20', 'tab20b', 'tab20c']),
         ('Miscellaneous', [
            'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
            'gist_rainbow', 'rainbow', 'jet', 'nipy_spectral', 'gist_ncar'])]

colormaplist = sum([x[1] for x in colormap_from_reference],[])

#
#  Artist may not reture the same value as given by setter...
#  Also, matplotlib has a routine to get a list of valid property values.
#  With get_valid_values, it may be possible to implement more automatic
#  property list generation.
#
#  The following is an initial attempt. Needs to check more how well
#  matplotlib is organized in this aspect.

obj = PathCollection(Path.unit_rectangle())
#plinestylelist, plinestyle_rlist = artist_property_checker(obj, 'linestyle')
pedgecolorlist, pedgecolor_rlist = artist_property_checker(
    obj, 'edgecolor', values="'"+"','".join(collist)+"'")
plinestylelist = ['solid', 'dotted', 'dashed', 'dashdot']
plinestyle_rlist = ['solid', 'dotted', 'dashed', 'dashdot']
if isMPL2:
    plinestylelist = plinestylelist[:4]
    plinestyle_rlist = plinestyle_rlist[:4]


def colormap_list():
    return colormaplist


def scratch_file():
    return scratch


def color_list():
    return collist


def color_list_face():
    return collistf


def marker_list():
    return markerlist


def linestyle_list():
    return linestylelist


def linewidth_list():
    return linewidthlist


def plinestyle_list():
    return plinestylelist


def arrowstyle_list():
    return [(arrowstylename[i], arrowstylelist[i]) for i in range(len(arrowstylename))]


class iFigureConfig(PrefComponent):
    setting = None

    def __init__(self):
        PrefComponent.__init__(self, 'General')
        if iFigureConfig.setting is None:
            p = SP()
            iFigureConfig.setting = p.read_setting('pref.general_config')

    def save_setting(self):
        p = SP()
        p.write_setting('pref.general_config', iFigureConfig.setting)

    def get_dialoglist(self):

        s = iFigureConfig.setting
        if s["delbook_on_windowclose"] == 1:
            text = 'no'
        else:
            text = 'yes'
        list = [["Model add-on path", s['usr_addon_dir'], 0, None],
                ["Root work dir. (need restart)", s['root_work_directory'], 200, None],
                ["WikiHelp front", s['wikihelp_front'], 0, None],
                ["WikiHelp base", s['wikihelp_base'], 0, None],
                ["Default keep book in proj", text, 1,
                 {"values": ["yes", "no"]}]]
        hint = ["path to scripts/modules used in models",
                'root directory of temporary work files. ("default": tempfile.gettempdir()/os.getenv(\'USER\'))',
                "wiki front page",
                "wiki base page",
                "Default delete book data when window is closed"]

        return list, hint

    def set_dialog_result(self, value):
        s = iFigureConfig.setting
        if str(value[4]) == 'yes':
            val = 1
        else:
            val = 0
        s["usr_addon_dir"] = str(value[0])
        s['root_work_directory'] = str(value[1])
        s["wikihelp_front"] = str(value[2])
        s["wikihelp_base"] = str(value[3])
        s["delbook_on_windowclose"] = not (val)
