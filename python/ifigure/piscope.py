def piscope():
    import multiprocessing as mp
    import pkg_resources  # somehow importing this later cause warning message
    import mpl_toolkits
    import sys
    import os
    import wx
    import weakref
    import matplotlib
    import shutil
    import warnings

    import platform
    if platform.system() == 'Darwin':
        mp.set_start_method('spawn')
    else:
        if 'forkserver' in mp.get_all_start_methods():
            mp.set_start_method('forkserver')

    matplotlib.use('WXAGG')

    wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)
    wx.UpdateUIEvent.SetUpdateInterval(1000)

    import ifigure
    from ifigure.ifigure_app import ifigure_app, MyApp
    from ifigure.utils.mp_tarzip import MPTarzip
    from os.path import expanduser

    # if it does not have write permission to current directory
    # it moves to home directory
    # make tempfile need write permission in some case?
    # (2014 10)
    if not os.access(os.getcwd(), os.W_OK):
        print('No access to current working directory, moving to home directory')
        os.chdir(expanduser('~'))

    import site
    home = expanduser('~')
    site.USER_SITE = os.path.join(
        home, '.ifigure_rc', '.local', 'site-packages')
    site.USER_BASE = os.path.join(home, '.ifigure_rc', '.local')
    redirect_std = True
    use_console = True
    file = None
    start_server = False
    show_file_open_error = False
    exe_command = None
    hide_main = False

    class MainlevelJob(object):
        def __init__(self):
            self.func = None
            self.func2 = []

        def setjob(self, func):
            self.func = func

        def dojob(self):
            if self.func is not None:
                self.func()
            self.func = None

        def setfinishjob(self, func):
            if not func in self.func2:
                self.func2.append(func)

        def finishjob(self):
            for f in self.func2:
                f()

    # this is a place where wdir is set when exiting
    # the program
    import __main__
    __main__.xxx = []
    launcher_file = None
    use_gl = True
    if len(sys.argv[1:]) >= 1:
        rflag = False
        lflag = False
        eflag = False
        for p in sys.argv[1:]:
            if p == '-h':
                print('[Usage: ifigure -s -r command -h file]')
                print('ifigure          : start a new project')
                print('ifigure <file>   : open an existing project')
                print('-s               : start server thread')
                print('-d               : suppress console redirect')
                print('-c               : completely suppress redirect')
                print('-n               : no main window')
                print('-p               : call profiler')
                print('-r <command>     : run command')
                print('-h               : show this help')
                print('-g               : turn off gl')
                print('-w               : warning on')
                print('-ww              : warning on (error)')
                print('-l <path>        : file to commnicate with launcher ')
                sys.exit()
            elif p == '-s':
                start_server = True
                redirect_std = True
                __main__.process_server_request = False

                server = ifigure.server.Server()
                server.start()
                continue
            elif p == '-e': ## this is backword compatibility (ignored)
                eflag = True
            elif p == '-d':
                use_console = False
                redirect_std = False
                print('debug mode (console is suppressed. all redirect is off')
                continue
            elif p == '-c':
                use_console = False
                print('debug mode (console is suppressed, but thread log  window is on)')
                continue
            elif p == '-n':
                hide_main = True
                continue
            elif p == '-p':
                pr = None
                import cProfile
                print('starting profiler')
                pr = cProfile.Profile()
                pr.enable()
            elif p == '-r':
                rflag = True
            elif p == '-l':
                lflag = True
            elif p == '-g':
                use_gl = False
            elif p == '-w':
                warnings.simplefilter('always')
                print('debug mode (warning is on)')
            elif p == '-ww':
                warnings.simplefilter('error')
                print('debug mode (warning cuases error)')
            else:
                if rflag:
                    if len(p) > 0:
                        p = p.strip()
                        if p.startswith('"'):
                            exe_command = p[1:-1]
                        elif p.startswith("'"):
                            exe_command = p[1:-1]
                        else:
                            exe_command = p
                    if exe_command.strip() == '':
                        exe_command = None
                    rflag = False
                elif lflag:
                    launcher_file = p.strip()
                    lflag = False
                elif eflag:
                    eflag = False
                else:
                    if os.path.exists(p):
                        file = p
                        print(('opening file : '+file))
                        file = os.path.abspath(file)
                    else:
                        show_file_open_error = True
                        filename = p
                        file = None
    from ifigure.widgets.appearance_config import AppearanceConfig
    appearanceconfig = AppearanceConfig()

    import ifigure.widgets.canvas.ifigure_canvas
    import ifigure.matplotlib_mod.backend_wxagg_gl as wxagg_gl
    if use_gl:
        use_gl = appearanceconfig.setting['gl_use']
    if use_gl:
        ifigure.widgets.canvas.ifigure_canvas.turn_on_gl = use_gl
        wxagg_gl.use_gl_12 = appearanceconfig.setting['gl_use_12']
        wxagg_gl.load_glcanvas(debug=True)
    else:
        print('No 3D plot (OpenGL turned off)')

    ifigure.ifigure_app.redirect_std = redirect_std
    ifigure.ifigure_app.use_console = use_console
