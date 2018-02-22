#
#  Name   :ifigure_app
#
#          main application for a script driven
#          data analysis/visulaization tool
# 
#  Author :
#         Syun'ichi Shiraiwa
#  E-mail :
#         shiraiwa@psfc.mit.edu
#
#
#  History : 
#         An idea of wrting an iScope/COMSOL hybrid (iScope
#         like interface with COMSOL like data management)
#         using python occurred to me during 2011 APS.
#
#         Beginning of "writing" was around Feb. 2012, and
#         it is becoming to have a shape in June.
#
#         This memo is to record the histroy since then.
#
#
#         2012. 05       NetCDF4, Namelist, G-file loading  
#         2012. 06  5-10 FigContour and FigImage was added
#         2012. 06    11 At a farm in west Mass. Custom Picker
#                        starts to work
#               06    15 PyParam became real component
#               06 19-21 ScriptEditor was added to edit script
#               06    21 Compare TreeDicts are added
#               06    26 PySetting, PyScript, reconstructing
#                        package directorys
#                        mto = ModelTreeObject will be used
#                        instead of fig_object
#                     28 Improved keyboard shot cut. SSH subpro
#                        cessing..
#               07    01 fig_text, fig_axspan, fig_axline 
#               07    02 mdstree add_on was rebuilt 
#                        + many bug fix...
#               07    04 many interactive palettes are doen. 
#                        still need to add more object, 
#                        but an infrastruture
#                        is almost okey.
#               07 09-13 trip to San-Diego
#               07 13-20 cleaning on main gui code
#               08   -23 solver (std, parametric, optimizer)         
#                        solution folder was added
#                        pyro_ssh
#                        font style panel
#                        partial implementation of undo/redo
#                        partial implementation of load/save subtree
#               08 27-28 switch to dictionary to represent "contents"
#                        enhancement in interactive command (nsec, isec, cls..)
#                        genray_cql3d.pfz seems to work now.
#               09 02-03 thread monitor
#                  04    edge drag in section editor
#               Oct.     various works relating to annotation)
#               11 08    mdsscope first version was added
#               11 30    WxAgg_Mod attempt to speed up mdsscope
#                        The idea is to treat each axes as separate
#                        image layer.
#               12 01-05 client mode (remote interactive command) 
#               12 06-12 bug fix in history
#                        change text to use gp
#                        legend
#          2013 01 07    format version 2
#               01 07-   revising axis
#               02 22-28 many minor improvement to make GUI behave right
#                        during KSTAR conference
#               03 01-10 add nomargin, global fontsize setting, grid
#                        range reset by double click
#               03 11    fig_fill was added
#               03 23    Implementation of scope is going on.
#                        Things starts to work. But, still need to touch
#                        to make details right. 
#                  24    Panels are improved to behave as if side panels
#                        are hidden closet...It was made to avoid resize
#                        event,,, but somehow on linux it keep resizing....
#                  25    wheel page scroll
#                        no margin mode
#                  26    configuration file management (setting_parser)
#                  28    common axis plot (bottom and left)
#                        equal space axis
#                  29    working on cursor mode 
#                        1) standard cursor(done)
#                        2) tracking cursor(done)
#                        3) contour cursor (done)
#                        4) image cursor (done)
#               04 01    5) slice viewer (done)
#                        6) navigation string (done)
#                        7) object generation...(need to fix other things 
#                           first..)
#               04 02-   cleaning interface of figobjs
#                            FigPlot, FigContour, FigImage, FigAxline, 
#                            FigAxspan, FigFill, FigSpline
#               04 03    3D mode ver. 0.1
#                        FigSurface is added
#               04 15    Modifing to handle ScalarMappable object in more
#                        natural way
#               04 19    Improving MDSScope and other interface behaviors...
#               04 23    Decimation of large array to save time and memory.
#               04 26    Help system (C-Mod wiki)
#               05 02    Improve range setting GUI
#               05 28    option to save book file as separate file
#               05 29    alpha panel, rotation panel improved
#               05 31    support contour/image in MDSScope
#                        add scope file generation from TreeBrowser
#                        add abort loading of MDSScope 
#               06 03    surpport surface in MDSScope
#                        mail graphics
#               07 15    minor improvements to section editor, custom_sliders
#               08 05    started macport version
#                        figure() now does now show property at beginning
#                        bookviewer needs to be called with "show_prop = True"
#                        to change the initial setting
#               08 24    still working on compatibility of wx2.9
#                        DnD on MacOS is in question
#               09 19    Working on twinx and twiny
#                  25    still working on twinx/y
#               10 02    axes artists panel is modified, so that it does not
#                        make the panel from scratch everytime.
#               10 05    fig_axes::color_cycle_reset is added. 
#                        cla() by default will reset color cycle 
#                        still working on twinx/twiny
#               10 15    cycle windows by F1, F2 keys
#                        general panel in preference dialog
#               10 18    upgraded 2.9.5 DnD is fixed.
#               10 22    export to client is done
#               10 27    improving mdsscope, mdsconnect is added.
#                        partial loading is also added
#                        current shot ('c') was added
#                        single worker modes were added
#               10 30    fixed the problem of column width ov variable viewers
#              -11 18    fixed many things before and during APS
#               11 19    Version 2.
#                            files does not have owndir
#                            better command history
#                            new model tree flow control
#                            simplified solver scripts
#                            mdscoonect should have connection mode (done)
#                            about box
#                            (some plan)
#                               app-wide default values
#                               keyboard combination
#                               model template
#                               user script directory
#                               how do I make a subtree/model repository?
#               11 26    py_script is enhanced to support
#                            Run
#                            Run with arguments
#                            model, param, and so on
#                        Perhaps I have all machinary implemented to do
#                        modeing.
#                        I still need to implement some decorative stuff,
#                        helper/assistance. But, it is the time to implement
#                        models...
#               12 02    first TSC parametric scan is running
#                        working on GNERAY/CQL3D interface for loki 
#                        fixed the problem in script editor when project is
#                        renamed.
#               12 03    improving mdsscope
#                          dynamic evaluation of shot number
#                          optimize MDSplus session job generation
#                          fixed bug around reset_private()
#               12 06    saving multi-page pdf file
#                        parameter overwritten is now indecated in variable viewer
#               12 09    working on speeding up mdsscope
#                           decimation is fixed
#                           multiprocessing workers now work
#               12 31    recovery from crash
#                        broken link in history
#                        revised undo/redo menu
#                        copy/paste special..
#                        move tar.gzipping while saving project to MP
#
#          2014 01 07    * reconstructing range adjustment 
#                        * add multipage range adjustment is added
#                        * xauto/yauto/zauto/cauto is added in interactive.py
#                        * fixed copy/paste axes objects
#                        * update script in sol now create PyScript if a PyScript
#                        object does not exist at the corresponding place in
#                        PySol.
#                        * specgram in ifigure.interactive
#                        * marker edge width in FigPlot
#               01 15    * many fixes of user interaction
#                        * merged a-mode and p-mode 
#               01 22    * save w/o data (or artists) in fig_mds
#               01 29    * auto grid on/off in mdsscope
#                        * fixed samex_autoy
#                        * auto scale add small space outside the computed range
#                        * shot number history in mdsscope
#                        * mdsscope panel update is fixed
#                        * autogrid, plot_mode is added in mdsscope/fig_mds
#                        * auto scale axis margin is added in axes
#                        * dpi for image in advancd_config
#                        * rasterized is added to FigObj
#                          FigContour, FigImage, FigPlot, FigAxline, FigAxspan apply
#                          rasterized when it generates artists
#               02 02    * isolate interactive mode and mdsscope           
#                        * mdsevent_listener
#               02 09    * opened book and book geometries are saved, when
#                          projects are saved.
#                        * fig_triplot is remade and now it allows to 
#                          change colors. It won't save color and so on,
#                          fixing which requires to cleaing fig_obj
#                          property saving scheme.
#               02 25    * rewrite MDSscope to improve data loading loop done?
#                        * rewrite interactives to point bookviewer methods.
#               03 01    * added undo/redo in seciton editor
#               03 10    * fig_plotc and fig_axlinec are added.
#                          completed components for kefit_gui.
#                  18    * close command
#                        * fixed decimation
#                        * fixed some interactive commands 
#                          which was broken due to interactive method 
#                          addition (twinx, twiny, specgram,,,)
#               03 27    * parent class of FigObj was changed to TreeDict from PyScript
#                        * addtional tree browser menu for ScriptLink
#                  28    * _suppress is now correctly restored
#                        * working on genray_cql3d_cmod
#               04 01    * forked dev3 branch
#                        ** this branch test if tempfile.tempdir can be used for 
#                           temporary directory
#               04 06    * section editor is merged as layout editor mode
#                        * tempraroy directory auto delete
#                        * icons to range menu items
#                        * working on hg_exclude ...
#               04 21    * eliminated nodraw_on and unified to use a new 
#                          draw_later, which automatically eliminate requests
#                          issued before the last screen update
#                        * fixed zorder bottom
#                        * added BookViewerInteractive::update
#               05 18    * updating solvers
#                        * UPDATE_UI_PROCESS_SPECIFIED is added to reduce
#                          uievents to reduce idle time CPU load?
#               06 05    * improved resize event
#                        * order of drawing is changed to fix the problem of 
#                          object using gp_points
#                        * fig_arrow picker is fixed to address strange
#                          results of a.contains for a paricular arrow head type
#                        * fixed the problem when ifigure.mdsplus does not exists.
#                        * addressed the resizing of aspect = 'equal' object
#                        * colorbar move/resize is now undoable
#                        * undo/redo of the second and third panel of section editor
#                          is finished
#               06 12    * multithread version of mdsplsu worker is added
#                        ** uses thin client (MDSplus.connection) to read data from sever
#                        ** Direct connection (MDSplus.tree) is not thread-safe and can be 
#                        ** used in MP worker mode
#                        ** mdsevent is still done by non-thin client, but can be turn off
#                        ** from menu
#                        ** this mode eliminate the overhead of transfering data from child
#                        ** processes to the main process, realizing a significant preformance
#                        ** boost.
#               mid 06   * moved to HG repository
#                        ** update log is moved to piscope.psfc.mit.edu
#                        ** this log will be edited less frequently 
#
#               07 16    * first preview at C-Mod Science Meeting
#               07 17    * stepplot support to fig_mds
#               
#               09 03    * another attempt to make nonalias mode work, which failed..
#                        ** probably it is better to make a setup script
#                        ** which take care of installing all dependencies using macport.
#
#  Setup for macports
#      install py27-wxpython (port command)
#      install matplotlib (port command)
#      install scipy (port command)
#      install py-netcdf4 (port command)
#      install pypdf2
#      install py27-pdfrw (port commnad)

