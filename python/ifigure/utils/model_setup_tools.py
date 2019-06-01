'''
simpe package/module management tool for piscopelib 

piscopelib is a libray located in .ifigure_rc/.local/site-packages/piscopelib


'''
import wx
from ifigure.utils.edit_list import DialogEditList


def setup(package='', root='', path='setup_scripts',
          del_scripts=True, model=None):

    from ifigure.mto.hg_support import load_subtree_hg, dlg_s
    from ifigure.events import SendSelectionEvent

    app = wx.GetApp().TopWindow
    proj = app.proj
    name = 'setup_scritps'

    if root == '' or path == '':
        if path == '':
            path = 'setup_scripts'
        list6 = [
            ["root repository", None, 404, dlg_s()],
            ["source ", path, 0], ]
        value = DialogEditList(list6, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=app,
                               title='Select Setup Scripts Repo.')
        if not value[0]:
            return
        root = str(value[1][0])
        path = str(value[1][1])

    if not proj.has_owndir():
        proj.mk_owndir()

    if proj.has_child(name):
        name = proj.get_next_name(name)
    obj = load_subtree_hg(proj, root=root, path=path, name=name, overwrite=False,
                          run_setup=False, launch_gui=False)  # , src = 'setup_scripts')

    separator = '---------'
    if package == '':
        names = obj.get_childnames()
        names = sorted(names)
        names.extend([separator, 'setup scripts'])
        setting = {"style": wx.CB_READONLY,
                   "choices": names}
        list6 = [[None, "Select scripts to run ", 2, None],
                 ["setup scripts", names[0], 4, setting], ]
#             [None, del_scripts, 3, {"text":'Delete scripts folder after the run'}],]

        value = DialogEditList(list6, modal=True,
                               style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                               tip=None,
                               parent=app,
                               title='Select Setup Scripts')
        if not value[0]:
            if del_scripts:
                obj.destroy()
            else:
                app.proj_tree_viewer.update_widget()
                SendSelectionEvent(obj)
            return
        package = str(value[1][1])
#        del_scripts = value[1][2]

    if (package != 'setup scripts') and (package != separator):
        script = obj.get_child(name=package)
        if model is None:
            model = proj.onAddModel()
        new_model = script(model)

        if del_scripts:
            obj.destroy()

        app.proj_tree_viewer.update_widget()
        if new_model is not None:
            SendSelectionEvent(new_model)
        return model
    else:
        app.proj_tree_viewer.update_widget()
        SendSelectionEvent(obj)
        return obj