#   from ifigure.utils.rollback_importer import RollbackImporter as RI
    from ifigure.mto.treedict import fill_td_name_space

    sc = os.path.join(os.path.dirname(ifigure.__file__),
                      'mto', 'treedict_ns.py')
    if os.path.exists(sc):
        fill_td_name_space(sc)
    from ifigure.ifigure_config import rcdir
    sc = os.path.join(rcdir, 'treedict_ns.py')
    if os.path.exists(sc):
        fill_td_name_space(sc)

    app = MyApp(False, clearSigInt=False)
    ifig_app = app.get_ifig_app()

    if show_file_open_error:
        ifig_app.shell.write('### File not found : ' + filename)

    if file is not None:
        if file[-4:] == '.pfz':
            ifig_app.proj_tree_viewer.update_widget()
            #ifig_app.open_file(file, call_close=True)
            # ifig_app.set_proj_saved(True)
            #wx.CallAfter(ifig_app.onOpen, path =file)
            # somehow this seems work, but others may not open
            # figure windows associated to the project file
            wx.CallLater(10, ifig_app.onOpen, path=file)

            #           ifig_app.draw_all()
            # ifig_app.set_filename_2_window_title()
        elif file[-4:] == '.bfz':
            bk = ifig_app.proj.load_subtree(file, compress=True)
            from ifigure.mto.fig_book import FigBook
            if not isinstance(bk, FigBook):
                sys.exit()
            ifig_app.ipage = 0
            bk.setvar("original_filename", file)
#           bk.set_open(True)
            ifig_app.book = bk
#           obk.destroy()
            ifigure.events.SendChangedEvent(bk, w=ifig_app)
            ifigure.events.SendOpenBookEvent(bk, w=ifig_app)
#           ifig_app.show_page(ifig_app.ipage)
        else:
            wx.CallLater(3, ifig_app.onOpenWithHelperCommand,
                         path=file, hide_main=hide_main)
#       ifig_app.open_book_in_appwindow(ifig_app.proj.book1, ipage=0)

    if start_server:
        ifig_app.use_server()
        __main__.process_server_request = True
        port = server.info()[3]
        print('remote port is open : port = ' + str(port) + '\n')

    # call tempdir_clean when ifig_app is being deleted
    class TempdirObj(object):
        pass
    ifig_app._tempdir_obj = TempdirObj()
    from ifigure.ifigure_config import tempdir_clean
    tempdir_ref = weakref.ref(ifig_app._tempdir_obj, tempdir_clean)

    # reduce update events
    wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)

#   if pr is not None:
#      from ifigure.interactive import profile_stop
#      profile_stop(pr, sortby='cumulative')

    if exe_command is not None:
        if hide_main:
            wx.CallAfter(ifig_app.shell.execute_and_hide_main, exe_command)
        else:
            wx.CallAfter(ifig_app.shell.Execute, exe_command)
    if hide_main and exe_command is None:
        # i don't know if this is necessary hide_main and exe_command
        # is used together for normal situation.
        wx.CallAfter(ifig_app.goto_no_mainwindow)
    # conditions for iptyhon
    ifig_app.set_launcher_file(launcher_file)

    from ifigure.widgets.taskbar import TaskBarIcon
    tbicon = TaskBarIcon()

    app.MainLoop()

    server = ifigure.server.Server()
    if server.info()[0]:
        server.stop()

    if not MPTarzip().isReady():
        # seems like it is not necessary since wx.CallLater
        # im MPTarzip makes sure that the program does not
        # come here before save process finishes.

        # anyway, just in case...
        print('waiting for save to be done')
        MPTarzip().worker.join()
    #
    #  deleting the wdir used last moment...
    #
    wdirs = __main__.xxx
    for wdir in wdirs:
        if os.path.exists(wdir):
            print(('deleting :', wdir))
            shutil.rmtree(wdir)
#   MDSWorkerPool(type=worker_mode).reset()
    print('Exiting piScope (main loop finished)')
    from .ifigure_config import tempdir
    if os.path.exists(tempdir) and len(os.listdir(tempdir))==0:
        print(' --- removing workdirectory :' + tempdir)
        os.rmdir(tempdir)
    print(' --- ebug to check if normal exit (list of remaining threads)')
    import threading
    import time
    time.sleep(1)
    for t in threading.enumerate():
        print(" --- "+str(t))
    print(" --- "+str(wx.GetTopLevelWindows()))