#import wxversion
#wxversion.ensureMinimal('2.8')
import wx
#import wx.py, wx.lib
#

import sys, shutil, os, tarfile, collections, logging, threading
import cPickle as pickle

from numpy import arange, sin, pi
import ifigure

###
### application global
###
ifigure._cursor_config = {}   ### cursor configuration 
                              ### populated in load_pref
ifigure._visual_config = {}
#                         {'1dcolor1': 'red',
#                          '1dcolor2': 'blue',
#                          '1dalpha' : 0.5,           
#                          '1dthick' : '1.0',           
#                          '2dalpha' : 0.7,
#                          '2dcolor' : 'grey',
#                          'format' : '{:.2e}'}
ifigure._cursor_book = None   ### specail book for slice cursor

redirect_std = False
#
#  debug setting
#
import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('iFigureApp')

from ifigure.utils.mp_tarzip import MPTarzip
import ifigure.events
from ifigure.widgets.canvas.ifigure_canvas import ifigure_canvas
from ifigure.widgets.property_editor import property_editor
from ifigure.widgets.proj_tree_viewer_aui import ProjTreeViewer
from ifigure.widgets.simple_shell import SimpleShell, FakeSimpleShell
from ifigure.widgets.panel_checkbox import PanelCheckbox
from ifigure.widgets.script_editor import ScriptEditor
from ifigure.widgets.consol import Consol
from ifigure.widgets.command_history import CommandHistory
from ifigure.widgets.logwindow import Logwindow
from ifigure.widgets.tipwindow import Tipwindow
from ifigure.widgets.statusbar import StatusBar
from ifigure.widgets.redirect_output import RedirectOutput
from ifigure.widgets.book_viewer import BookViewerFrame, BookViewer
#from ifigure.mdsplus.mdsscope import MDSScope
import ifigure.widgets.dialog as dialog
from ifigure.mto.treedict import TopTreeDict
from ifigure.mto.treelink import TreeLink
from ifigure.mto.project_top import ProjectTop
from ifigure.mto.fig_book import FigBook
from ifigure.mto.fig_page import FigPage
from ifigure.mto.fig_axes import FigAxes
from ifigure.mto.fig_obj import FigObj
from ifigure.mto.py_code import PyModel
from ifigure.mto.py_file import PyText
from ifigure.widgets.undo_redo_history import GlobalHistory,UndoRedoHistory
from ifigure.utils.postoffice import PostOffice
from ifigure.ifigure_config import iFigureConfig
from ifigure.utils.helper_app import HelperApp
from ifigure.widgets.advanced_config import AdvancedConfig
from ifigure.widgets.appearance_config import AppearanceConfig


import ifigure.utils.cbook as cbook
import ifigure.server
import wx, sys, weakref, time
from ifigure.utils.wx3to4 import PyDeadObjectError, menu_Append

try:
    from wx import glcanvas
    haveGLCanvas = True
except ImportError:
    haveGLCanvas = False

try:
    # The Python OpenGL package can be found at
    # http://PyOpenGL.sourceforge.net/
    from OpenGL.GL import *
    from OpenGL.GLUT import *
    haveOpenGL = True
except ImportError:
    haveOpenGL = False

class WindowList(list):
   def get_list(self):
       ret = [item() for item in self if item() is not None]
       self = [item for item in self if item() is not None]
       return ret
   def add_item(self, item):
       self.append(weakref.ref(item))
   def get_next(self, current):
       ret = self._get_valid_item()
       self._validate_ref()
       id = ret.index(current)+1
       if id >= len(self): id = 0
       return self[id]()
   def get_prev(self, current):
       ret = self._get_valid_item()
       self._validate_ref()
       id = ret.index(current)-1
       if id < 0: id = len(self)-1
       return self[id]()
   def _get_valid_item(self):
       self._validate_ref()
       ret = [item() for item in self]
       return ret
   def _validate_ref(self):
       # check for wx4
       ret =  [item for item in self if item() is not None]
       self[:] = [item for item in ret if item()]
       # check for wx3       
       ret =  [item for item in self if item() is not None]       
       self[:] = [item for item in ret if isinstance(item(), wx.Window)]       

class  CanvasPanel(wx.Panel):
   pass
class  EditorPanel(wx.Panel):
   pass

ID_DETACH_EDITOR = wx.NewId()
ID_SAVEDOC = wx.NewId()
ID_SAVEASDOC = wx.NewId()
ID_RECENT = wx.NewId()
    
from collections import deque
RECENT_FILE = deque(['']*10, 10)
class ifigure_app(BookViewerFrame):
    def __init__(self, parent, title, noPyShell = False, hide = False,
                 launcher_file = None   ):

       self.windowlist = WindowList()
       self.appearanceconfig = AppearanceConfig()
       
       super(ifigure_app, self).__init__(parent, 
                   title=title, size=(10,10), 
                   style = wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | 
                           wx.RESIZE_BORDER | wx.SYSTEM_MENU | 
                           wx.CAPTION | wx.CLOSE_BOX |
                           wx.CLIP_CHILDREN)

       self._launcher_file = launcher_file
       logging.basicConfig(level=logging.DEBUG)
       self.stdfiles = (sys.stdout, sys.stderr)
       self._text_clip=''
       self.timer = None
       self.remote_lock = threading.Lock()
       self.viewers = [self] # list of fig viewers
       self._aviewer =  self

       self.ipage=-1
       self.book = self.make_empty_project()
       self.load_pref()
       self.InitUI(parent, title, noPyShell=noPyShell)
       
       self.BindTreeDictEvents()
       self.BindPVCVEvents()
#       self.Bind(ifigure.events.TD_EVT_NEWHISTORY, self.onNewHistory)
       self.shell.set_proj(self.proj)
       
       self.set_filename_2_window_title()
       self.logw = Logwindow(self, wx.ID_ANY, 'log')
#       self.logw.redirector = RedirectOutput(sys.stdout)
       self.tipw = Tipwindow(self, wx.ID_ANY, 'Command help')
       self.shell.set_tipw(self.tipw)
       self.hdf_export_window = None
       
       if redirect_std:
           self.redirector = RedirectOutput(self.proj_tree_viewer.consol.log,
                                            self.proj_tree_viewer.consol.log)
#           sys.stdout = redirector
#           sys.stderr = redirector
       else:
           self.redirector = RedirectOutput(sys.stdout, sys.stderr)     
       self.redirector.turn_on() ### doesn't do anything if not redirect_std
       self.logw.set_redirector(self.redirector)

       ### these are preference components
       self.po = PostOffice().set_parent(self)
       self.config = iFigureConfig()
       self.helper = HelperApp()
       self.aconfig = AdvancedConfig()
       self.aconfig.add_user_path()

       dx, dy = wx.GetDisplaySize()
       msx, msy=self.GetSize()
       if msy>dy: msy = dy-50
       if msx>dx: msy = dx-50
       self.SetSize((msx, msy))
       self.Layout()
       self.Centre()
       if not hide:  
          wx.CallAfter(self.Show, True)
          wx.CallAfter(self.Raise)
          wx.CallAfter(self.proj_tree_viewer.get_shellvar_viewer().update, self.shell)

#       self.Show()
#       self.Raise()       

#       spx, spy=self.GetScreenPosition()
#       if spx < 40: spx = 40
#       if spy < 40: spy = 40

#       def onidle(evt):
#           print 'onidle'
#       self.Bind(wx.EVT_IDLE, onidle) 

    @property
    def aviewer(self):
        return self._aviewer
    @aviewer.setter
    def aviewer(self, value):
        self._aviewer = value
        if value is not None:
            if not value.isinteractivetarget: return
        from ifigure.interactive import set_aviewer
        set_aviewer(self._aviewer)

    def get_components(self):
        return [self.config, self.appearanceconfig, self.po, self.helper, self.aconfig]

    def load_pref(self):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP()
        names = ['cursor_config', 'visual_config']
        for name in names:
           var = p.read_setting('pref.'+name)
           d = getattr(ifigure, '_'+name)
           for key in var: d[key] = var[key]

    def save_pref(self):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP()
        names = ['cursor_config', 'visual_config']
        for name in names:
           d = getattr(ifigure, '_'+name)
           p.write_setting('pref.'+name, d)

    def InitUI(self, parent, title, noPyShell=False):  
       # A Statusbar in the bottom of the window
       self.sb = StatusBar(self)
       self.SetStatusBar(self.sb) 

       ## define splitter panel tree

       ## valid panel p1, p22, p121, p122
       self.gui_tree = PanelCheckbox(self, wx.VERTICAL)
       p1, p2 = self.gui_tree.add_splitter('v', 'h')
       p21, p22 = p2.add_splitter('h', 'h')
       p211, p212 = p21.add_splitter('v', 'h')

       ## make all panels
       self.proj_tree_viewer = p1.add_panel(ProjTreeViewer, 
                               "Project", "Project", 0, 'l',
                               1, wx.ALL|wx.EXPAND, 0)
       if noPyShell:
           shell = FakeSimpleShell
       else:
           shell = SimpleShell
       self.shell = p22.add_panel(shell,
                                  "Shell", "Shell", 1, 'b',
                                   1, wx.ALL|wx.EXPAND, 0)


       self.panel2 = p211.add_panel(EditorPanel,
                               "Editor", "Editor", 2, False, 
                               1, wx.ALL|wx.EXPAND,0 )
       self.panel2.SetSizer(wx.BoxSizer(wx.VERTICAL))
       self.make_attached_script_editor()
       self.panel1 = p212.add_panel(CanvasPanel,
                                    "Figure", "Figure", 3)
       p212.set_primary(self.panel1)
       self.property_editor = p212.add_panel(property_editor,
                              "Property", "Property",
                              4, 'r', 0, wx.ALL|wx.EXPAND, 0)
       #self.gui_tree.hide_toggle_menu(self.panel1)
       #self.gui_tree.hide_toggle_menu(self.property_editor) 
       ch = self.proj_tree_viewer.get_command_history() 
       self.shell.set_command_history(ch)
       #self.script_editor.Hide()
       self.canvas=None
       self._rebuild_ifigure_canvas()
       self._link_canvas_property_editor()
       self.gui_tree.primary_client(self.canvas)
       

       # File Menu
       newmenu = wx.Menu()
       menu_Append(self.filemenu, wx.ID_ANY, 'New', newmenu)
       self.add_menu(newmenu, wx.ID_ANY, 
                     "piScope", "Start new piScope application", 
                     self.onNewApp)
       self.add_menu(newmenu, wx.ID_ANY, 
                     "Project", "Create new project", 
                     self.onNew)
       self.add_menu(newmenu, wx.ID_ANY, 
                     "Figure", "Create new book and open it in a new viewer", 
                     self.onNewBook)
       self.add_menu(newmenu, wx.ID_ANY, 
                    "Script", "Create new script in project", 
                     self.onNewScript)
       self.add_menu(newmenu, wx.ID_ANY, 
                     "Text", "Create new text in project", 
                     self.onNewFile)
       self.add_menu(newmenu, wx.ID_ANY, 
                     "non-project Text", "Create new untitled text (file is not stored in project)", 
                     self.onNewDoc)
       openmenu = wx.Menu()
       menu_Append(self.filemenu, wx.ID_ANY, 'Open', openmenu)
       self.add_menu(openmenu, wx.ID_ANY,
                     "Project...", "Open an existing project", 
                     self.onOpen)
       self.add_menu(openmenu, wx.ID_ANY,
                     "Project in new piScope...", "Open an existing project in new piscope", 
                     self.onOpenInNewpiScope)
       self.add_menu(openmenu, wx.ID_OPEN,
                     "Book ...",
                     "Import book file (.bfz). Current book is deleted from project", 
                     self.onLoadBook)
       self.add_menu(openmenu, wx.ID_ANY,
                     "Book in new window...",
                     "Import Book file (.bfz), New book data will be added to project",
                     self.onLoadBookNew)
       self.add_menu(openmenu, wx.ID_ANY,
                     "Script...", "Open Script", 
                     self.onOpenScript)
       self.add_menu(openmenu, wx.ID_ANY,
                     "File...", "Open File", 
                     self.onOpenFile)
       self._recentmenu = wx.Menu()
       menu_Append(self.filemenu, ID_RECENT,
                                "Open Recent", self._recentmenu)
       self.filemenu.AppendSeparator()
       self.append_save_project_menu(self.filemenu)
