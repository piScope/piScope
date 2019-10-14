from ifigure.mto.treedict import TreeDict


class PyClass(TreeDict):
    """ 
    A tree object class which all the essential 
    capabilities are defined externally
    """

    def __init__(self, parent, src=None):
        self._module_file = ''      # file name
        self._module_co = None
        self._module_mtime = 0.
        super(PyClass, self).__init__(parent=parent, src=src)

    @classmethod
    def isPyClass(self):
        return True

    def get_namebase(self):
        return 'classmodule'

    @classmethod
    def load_classimage(self):
        from ifigure.ifigure_config import icondir as path
        idx1 = cbook.LoadImageFile(path, 'script.png')
        return [idx1]

    def run_init(self, e=None):
        self._module.run_init(self)

    def do_run(self, e=None):
        pass

    def popup_menu(self):
        pass

    def load_module(self, file=None):
        if file is None:
            self._module_co = None

        logging.basicConfig(level=logging.DEBUG)
        try:
            self._module_co = imp.load_source('ifigure.add_on.tmp', file)
            name = self._module_co.module_name
            self._module_co = imp.load_source('ifigure.add_on'+name, file)
            self._module_mtime = os.path.getmtime(file)
            self._module_file = file
            self._func = self._module_co.func
            self._func_init = self._module_co.func_init
            self._method_init = self._module_co.method_init
            self._menu = self._module_co.menu
            for mname in self._module_co.method:
                m = getattr(self._module_co, mname)
                object(TreeDict, self).__setattr__(self, mname,
                                                   m.__get__(self, self, self.__class__))
        except Exception:
            logging.exception("Module Loading Failed")

    def load_classfile(self, file):
        self.setvar("module file", file)
        ####

    def tree_viewer_menu(self):
     # return MenuString, Handler, MenuImage
        return self.menu + \
            [('+Module', None, None),
                ('Reload', self.onReload, None),
                ('Edit File', self.onEditModule, None),
                ('Select File', self.onSelectModuleFile, None),
                #               ('Import File', self.onImportScriptFile, None),
                ('!', None, None),
                ('---', None, None)] + \
            super(PyClass, self).tree_viewer_menu()

    def onEditModule(self, e):
        self._module.load_module(self.getvar("module file"))
        if wx.GetKeyState(wx.WXK_CONTROL):
            self._module.edit_module()
            return
        handler = self.get_root_parent().app.GetEventHandler()
        evt = ifigure.events.TreeDictEvent(
            ifigure.events.EditFile,
            wx.ID_ANY)
        evt.SetTreeDict(self)
        evt.file = self._module._module_file
        handler.ProcessEvent(evt)

    def onSelectModuleFile(self, e=None):
        open_dlg = wx.FileDialog(None, message="Select module",
                                 wildcard='*.py', style=wx.FD_OPEN)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            raise ValueError
        file = open_dlg.GetPath()
        self.load_module(file)
        open_dlg.Destroy()