#       self.save_project_menu = self.add_menu(
#                     self.filemenu, wx.ID_ANY, 
#                     "Save Project", "Save Project", 
#                     self.onSave)
#       self.update_save_project_menu(False)
#       self.add_menu(self.filemenu, wx.ID_SAVEAS, 
#                     "Save Project As...", "Save Project", 
#                     self.onSaveAs)
       self.add_menu(self.filemenu, ID_SAVEDOC, 
                     "Save Document", "Save current editor document", 
                     self.onSaveDoc)
       self.add_menu(self.filemenu, ID_SAVEASDOC, 
                     "Save Document As...", 
                     "Save current editor document in a different file", 
                     self.onSaveAsDoc)
#       self.add_menu(self.filemenu, wx.ID_ANY, 
#                     "Close Project", "Close Project", 
#                     self.onCloseProject)
       self.add_menu(self.filemenu, wx.ID_ANY, 
                     "Preference...", "Preference", 
                     self.onAppPreference)
       self.filemenu.AppendSeparator()
       self.export_book_menu = self.add_menu(self.filemenu, 
                     BookViewerFrame.ID_EXPORTBOOK, 
                     "Export Book", "Export Book", 
                     self.onExportBook)
#       self.export_book_menu.Enable(True)
       self.add_menu(self.filemenu, 
                     BookViewerFrame.ID_EXPORTBOOK_AS, 
                     "Export Book As...", "Export Book", 
                     self.onExportBookAs)
       self.add_saveimage_menu(self.filemenu)
       self.filemenu.AppendSeparator()
       self._figure_mnis = [self.add_menu(self.filemenu, wx.ID_ANY, 
                                              "Close Figure", "Close figure", 
                                              self.onCloseFigure),]
#                                 self.add_menu(self.filemenu, wx.ID_ANY, 
#                                              "Close Figure + Delete Book", 
#                                    "Close figure and delete book data", 
#                                        self.onCloseFigureDeleteBook)]
       self.filemenu.AppendSeparator()
       self.add_quitemenu(self.filemenu)
#       self.add_menu(self.filemenu, wx.ID_ANY,
#                     "Quit piScope"," Terminate the program", 
#                     self.onQuit)
       self.Bind(wx.EVT_CLOSE, self.onAppWindowClose)
       #plot menu
#       self.plotmenu = wx.Menu()
#       self.menuBar.Append(self.plotmenu,"Plot")
       self.add_std_plotmenu(self.plotmenu)
       # help menu
       self.append_help_menu()

       # Edit Menu
       self.append_undoredo_menu(self.editmenu)
       self.editmenu.AppendSeparator()

       self.add_cutpaste_menu(self.editmenu)

       panelmenu = wx.Menu()
       menu_Append(self.viewmenu, wx.ID_ANY, 'Panels', panelmenu)
       self.gui_tree.append_menu(panelmenu)
       self.viewmenu.AppendSeparator()
       self.gui_tree.update_check()
       self.gui_tree.bind_handler(self)

       self.gui_tree.set_splitters()

       self.editmenu.AppendSeparator()
       self.add_bookmenus(self.editmenu, self.viewmenu)
       self.viewmenu.AppendSeparator()
       x = self.add_menu(self.viewmenu, wx.ID_ANY,
                     "Detach Figure"," Detach figure and show it in a separate window", 
                     self.onDetachFigure)
       self._figure_mnis.append(x)
       self.add_menu(self.viewmenu, ID_DETACH_EDITOR,
                     "Detach Editor"," Detach editor in a separate window", 
                     self.onDetachEditor)

       self.append_std_viewmenu2(self.viewmenu)
#       self.editmenu.AppendSeparator()
#       self.append_undoredo_menu(self.editmenu)
       self.editmenu.AppendSeparator()
       self.add_menu(self.editmenu, wx.ID_ANY,
                     "Clear history","Clear command history panel",
                     self.onClearCommandHistory)
#       self.add_menu(self.editmenu, wx.ID_ANY,
#                     "MP","testing mp",
#                     self.onMP)
#       self.add_menu(self.editmenu, wx.ID_ANY,
#                     "MP End","testing mp",
#                     self.onMPEnd)

       self.helpmenu.AppendSeparator()
       self.add_menu(self.helpmenu, wx.ID_HELP, 
                     "About...","About this program", 
                     self.onAbout)

#       self.SetMenuBar(self.menuBar)  
       # Adding the MenuBar to the Frame content.
       #aTable = wx.AcceleratorTable([(wx.ACCEL_CTRL,  ord('Z'), wx.ID_UNDO),
       #                (wx.ACCEL_CTRL|wx.ACCEL_SHIFT, ord('Z'), wx.ID_REDO),
       #                ])
       #self.SetAcceleratorTable(aTable)

#       self.Layout()

       self.panel2.Hide()
       self.gui_tree.hide_toggle_menu(self.panel2)
       self.gui_tree.rebuild_menu()

       self.SetSize([800, 500])
       self.gui_tree.update_check()       
       self.gui_tree.set_splitters()
       self.Layout()
       size=self.GetSize()
       self.gui_tree.set_sashposition([200, size[1]-100, 300])
       self.property_editor.set_sizehint()

 #      if os.path.exists(geom_file):
       try:
           val = self.read_geom_file()
#           from ifigure.ifigure_config import geom_file
#           fid=open(geom_file, 'r')
#           val=pickle.load(fid)
#           fid.close()
           if "editor_detached" in val:
#               print 'editor_detached', val["editor_detached"]
               self.script_editor._first_open_style = val["editor_detached"]
       except:
           self.book.set_open(True)
       else:
           val["sh"][1]=False ## this is to hide script editor

           # safe guard in case size is zero...
           val["size"][0] = max(( val["size"][0], 300))
           val["size"][1] = max(( val["size"][1], 300))           
           self.SetSize(val["size"]) 
           self.gui_tree.set_showhide(val["sh"])
           self.gui_tree.update_check()
           self.gui_tree.set_splitters()

           self.CenterOnScreen()


           self.Layout()
           self.gui_tree.set_sashposition(val["pos"])
#           self.property_editor.set_sizehint()

           if not val["sh"][2]: 
#               self.close_figurebook()
               self.onCloseFigureDeleteBook()               
           else:
               self.aviewer = self
               self.book.set_open(True)
           if 'RECENT_FILE' in val:
              for item in val['RECENT_FILE']:
                  if not item in RECENT_FILE and os.path.exists(item):
                      RECENT_FILE.append(item)

       self.proj_tree_viewer.update_widget()
       self.set_accelerator_table()                

       from ifigure.widgets.taskbar import TaskBarIcon
       self.tbicon = TaskBarIcon(self)

    def onUpdateUI(self, evt):
        if evt.GetId() == ID_DETACH_EDITOR:
            if (self.script_editor.GetTopLevelParent() == self and
                self.gui_tree.get_toggle(self.panel2)):
                evt.Enable(True)
            else:
                evt.Enable(False)
        elif evt.GetId() == ID_RECENT:
            m = self._recentmenu
            for item in m.GetMenuItems():
                m.DestroyItem(item)
            evt.Enable(True)
            mm = []
            self.read_recent_files()
            for item in RECENT_FILE:
                if item == '': continue
                def dummy(evt, file = item):
                    self.onOpen(None, path = file)
                    evt.Skip()
                mm.append((#os.path.basename(item),
                           item,
                          'Open '+ item,
                           dummy))
            if len(mm) > 0:
                for a,b,c in mm:
                     mmi = self.add_menu(m, wx.ID_ANY, a, b, c)
                m.AppendSeparator()
                mmi = self.add_menu(m, wx.ID_ANY, 'Reset Menu', 'Reset recent file menu', self.onResetRecent)
            else:
                evt.Enable(False)
        elif evt.GetId() == wx.ID_UNDO:
           fc=self.FindFocus()
           if isinstance(fc, wx.stc.StyledTextCtrl):
               evt.SetText('Undo text edit')
           else:
               self.history.update_menu_item()
        elif evt.GetId() == wx.ID_REDO:
           fc=self.FindFocus()
           if isinstance(fc, wx.stc.StyledTextCtrl):
               evt.SetText('Redo text edit')
           else:
               self.history.update_menu_item()
        elif evt.GetId() == ID_SAVEDOC:
           fc=self.FindFocus()
           if fc in self.script_editor.page_list:
               a, b =  self.script_editor.check_if_need_save(fc)
               if a :
                   evt.Enable(True)
               else:
                   evt.Enable(False)
           else:
               evt.Enable(False)
        elif evt.GetId() == ID_SAVEASDOC:
           fc=self.FindFocus()
           if fc in self.script_editor.page_list:
               evt.Enable(True)
           else:
               evt.Enable(False)
        else:
            return super(ifigure_app, self).onUpdateUI(evt)
        
    def BindPVCVEvents(self):
        self.Bind(ifigure.events.PV_EVT_DrawRequest,
                 self.onPV_DrawRequest)
        self.Bind(ifigure.events.PV_EVT_AddFigobj,
                 self.onPV_AddFigobj)
        self.Bind(ifigure.events.PV_EVT_DeleteFigobj,
                 self.onPV_DeleteFigobj)
        self.Bind(ifigure.events.CV_EVT_CanvasSelected,
                 self.onCV_CanvasSelected)
        self.Bind(ifigure.events.REMOTE_COMMAND,
                 self.onRemoteCommand)
        self.Bind(ifigure.events.TD_EVT_UNDO,
                 self.onTD_EvtUndo)
        self.Bind(ifigure.events.TD_EVT_REDO,
                 self.onTD_EvtRedo)
        self.Bind(ifigure.widgets.simple_shell.EVT_SHELL_ENTER,
                 self.onShellEnter)
        self.Bind(ifigure.events.TD_EVT,
                 self.onTD_Evt)
        self.Bind(ifigure.events.TD_EVT_FILESYSTEMCHANGED, 
                  self.onFileSystemChanged)
        self.Bind(ifigure.events.TD_EVT_PAGESHOWN, 
                  self.onTD_PageShown)
        self.Bind(ifigure.events.TD_EVT_CLOSEBOOKREQUEST, 
                  self.onTD_CloseBookRequest)
    def onFileSystemChanged(self, evt=None):
        self.script_editor.onFileSystemChanged(evt)
    #
    #  File Menu
    #    
    def onResetRecent(self, evt):
        for i in range(len(RECENT_FILE)): RECENT_FILE.append('')
        self.write_recent_files()

    def onExportBook(self, evt):
        self.onSaveBook(evt)
    def onExportBookAs(self, evt):
        self.onSaveBookAs(evt)
    def onNewBook(self, evt, veiwer=None):
        from ifigure.widgets.book_viewer import BookViewer
        super(ifigure_app, self).onNewBook(evt, 
                                           viewer = BookViewer, proj=self.proj)
    def onLoadBook(self, evt, mode=0, proj=None):
        if self.book is None:
           bk = super(ifigure_app, self).onLoadBook(evt, mode=1, 
                                       proj=self.proj)
           if bk is not None:
               self.open_book_in_appwindow(bk)
        else:
           super(ifigure_app, self).onLoadBook(evt)
    def onLoadBookNew(self, evt, viewer=None, proj=None):
        from ifigure.widgets.book_viewer import BookViewer
        super(ifigure_app, self).onLoadBookNew(evt, 
                                       viewer = BookViewer,
                                       proj=self.proj)
    def onOpen(self, e=None, path = None):
        from ifigure.utils.mp_tarzip import lc
        if not lc.acquire(False):
            ret=dialog.message(self, 'Save job is running.','Please wait', 0)
            return
        lc.release()
        if path is None:
            path = dialog.read(parent = self,  message="Select project (.pfz) to open",
                               wildcard='*.pfz')
        if path != '':
           call_close = (self.proj is not None)
           if not self.open_file(path, call_close=call_close): return
           self.deffered_force_layout()
           self.set_proj_saved(True)
           
    def get_file_helper_command(self, path):
        from ifigure.utils.setting_parser import iFigureSettingParser as SP
        p = SP().set_rule('file', 
                          {'name':'', 'ext':'', 'action':'',
                           'action_txt':'', 'use':False})
        var = p.read_setting('pref.file_helper')
        import os
        path = os.path.expanduser(path)
        basepath = os.path.basename(path)
        import re
        for x in var['file']:
            try:
               rule = x['ext']
               p = re.compile(rule)
            except:
               print('compile error of regular expression: ' + rule)
            if p.match(basepath) is not None:
                if not x['use']: continue
                command = x['action']
                command = command.replace('{1}', '"'+path+'"')
                command = command.replace('{top}', 'proj')
                return command
        return ''
    
    def onOpenWithHelperCommand(self, e=None, path = None, hide_main = False):
        command = self.get_file_helper_command(path)
        if command != '':
#            self.shell.lvar['command'] = command
            wx.CallAfter(self.shell.Execute, command)
            wx.CallAfter(self.proj_tree_viewer.update_widget)
            if hide_main:
                wx.CallAfter(self.goto_no_mainwindow)
                
    def onOpenInNewpiScope(self, e):
        path = dialog.read(parent = self,
                           message="Select project (.pfz) to open in new piScope application",
                           wildcard='*.pfz')
        if path != '':
            import piscope, subprocess, shlex
            import ifigure.widgets.canvas.ifigure_canvas
            options = ' '
            if not ifigure.widgets.canvas.ifigure_canvas.turn_on_gl:
               options = options + '-g '
            if redirect_std:
               options = options + '-d '                
            command = sys.executable + ' ' + piscope.__file__ + options  + path
            if os.altsep is not None:
               command = command.replace(os.sep, os.altsep)

            self.redirector.turn_off()
            p=subprocess.Popen(shlex.split(command))
#                           shell = True)
#                           stdout=subprocess.PIPE)
            self.redirector.turn_on()
           
    def open_file(self, file, call_close=False): 
        tmp_top = TopTreeDict(); tmp_top.set_app(self)
        proj=tmp_top.LoadFromFile(file, sb = self.sb)
        if proj is None:
           print("file load error")
           return False
        if call_close:
           self.onCloseProject() 

        self.read_recent_files()     
        if not file in RECENT_FILE: 
            RECENT_FILE.append(file)
            self.write_recent_files()

        self.Freeze()

        self._set_proj(proj)

        #        if (proj.pbook is not None and
        #            proj.pbook.num_page() != 0):
        #           self.book = proj.pbook
        #           self.ipage=0
        #           self.show_page(0)
        #           self.proj_tree_viewer.update_widget()

        ### open previously opend files
        from ifigure.mto.treedict import str_td
        wdir=self.proj.getvar('wdir')
        dot_file=os.path.join(wdir, '.opened_file')
        file_count = 0
        if os.path.exists(dot_file):
            fid=open(dot_file, 'r')
            for name in fid.readlines():
               file = name.strip('\n').split('\t')[0]
               file=os.path.join(wdir, file)
               # note: if file is absolute path, wdir is ignored
               if not os.path.exists(file):continue
               if len(name.strip('\n').split('\t')) == 2:
                   file = str_td(file)
                   file.td = name.strip('\n').split('\t')[1]
               ifigure.events.SendEditFileEvent(self.proj,
                                             w= self,
                                             file=file)
               file_count = file_count + 1
            fid.close()
        if file_count == 0:
            # close editor if it is shown
            if not self.isEditorAttached():
                self.attach_editor(open_editor=True)
            self.gui_tree.set_showhide([False], self.panel2)
            self.gui_tree.show_toggle_menu(self.panel2)
            self.gui_tree.rebuild_menu()
            self.gui_tree.update_check()
            self.gui_tree.set_splitters()

        dot_file=os.path.join(wdir, '.command_history')
        if os.path.exists(dot_file):
           self.proj_tree_viewer.ch.loadfromfile(dot_file)

        ### 
        self.load_gui_setting()
#        self._force_layout()


        show_hg_message = False
        if (self.proj is not None and wx.GetApp().IsMainLoopRunning()): 
            self.perform_package_update_check()
        else:
            wx.CallAfter(self.perform_package_update_check)
        ### load gui setting
        self.proj_tree_viewer.update_widget()
#        self.update_save_project_menu(True)
        self.Thaw()
        self.sb.SetStatusText("", 0)
        self.sb.Refresh()

        return True
    def perform_package_update_check(self):
        dprint1('checking HG repo for updates')
        from ifigure.mto.hg_support import hg_check_all_incoming_outgoing
        ret, ret2, ret3 = hg_check_all_incoming_outgoing(self.proj)
        if len(ret) > 0 or len(ret2) > 0:
            wx.CallAfter(self.show_package_update_notice, len(ret), len(ret2), len(ret3))

    def show_package_update_notice(self, l, l2, l3):
        dlg=wx.MessageDialog(self, 
               str(l) +  " packages are updated in repository.\n"+
               str(l2) + " local packages are newer than repository.\n" + 
               str(l3) + " packages may need merge (multiple heads).\n\nConsider Package Update from project pull down menu.",
               'Package check notice',
                             wx.OK|wx.STAY_ON_TOP|wx.ICON_INFORMATION)
        ret=dlg.ShowModal()
        dlg.Destroy()

    def make_empty_project(self):
        '''
        make some default empty project
        '''
        self._set_proj(ProjectTop())
        #return None
        book = self.proj.onAddBook()
        #book._keep_data_in_tree = True
        ipage  = book.add_page()
        self.ipage = ipage
        f_page = book.get_page(ipage)
        f_page.add_axes()
        return book


    def open_editor_panel(self):
        if (not self.gui_tree.get_toggle(self.panel2) and 
            self.isEditorAttached()):
             self.gui_tree.set_showhide([True], self.panel2)
             self.gui_tree.show_toggle_menu(self.panel2)
             self.gui_tree.rebuild_menu()
             self.gui_tree.update_check()
             self.gui_tree.set_splitters()

    def onOpenFile(self, e=None):
        path = dialog.read(parent = self, message="Select file to open", 
                           wildcard = 'Any|*|py(*.py)|*.py')
        if path != '':
           command = self.get_file_helper_command(path)
           if command != '':
               wx.CallAfter(self.shell.Execute, command)
               wx.CallAfter(self.proj_tree_viewer.update_widget)
           else:
               self.script_editor.OpenFile(path)
               self.open_editor_panel()
#           self.gui_tree.set_splitters()
               self.Layout()

    def onOpenScript(self, e=None):
        path = dialog.read(parent = self, message="Select script to open", 
                           wildcard = 'py(*.py)|*.py')
        if path != '':
           dlg=wx.MessageDialog(None, 
                    'Do you want to create Script in Tree?',
                    'Import script',
                    wx.YES_NO)
           ret=dlg.ShowModal()
           dlg.Destroy()
           if ret  == wx.ID_YES:
               newname = str(os.path.basename(path).split('.')[0])
               script = self.proj.add_script(newname)
               script.onImportScriptFile(file = path)
               self.proj_tree_viewer.update_widget()
               if e is not None: script.onEditScript(e)
           else:
               self.script_editor.OpenFile(path)
               self.open_editor_panel()
#           self.gui_tree.set_splitters()
               self.Layout()

    def onNew(self, e=None):
        if self.proj is not None:
           dlg=wx.MessageDialog(None, 
                    'Do you want to close it?',
                    'Project is open',
                    wx.OK|wx.CANCEL)
           ret=dlg.ShowModal()
           dlg.Destroy()
           if ret  == wx.ID_OK:
               self.onCloseProject(e)
#            elif ret == wx.ID_SAVE:
#                self.onSave(e)
           else:
              return
        book = self.make_empty_project()
#        self.open_book_in_appwindow(book, ipage=0)

        self.proj_tree_viewer.update_widget()
        self.proj_tree_viewer.ch.clear_text()
        self._force_layout()
        self.set_filename_2_window_title()
#        self.update_save_project_menu(False)
        self.set_proj_saved(False)
  
    def onNewApp(self, e):
        import piscope, subprocess, shlex
        import ifigure.widgets.canvas.ifigure_canvas
        options = ' '
        if ifigure.widgets.canvas.ifigure_canvas.turn_on_gl:
            options = options + '-g '
        command = sys.executable + '  ' + piscope.__file__ + options
        if os.altsep is not None:
            command = command.replace(os.sep, os.altsep)

        self.redirector.turn_off()
        
        p=subprocess.Popen(shlex.split(command))
#                           shell = True)
#                           stdout=subprocess.PIPE)
        self.redirector.turn_on()

    def isEditorAttached(self):
        return self.script_editor.GetTopLevelParent() == self

    def onNewFile(self, e=None):
        obj = self.proj.onAddNewText()
        self.proj_tree_viewer.update_widget()

    def onNewScript(self, e=None):
        obj = self.proj.onAddNewScript()
        self.proj_tree_viewer.update_widget()

    def onNewDoc(self, e=None):
#        path = obj.path2fullpath()
        if not self.gui_tree.get_toggle(self.panel2) and self.isEditorAttached():
#             self.gui_tree.toggle_panel(self.panel2, True)
             self.gui_tree.set_showhide([True], self.panel2)
             self.gui_tree.show_toggle_menu(self.panel2)
             self.gui_tree.rebuild_menu()
             self.gui_tree.update_check()
             self.gui_tree.set_splitters()

        self.script_editor.NewFile()

    def save_gui_setting(self):
        '''
        save gui preference (if any)  at save time
        '''
        if self.canvas.get_figure() is not None:
            a = self.canvas.get_figure().figobj.get_full_path()
        else:            
            a = ''
        data = {'open page': a}


        path=self.proj.getvar("wdir")
        fpath = os.path.join(path, '.gui_setting')
        fid = open(fpath, 'w')
        pickle.dump(data, fid)
        fid.close()

        data = [{'module': v.__module__, 
                 'class':v.__class__.__name__, 
                 'path':v.book.get_full_path(), 
                 'ipage':v.ipage, 
                 'size': v.GetSize(), 
                 'pos': v.GetPosition(),
                 'isPropShown': v.isPropShown()}
                for v in self.viewers]
        fpath = os.path.join(path, '.opened_books')
        fid = open(fpath, 'w')
        pickle.dump(data, fid)
        fid.close()

    def load_gui_setting(self):
        '''
        load gui preference at save time

        gui_setting : currently not used
        opend_books : information of previously opend book and page
        '''
        path=self.proj.getvar("wdir")
        fpath = os.path.join(path, '.gui_setting')
        if os.path.exists(fpath):
           fid = open(fpath, 'r')
           gui_setting_data = pickle.load(fid)
           fid.close()

        fpath = os.path.join(path, '.opened_books')
        if os.path.exists(fpath):
           fid = open(fpath, 'r')
           opend_book_data = pickle.load(fid)
           fid.close()
           flag = False
           for v in opend_book_data:
               if isinstance(v, tuple):  
                   v =  {'module': v[0],
                         'class':  v[1],
                         'path':   v[2],
                         'ipage':  v[3]}
               try:
                  mod = __import__(v['module'])
                  mod = sys.modules[v['module']]
                  cls = getattr(mod, v['class'])
                  book = self.proj.find_by_full_path(v['path'])
#               print cls, self.__class__
                  kargs = {key:v[key] for key in ('ipage', 'size', 'pos', 'isPropShown') 
                           if key in v}
 
                  if cls == self.__class__:
                      self.open_book_in_appwindow(book, ipage = v['ipage'])
                      flag  = True
                  else:
#                      kargs['size'] = (200, 400)
                      ifigure.events.SendOpenBookEvent(book, 
                                                    w = self,
                                                    viewer = cls, 
                                                    **kargs)
               except:
                  import traceback
                  traceback.print_exc()

           if not flag:
              self._go_closed_figure_mode()
    def onSave(self, e):
        if not MPTarzip().isReady():
            ret=dialog.message(self, 'Previous save job is still running.', 'Please wait', 0)
            return
        path=self.proj.getvar("filename")
        if path is None:
           self.onSaveAs(e)
        else:
           self.save_gui_setting()
           self.script_editor.SaveAll()
           self.proj_tree_viewer.ch.savetofile(filename = 
                os.path.join(self.proj.getvar("wdir"), '.command_history'))

           self.proj.SaveToFile(path)
        self.set_filename_2_window_title()
        self.set_proj_saved(True)

    def onSaveDoc(self, e):
        ipage = self.script_editor.nb.GetSelection()
        self.script_editor.SaveFile(saveas = False, ipage=ipage)

    def onSaveAsDoc(self, e):
        ipage = self.script_editor.nb.GetSelection()
        self.script_editor.SaveFile(saveas = True, ipage=ipage)

    def set_window_title(self):
        super(ifigure_app, self).set_window_title()
        title=self.GetTitle()
        if title.endswith('*'): title = title[:-1]
        name = self.proj.getvar('filename')
        if name is None: 
           name = 'untitled'
        else:
           name = os.path.basename(name)
        self.write_launcher_file(name)

        if len(title) > 0:
           xxx = ['piScope',  name, title]
        else:
           xxx = ['piScope',  name]
        title = ':'.join(xxx)
        if not self.proj.get_saved():
            title = title + '*'

        from ifigure.utils.mp_tarzip import lc
        if not lc.acquire(False):
            title = title + ' (save project in progress)' 
        else: 
            lc.release()
        self.SetTitle(title)   

    def set_proj_saved(self, value):
        #import traceback
        #traceback.print_stack()
        proj = self.proj
        if not value:
             if proj.get_saved():
                 proj.set_saved(value)
                 self.set_window_title()
        else:
             if not proj.get_saved():
                 proj.set_saved(value)
                 self.set_window_title()

    def set_filename_2_window_title(self):
        self.set_window_title()
        return
#        name = self.proj.getvar('filename')
#        if name is None: name = 'untitled'
#        title=self.GetTitle()
#        arr = title.split(':')
#        arr[1] = os.path.basename(name)
#        self.SetTitle(':'.join(arr))        

    def onSaveAs(self, e):
        from ifigure.utils.mp_tarzip import lc
        if not lc.acquire(False):
            ret=dialog.message(self, 'Previous save job is still running.', 'Please wait', 0)
            return
        lc.release()
        opath=self.proj.getvar("filename")
        owdir=self.proj.getvar("wdir")
        self.save_gui_setting()

        try:
            def_path = os.path.dirname(opath)
        except:
            def_path = os.getcwd()
        path = dialog.write(parent = self, message="Enter Project File Name", 
                            defaultfile = os.path.join(def_path, '.pfz'))
        
        if path != '':
           if path[-4:] != '.pfz':
              path=path+'.pfz'
           print(("saving to " + path))
           self.proj_tree_viewer.ch.savetofile(filename = 
                os.path.join(self.proj.getvar("wdir"), '.command_history'))
           self.proj.SaveToFile(path, opath=opath)
#           self.update_save_project_menu(True)
#           self.set_filename_2_window_title()
           nwdir = self.proj.getvar("wdir")
           self.script_editor.switch_wdir(owdir, nwdir)
           self.set_proj_saved(True)

           self.read_recent_files()
           if not path in RECENT_FILE: 
               RECENT_FILE.append(path)           
               self.write_recent_files()


    def onSaveFile(self, e=None, saveas=False):
        self.script_editor.SaveFile(saveas)

    def onCloseProject(self, e=None):
        ## file date check should be added future....
        for v in [v for v in self.viewers]:
           if v is not self: 
               bk = v.book
               v.Close()
               while bk.isOpen:
                  time.sleep(0.1)
#                  wx.Yield()
        self.canvas.unselect_all()
        self.proj.CloseProject()
        self.script_editor.close_all_pages()
        self._set_proj(None)
        self.ipage=-1
        self.proj_tree_viewer.update_widget()
        self._force_layout()

#    def onPreference(self, e):
#        from ifigure.widgets.dlg_preference import dlg_preference

#        dlg_preference(components, self)
#        for c in components:
#            c.save_setting()
        #dprint1('preference panel is not yet implemented')

    def onAbout(self, e):
        import ifigure
        from ifigure.ifigure_config import icondir as path
        icon_path=os.path.join(path, 'app_logo_small.png')
        info = wx.AboutDialogInfo()
 
        info.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_PNG))
        info.SetName('piScope')
        info.SetVersion('beta ')
        info.SetDescription('Python scripting workbench for \n   - browing MDSplus Data.\n   - analysing experiemntal data.\n   - running simulation codes.\n        ...\n')
        info.SetCopyright('(C) 2012 - 2016 S. Shirawa')
        info.SetWebSite('http://piscope.psfc.mit.edu/')
        wx.AboutBox(info)

    def onClearCommandHistory(self, e):
        self.proj_tree_viewer.ch.clear_text()

    #
    #   Edit menue
    #
    def onCut(self, e):
        fc=self.FindFocus()
        
        while fc is not None:
           if (fc is self.canvas.canvas or
               fc is self.property_editor):                  
               super(ifigure_app, self).onCut(e)
               self.proj_tree_viewer.update_widget()               
               break
           #if isinstance(fc, ProjTreeViewer):
           #    fc.Cut()
           #    break
           if isinstance(fc, SimpleShell):
               fc.Cut()
               break                                   
           if isinstance(fc, CommandHistory):
               fc.Cut()
               break                                   
           if isinstance(fc, wx.stc.StyledTextCtrl):
               fc.Cut()
               break                        
           fc = fc.GetParent()                       

    def onCopy(self, e):        
        fc = self.FindFocus()

        while fc is not None:
           if ( fc is self.canvas.canvas or 
                fc is self.property_editor):                  
               super(ifigure_app, self).onCopy(e)
#               self.proj_tree_viewer.update_widget()               
               break
           elif fc is self.proj_tree_viewer.tree:
               if e.GetEventObject() != self:
                    check = self.proj_tree_viewer.copy_tree_item()
                    if not check:
                        dlg=wx.MessageDialog(self, 
                             'Selected Item can not be copyed',
                             'Error',
                              wx.OK)
                        ret=dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        self.set_status_text('Copy (tree item)', timeout = 3000)
#                    print 'copy in tree itme is selected from menu'
               break
           elif isinstance(fc, SimpleShell):
               fc.Copy()
               break                                   
           elif isinstance(fc, CommandHistory):
               fc.Copy()
               break                                   
           elif isinstance(fc, wx.stc.StyledTextCtrl):
               fc.Copy()
               break                        
           fc = fc.GetParent()               
           #        if fc is self.canvas.canvas:      
           #           super(ifigure_app, self).onCopy(e)
           #           self.proj_tree_viewer.update_widget()
           #        if isinstance(fc, wx.stc.StyledTextCtrl):
           #           fc.Copy()
           #        if isinstance(fc, ProjTreeViewer):
           #           fc.Copy()

    def onPaste(self, e):
        fc=self.FindFocus()
#        print fc.GetParent(), fc
        while fc is not None:
           if (fc is self.canvas.canvas or
               fc is self.property_editor):                  
               super(ifigure_app, self).onPaste(e)
               self.proj_tree_viewer.update_widget()               
               break
           elif fc is self.proj_tree_viewer.tree:
               if e.GetEventObject() != self:
                    check = self.proj_tree_viewer.paste_tree_item()
                    if not check:
                        dlg=wx.MessageDialog(self, 
                             'Selected Item can not be pasted',
                             'Error',
                              wx.OK)
                        ret=dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        self.set_status_text('Paste (tree item)', timeout = 3000)
               break
           elif isinstance(fc, SimpleShell):
               fc.Paste()
               break                                   
           elif isinstance(fc, wx.stc.StyledTextCtrl):
               fc.Paste()
               break                        
           fc = fc.GetParent()               
        
    def onAppWindowClose(self, e):
        
        from ifigure.utils.mp_tarzip import lc
        if not lc.acquire(False):
            ret=dialog.message(self, 'Save job is running. Application will close after \ndata is saved.', 'Please wait', 0)
            lc.acquire()
        lc.release()
        dprint1("ending program...(window close)")
        from ifigure.widgets.debugger import is_waiting
        if is_waiting():
            self.script_editor.d_panel.StopDebugger()
        sys.stdout = self.stdfiles[0]
        sys.stderr = self.stdfiles[1]

        self.shell.write_history()
        self.write_geom_file()

        for v in [v for v in self.viewers]:
           if v is not self: 
               bk = v.book
               v.clear_history()
               v.Close()
               while bk.isOpen:
                  time.sleep(0.1)

        self.viewer = []
        self.clear_history()

        ### close script editor if it is detached
        try:
            se = self.script_editor.GetTopLevelParent()
            if se != self:
                 se.Close()
        except PyDeadObjectError:     
            pass

        ##  stop file system checking from script edtior
        self.Unbind(ifigure.events.TD_EVT_FILESYSTEMCHANGED)
        if self.proj is not None:
            self.proj.CloseProject()

        self.save_pref()
    
        try:
            self.tipw.Destroy()
        except PyDeadObjectError:     
            pass
        try:
            self.logw.Destroy()
        except PyDeadObjectError:     
            pass

        ### close script editor if it is detached
        try:
            from ifigure.mto.hg_support import diffwindow
            if diffwindow is not None:
                 diffwindow.Destroy()
        except PyDeadObjectError:     
            pass
        self.tbicon.Destroy()
        self.Destroy() ## is this necessary to make sure app closes??? (2015.10)
        e.Skip()

#    def onQuit(self, e=None):
#        self.Close()
    
    def onShellEnter(self, evt):
        self.set_proj_saved(False)
        self.proj_tree_viewer.get_shellvar_viewer().update(self.shell)
        self.proj_tree_viewer.get_var_viewer().update()
        
    def write_geom_file(self):
        size=self.GetSize()
        sh =  self.gui_tree.get_showhide()
        pos = self.gui_tree.get_sashposition()
        print(('editor detached', not self.isEditorAttached()))
        val = {"version":0,"size":size, "sh":sh, "pos":pos,
               'editor_detached': not self.isEditorAttached(),
               'RECENT_FILE': RECENT_FILE }
        from ifigure.ifigure_config import geom_file
        fid=open(geom_file, 'w')
        pickle.dump(val, fid)
        fid.flush()
        fid.close()

    def read_geom_file(self):
        from ifigure.ifigure_config import geom_file
        fid=open(geom_file, 'r')
        val=pickle.load(fid)
        fid.close()
        return val

    def read_recent_files(self):
        val = self.read_geom_file()
        if 'RECENT_FILE' in val:
            for item in val['RECENT_FILE']:
                if not item in RECENT_FILE and os.path.exists(item):                
                     RECENT_FILE.append(item)

    def write_recent_files(self):
        val = self.read_geom_file()
        val['RECENT_FILE'] = RECENT_FILE

        from ifigure.ifigure_config import geom_file
        fid=open(geom_file, 'w')
        pickle.dump(val, fid)
        fid.flush()
        fid.close()

    def draw(self, *args, **kargs):
        if self.aviewer == self:
           super(ifigure_app, self).draw(*args, **kargs)
        else:
           self.aviewer.draw(*args, **kargs)

    def draw_all(self, *args, **kargs):
        if self.aviewer == self:
           super(ifigure_app, self).draw_all(*args, **kargs)
        else:
           self.aviewer.draw_all(*args, **kargs)

    def show_page(self, ipage=0, last=False, first=False):
        if self.aviewer == self:
            super(ifigure_app, self).show_page(ipage=ipage, 
                                           last=last, first=first)
        else:
            self.aviewer.show_page(ipage=ipage, 
                                           last=last, first=first)
        self.proj_tree_viewer.update_widget()
    def add_page(self, *args, **kargs):
        if self.aviewer == self:
           return super(ifigure_app, self).add_page(*args, **kargs)
        else:
           return self.aviewer.add_page(*args, **kargs)

    def get_page(self, *args, **kargs):
        if self.aviewer == self:
           return super(ifigure_app, self).get_page(*args, **kargs)
        else:
           return self.aviewer.get_page(*args, **kargs)

    def del_page(self, *args, **kargs):
        if self.aviewer == self:
           return super(ifigure_app, self).del_page(*args, **kargs)
        else:
           return self.aviewer.del_page(*args, **kargs)

    def set_selection(self, *args, **kargs):
        if self.aviewer == self:
           return super(ifigure_app, self).set_selection(*args, **kargs)
        else:
           return self.aviewer.set_selection(*args, **kargs)

    def get_axes(self, *args, **kargs):
        if self.aviewer == self:
           return super(ifigure_app, self).get_axes(*args, **kargs)
        else:
           return self.aviewer.get_axes(*args, **kargs)

    def set_axes(self, *args, **kargs):
        if self.aviewer == self:
           return super(ifigure_app, self).set_axes(*args, **kargs)
        else:
           return self.aviewer.set_axes(*args, **kargs)

    def open_newbook_in_newviewer(self, viewer_class):
        book = self.proj.onAddBook()
        i_page=book.add_page()
        page = book.get_page(i_page)
        page.add_axes()
        page.realize()
#       page.set_section(*args)

        from ifigure.widgets.book_viewer import BookViewer
        v = viewer_class(self, wx.ID_ANY, book.get_full_path(),
                               book=book)
        self.viewers.append(v)
        if self.aviewer is None:
            self.aviewer = v
        self.proj_tree_viewer.update_widget()
        return book, v

    def open_book_in_newviewer(self, viewer_class, book, ipage=0, kwargs={}):
        if book.num_page() == 0: 
             print("***No pages***")
             return
        v = viewer_class(self, wx.ID_ANY, book.get_full_path(),
                          book=book, **kwargs)
#        v.adjust_frame_size()
#        elif evt.viewer == 'mdsscope':
#           v = MDSScope(self, wx.ID_ANY, book.get_full_path(),
#                       book=book, connection_type=evt.param)
        self.viewers.append(v)
        self.proj_tree_viewer.update_widget()
        v.show_page(ipage)
        if self.aviewer is None:
            self.aviewer = v
        return v

    def open_book_in_appwindow(self, book, ipage=0):
        if self.book is not None:
            self.close_figurebook()
        self.book = book
        self.ipage = 0
        self.book.set_open(True)
        self.viewers.append(self)
        self.gui_tree.show_toggle_menu(self.panel1)
        self.gui_tree.show_toggle_menu(self.property_editor) 
        if self.aviewer is None:
            self.aviewer = self
        self.gui_tree.rebuild_menu()
        self.gui_tree.toggle_panel(self.panel1, True)
        self.proj_tree_viewer.update_widget()
        self.open_book()
        self.canvas.canvas._onSize()
        BookViewerFrame.show_page(self, ipage)
        [x.Enable(True) for x in self._figure_mnis]
        [v.adjust_attach_menu() for v in self.viewers]
        if self.aviewer is None:
            self.aviewer = v
        self.draw_all()

    def make_attached_script_editor(self):
        self.script_editor = ScriptEditor(self.panel2)
        sizer = self.panel2.GetSizer()
        sizer.Add(self.script_editor, 1, wx.EXPAND|wx.ALL)

    def onDetachFigure(self, evt):
        book = self.book
        ipage = self.ipage
        aviewer = self.aviewer
        self.close_figurebook()
        viewer = self.open_book_in_newviewer(BookViewer, book, ipage=ipage)
        if aviewer is self:
           self.aviewer = viewer

    def attach_editor(self, open_editor=True):
        self.script_editor.Reparent(self.panel2)
        self.gui_tree.show_toggle_menu(self.panel2)
        self.gui_tree.rebuild_menu()
        self.gui_tree.toggle_panel(self.panel2, open_editor)
        sizer = self.panel2.GetSizer()
        sizer.Add(self.script_editor, 1, wx.EXPAND|wx.ALL)
        sizer.Layout()

    def onDetachEditor(self, evt):
        # evt can be None
#        self._editor_mni.Enable(False)
        self.gui_tree.hide_toggle_menu(self.panel2)
        self.gui_tree.rebuild_menu()
        self.gui_tree.toggle_panel(self.panel2, False)

        self.panel2.GetSizer().Detach(self.script_editor)
#        sel, contents = self.script_editor.get_all_data()
#        self.script_editor.Destroy()
        from ifigure.widgets.script_editor import ScriptEditorFrame
        frame = ScriptEditorFrame(self)
        frame.set_script_editor(self.script_editor)

#        self.script_editor.set_all_data(sel, contents)

    def onCloseFigure(self, evt):
        if self.book._keep_data_in_tree:
            self.close_figurebook()
        else:
            self.onCloseFigureDeleteBook(evt)

    def onCloseFigureDeleteBook(self, evt = None):
        b = self.book
        self.close_figurebook()
        b.destroy()
        self.proj_tree_viewer.update_widget()

    def close_figurebook(self):
        ##
        ##  close figurebook opened in main window...
        ##  

        # self.viewers.remove(self)
       
        #if len(self.viewers) == 0:
        #    self.aviewer = None
        #elif self.aviewer == self:
        #    self.aviewer = self.viewers[0]

        self.book.set_open(False)
        s = self.canvas.GetClientSize()
        self.book._screen_size = (s[0], s[1])

        self._go_closed_figure_mode()

        self.set_window_title()
        [x.Enable(False) for x in self._figure_mnis]
        [v.adjust_attach_menu() for v in self.viewers]

        
    def _go_closed_figure_mode(self):
        if not self in self.viewers: return ## already in closed_figure_mode
        self.viewers.remove(self)
        #print len(self.viewers)
        if len(self.viewers) == 0:
            self.aviewer = None
        elif self.aviewer == self:
            self.aviewer = self.viewers[0]


        self.gui_tree.toggle_panel(self.panel1, False)
        self.gui_tree.hide_toggle_menu(self.panel1)
        self.gui_tree.hide_toggle_menu(self.property_editor) 
        self.gui_tree.rebuild_menu()
        self.proj_tree_viewer.update_widget()
        self.canvas.set_figure(None)
        self.book = None        

    def run_text(self, txt, no_exec=False):
        if not no_exec:
            self.shell.lvar['command']=txt+'\n'
            self.shell.execute_text(txt)
        else:
            self.shell.write(txt)     

    def _set_proj(self, proj):
        self.proj=proj
        if self.proj is not None:
           self.proj.set_app(self)
        if hasattr(self, 'shell'):
           self.shell.set_proj(self.proj)

#    def update_save_project_menu(self, value):
#        pass
#        for v in self.viewers:
#            if hasattr(v, 'save_project_menu'):
#                v.save_project_menu.Enable(value)
#        self.save_project_menu.Enable(value)
        
    def update_open_filelist(self, list):
        '''
        save file names opend in script editor
        it saves only the files under wdir.
        '''
        nlist=[]
        if self.proj is not None:
           wdir = self.proj.getvar("wdir")
           if wdir is None: return
        else:
           return
        for item in list:
            c1 = os.path.commonprefix([wdir, item])
            if c1 == wdir:
                nlist.append((item, 1))
            else:
                nlist.append((item, 0))
        dot_file=os.path.join(wdir, '.opened_file')
        fid=open(dot_file, 'w')
        for item, flag in nlist:
           if flag:
              relpath=os.path.relpath(item, wdir)
           else:
              relpath = item
           if hasattr(item, 'td'): relpath = relpath + '\t'+item.td
           fid.write(relpath + '\n')
        fid.close()
       
    def onTD_EvtUndo(self, evt):
        fc = self.FindFocus()
        if fc is not None:
            if isinstance(fc, wx.stc.StyledTextCtrl):            
                fc.Undo()
                return
            elif isinstance(fc, SimpleShell):            
                fc.Undo()
                return

        td=GlobalHistory().get_history(evt.GetEventObject()).undo()
        if isinstance(td, FigObj):
#           print 'change happens under', td.get_full_path()            
           book = td.get_root_figobj()
           viewer = self.find_bookviewer(book)
           if viewer is not None: 
              self.aviewer = viewer           
#              viewer.canvas.draw()
#              viewer.canvas.refresh_hl_idle()
              viewer.property_editor.update_panel()

    def onTD_EvtRedo(self, evt):
        fc = self.FindFocus()
        if fc is not None:
            if isinstance(fc, wx.stc.StyledTextCtrl):            
                fc.Redo()
                return
            elif isinstance(fc, SimpleShell):            
                fc.Redo()
                return

#       td=self.history.redo()
        td=GlobalHistory().get_history(evt.GetEventObject()).redo()        
        if isinstance(td, FigObj):
#           print 'change happens under', td.get_full_path()
           book = td.get_root_figobj()
           viewer = self.find_bookviewer(book)
           if viewer is not None: 
              self.aviewer = viewer           
#              viewer.canvas.draw()
#              viewer.canvas.refresh_hl_idle()
              viewer.property_editor.update_panel()

    def onTD_EditFile(self, evt):
        if self.helper.setting['use_editor']:
            root = os.path.dirname(os.path.dirname(ifigure.__path__[0]))
            bin = os.path.join(root, 'bin')
            txt = self.helper.setting['editor']
            txt = txt.replace('{bin}', bin)
            txt = txt.format(evt.file)
            dprint1(txt)
            os.system(txt)
        else:
            readonly = evt.readonly if hasattr(evt,'readonly') else False
            self.script_editor.OpenFile(file=evt.file, readonly=readonly)
            if self.isEditorAttached():
                self.gui_tree.set_showhide([True], self.panel2)
                self.gui_tree.show_toggle_menu(self.panel2)
                self.gui_tree.rebuild_menu()
                self.gui_tree.update_check()
                self.gui_tree.set_splitters()

            list = self.script_editor.get_filelist()
            self.update_open_filelist(list)

    def onTD_CloseFile(self, evt):
        list = self.script_editor.get_filelist()
        if len(list) == 0:
             if self.isEditorAttached():
                 self.gui_tree.set_showhide([False], self.panel2)
                 self.gui_tree.hide_toggle_menu(self.panel2)
                 self.gui_tree.rebuild_menu()
                 self.gui_tree.update_check()
                 self.gui_tree.set_splitters()
             else:
                 self.script_editor.GetTopLevelParent().Close()
        self.update_open_filelist(list)
        self.Layout()

    def onTD_Changed(self, evt):
        from ifigure.events import changed_in_queue

        figobj = evt.GetTreeDict()                    
        def update_proj_viewer(evt, td=figobj, time=evt.time):
            ifigure.events.changed_in_queue  = ifigure.events.changed_in_queue  - 1            
            if ifigure.events.changed_in_queue > 0:
                dprint2('more changed events are coming, let skip')
                return
            self.Unbind(wx.EVT_IDLE) 
            dprint2('processing changed event')
            self.proj_tree_viewer.update_widget_request2(time)
            dprint2('update_widget_done') 
            if (isinstance(td, FigObj) and
                td.get_figbook() is not None and
                td.get_figbook().isOpen):
                viewer = self.find_bookviewer(td.get_figbook())
                if viewer is not None: 
                    viewer.property_editor.update_panel_request2(time)            
#            ifigure.events.changed_in_queue = False
#            if contents_update:
#            self.proj_tree_viewer.update_content_widget(td)

        self.Bind(wx.EVT_IDLE, update_proj_viewer) 

    def onTD_Var0Changed(self, evt):
        self.proj_tree_viewer.update_content_widget(evt.GetTreeDict())

    def onTD_Selection(self, evt):
        td = evt.GetTreeDict()
        w = evt.GetEventObject() 
        fc = self.FindFocus()
        if isinstance(td, FigObj):
           book = td.get_root_figobj()
           viewer = self.find_bookviewer(book)
           if viewer is not None: self.aviewer = viewer
           if viewer is not None:
               if w != viewer.property_editor:
                   viewer.property_editor.onTD_Selection(evt)
               if w != viewer.canvas:
                   viewer.canvas.onTD_Selection(evt)
               # each bookviewer may want to get this event..    
               viewer.onTD_SelectionInFigure(evt)
        if w != self.proj_tree_viewer:
           self.proj_tree_viewer.onTD_Selection(evt)
        try:           
           if w != self.hdf_export_window:
              if self.hdf_export_window is not None:
                   self.hdf_export_window.onTD_Selection(evt)
        except PyDeadObjectError:
           self.hdf_export_window = None

#       this is added to preserve focus. 
#       not a perfect solution.
        if fc is not None: 
           fc.SetFocus()
           try: 
              fc.SetFocus()
           except PyDeadObjectError:
              pass

    def onTD_Replace(self, evt):
        super(ifigure_app, self).onTD_Replace(evt)
        history = GlobalHistory().get_history(evt.GetEventObject())        
        history.replace_artist(evt.a1, evt.a2)
#        print 'onTD_replace ifigure_app'
    def onTD_ThreadStart(self, evt):
        import time
#        print 'thread start event...', threading.current_thread().name
        if self.logw.check_thread_can_start(evt.thread):
            evt.dt._status = 'running ...'
            #self.proj_tree_viewer.update_widget()
            self.logw.watch_thread(evt)
#            evt.thread.start()
#            print evt.dt._status
#            while evt.thread.is_alive():
#               time.sleep(1)
#               print 'waiting'
        self.proj_tree_viewer.update_widget(no_set_selection = True)

    def onTD_RangeChanged(self, evt):
        # this is for mouse drag in colorbar
        # looks like generating unnecessary draw....

        dprint1('process range event')

        def rebind_range_changed(evt):
#            print 'rebinding'
            self.Bind(ifigure.events.TD_EVT_RANGECHANGED,
                 self.onTD_RangeChanged)
            self.Unbind(wx.EVT_IDLE) 
        self.Unbind(ifigure.events.TD_EVT_RANGECHANGED)
        self.Bind(wx.EVT_IDLE, rebind_range_changed) 

        book = evt.GetTreeDict().get_figbook()
        viewer = self.find_bookviewer(book)
#        viewer.canvas.onTD_RangeChanged(evt)
        viewer.property_editor.update_panel()

    def onTD_OpenBook(self, evt):

        book = evt.GetTreeDict()
        viewer_class = evt.viewer
        viewer =  self.open_book_in_newviewer(viewer_class, book,
                                              ipage=evt.ipage, kwargs = evt.kwargs)

        if evt.isPropShown is not None:
             if viewer.isPropShown() != evt.isPropShown:
                   wx.CallAfter(viewer.toggle_property)
        if evt.size is not None: wx.CallAfter(viewer.SetSize, evt.size)
        if evt.pos is not None: 
             from ifigure.utils.cbook import get_current_display_size
             x0, y0, xd, yd = get_current_display_size(self)
             if (evt.pos[0] < 0.9*xd and 
                 evt.pos[1] < 0.9*yd):
                 wx.CallAfter(viewer.SetPosition, evt.pos)        
        return viewer

    def onTD_CloseBook(self, evt):
        if evt.GetEventObject() in self.viewers:
            self.viewers.remove(evt.GetEventObject())
        else:
            dprint1('not found in current viewer list', evt.GetEventObject())
        if (self.aviewer == evt.GetEventObject() and
            len(self.viewers) != 0):
            self.aviewer = self.viewers[0]
        if len(self.viewers) == 0: 
            self.aviewer = None
        self.proj_tree_viewer.update_widget()

        if not self.IsShown() and len(self.viewers) == 0:
            wx.CallAfter(self.onQuit)

    def onTD_CloseBookRequest(self, evt):
        evt.GetEventObject().Close()

    def onTD_FileChanged(self, evt):
        self.script_editor.onTD_FileChanged(evt)
                 
    def onTD_PageShown(self, evt):
        td = evt.GetTreeDict()
        self.proj_tree_viewer.set_td_selection(td)

    def onTD_ShowPage(self, evt):
#        print 'here', 'ifigure'
        super(ifigure_app, self).onTD_ShowPage(evt)
        return

#       this part is removed. bookframe showpage now
#       trigger pageshown event, which is received
#       by a main window.
#
#        if not evt.BookViewerFrame_Processed:
#            td = evt.GetTreeDict()
#            book = td.get_root_figobj()
#            viewer = self.find_bookviewer(book)
#            if viewer == self: 
#                super(ifigure_app, self).onTD_ShowPage(evt)
#                evt.SetEventObject(self)
#            elif viewer != None:
#                viewer.onTD_ShowPage(evt)               
#                evt.SetEventObject(viewer)
#                viewer.Raise()
#            else:
#                #book is not open
#                super(ifigure_app, self).onTD_ShowPage(evt)
#                evt.SetEventObject(self)
#            evt.BookViewerFrame_Processed = True

#        bf = evt.GetEventObject()
#        f_page = bf.book.get_page(bf.ipage)
#        self.proj_tree_viewer.set_td_selection(f_page)

    def onTD_Evt(self, evt):
        if evt.code == 'Rename':
            for v in self.viewers:
                v.set_window_title()

    def onPV_DrawRequest(self, evt):
        td = evt.GetTreeDict()
        book = td.get_root_figobj()
        viewer = self.find_bookviewer(book)
        if viewer is None: return
        self.aviewer = viewer
#        if evt.wait_idle:
#           viewer.canvas.refresh_hl_idle()
#        else:
        if evt.time >  viewer.last_draw_time():
             viewer.draw(refresh_hl = evt.refresh_hl)

    def onPV_AddFigobj(self, evt):
        td = evt.GetTreeDict()
        book = td.get_root_figobj()
        viewer = self.find_bookviewer(book)
        if viewer is None: return
        self.aviewer = viewer
        page = book.get_page(viewer.ipage)
        if page.is_descendant(td) or page == td:
           viewer.draw()
           viewer.Raise()

    def onPV_DeleteFigobj(self, evt):
        td = evt.GetTreeDict()
        book = td.get_root_figobj()
        viewer = self.find_bookviewer(book)

        if viewer is None: 
           td.destroy()
           self.proj_tree_viewer.update_widget_request2(evt.time)
           return
        else:
           self.aviewer = viewer
           page = book.get_page(viewer.ipage)
           if isinstance(td, FigPage):
              ipage = book.i_page(td)
              npage = book.num_page()
              if npage == 1:
                  if viewer is not self:
                      viewer.Close()
                      td.destroy()
                  else:
                      # do nothing
                      return
              else:
                  book.i_page(td)
                  viewer.del_page(ipage)
              self.proj_tree_viewer.update_widget_request2(evt.time)
              return
           elif td == book:
              if viewer is not self:
                  viewer.Close()
                  td.destroy()
                  wx.CallAfter(self.proj_tree_viewer.update_widget_request, 
                               delay=500)
              else:
                  self.close_figurebook()
                  td.destroy()
                  wx.CallAfter(self.proj_tree_viewer.update_widget_request, 
                               delay=500)

           else:
              redraw = page.is_descendant(td)
              td.destroy()
              self.proj_tree_viewer.update_widget_request2(evt.time)
              if redraw: 
                  viewer.draw()
                  viewer.Raise()

    def onCV_CanvasSelected(self, evt):
        fig_page = evt.GetTreeDict()
        book = fig_page.get_parent()
        viewer = self.find_bookviewer(book)
        if viewer is not None: 
            self.aviewer = viewer

    def onRemoteCommand(self, evt):
        server = ifigure.server.Server()
        try:
            response  = server.process(evt.command)
        except:
            import traceback
            traceback.print_exc()
            response = 'failed'
        self.server_response_queue.put(response)

    def use_server(self):
        import Queue
        self.server_response_queue = Queue.Queue()
        return self.server_response_queue

    def find_bookviewer(self, book):
        for viewer in self.viewers:
            if viewer.book == book:
                return viewer
        return None
    def goto_no_mainwindow(self):
        if len(self.viewers) == 0:
            return
        if (len(self.viewers) == 1 and    
            self.viewers[0] is self):
            return
        self.Hide()

    def set_launcher_file(self, file):
        self._launcher_file = file
        if self.proj is None: return
        name = self.proj.getvar('filename')
        if name is None: 
           name = 'untitled'
        else:
           name = os.path.basename(name)
        self.write_launcher_file(name)
 
    def get_launcher_file(self):
        return self._launcher_file

    def write_launcher_file(self, name):
        file = self.get_launcher_file()
        if file is None: return
       
        filename = os.path.join(file, str(os.getpid()))
        fid = open(filename, 'w') 
        fid.write(name)
        fid.close()

class MyApp(wx.App):
    def __init__(self, *args, **kwargs):
        self._palettes = weakref.WeakKeyDictionary()
        self.AppWindow = None
        wx.App.__init__(self, *args, **kwargs)

        
    def OnInit(self,launcher_file = None):
        self._ifig_app = ifigure_app(None, "iScope+:")
        self.SetTopWindow(self._ifig_app)
        self.AppWindow = self._ifig_app
        
        self._ifig_app.Show(True)

        if "wxMac" in wx.PlatformInfo:
            self._ifig_app.Bind(wx.EVT_MENU, self.MacQuit, id = self.GetMacExitMenuItemId())
        return True

    def add_palette(self, window):
        if not window.GetParent() in self._palettes:
           self._palettes[window.GetParent()] = [window, ]
        else:
           self._palettes[window.GetParent()].append(window)
        
    def raise_palette(self, window):
        if not window in self._palettes:return
        x = self._palettes[window]
        for w in x:
            try:
                w.Raise()
            except:
                import traceback
                traceback.print_exc()
                pass
        wx.CallAfter(window.Raise)
        
    def rm_palette(self, window):
        x = self._palettes[window.GetParent()]
        if window in x:
            x.remove(window)
        if len(x) == 0: self._palettes[window.GetParent()]

    def clean_palette(self):
#        from wx._core import _wxPyDeadObject
        dead_keys = [key for key in self._palettes if not key]
#                     if isinstance(key, _wxPyDeadObject)]
        for key in dead_keys:
            del self._palettes[key]
        dead_keys = []
        for key in self._palettes:
            dead_window = []
            for x in self._palettes[key]:
#               if isinstance(x, _wxPyDeadObject):
                if not x:
                   dead_window.append(x)
            for x in dead_window:
                self._palettes[key].remove(x)
            if len(self._palettes[key]) == 0:
                dead_keys.append(key)
        for key in dead_keys:
            del self._palettes[key]

    def process_child_focus(self, window):
        self.clean_palette()
        for key in self._palettes:
            if key is window:
                for x in self._palettes[key]:
                    if x.IsShown(): continue
                    try:
                        x.Show()
                        x.Raise()
                    except:
                        pass
            else:
                for x in self._palettes[key]:
                    try:
                        x.Hide()
                    except:
                        pass
    def get_ifig_app(self):
        return self._ifig_app
    def MacReopenApp(self):
        if self.GetTopWindow().IsShown():
            self.GetTopWindow().Raise()            
#        print 'here'
    def MacQuit(self, evt):
        self.GetTopWindow().Close()


