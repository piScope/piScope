from __future__ import print_function
#
#    Events for ifigure/treedict object
#
# *******************************************
#     Copyright(c) 2012- S.Shiraiwa
# *******************************************
#
#    2013.11.  post_process_event is added
#              I am little concerned if posting
#              event from thread is safe or not.
#
#              posting event through this routine
#              should be thread safe....?
import time
import os
import threading
from ifigure.widgets.book_viewer import BookViewer
import wx
from ifigure.utils.wx3to4 import deref_proxy
from weakref import ProxyType
import traceback
changed_in_queue = 0


EditFile = wx.NewEventType()
TD_EVT_EDITFILE = wx.PyEventBinder(EditFile, 1)
CloseFile = wx.NewEventType()
TD_EVT_CLOSEFILE = wx.PyEventBinder(CloseFile, 1)
Changed = wx.NewEventType()
TD_EVT_CHANGED = wx.PyEventBinder(Changed, 1)
Var0Changed = wx.NewEventType()
TD_EVT_VAR0CHANGED = wx.PyEventBinder(Var0Changed, 1)
ArtistSelection = wx.NewEventType()
TD_EVT_ARTIST_SELECTION = wx.PyEventBinder(ArtistSelection, 1)
ArtistDragSelection = wx.NewEventType()
TD_EVT_ARTIST_DRAGSELECTION = wx.PyEventBinder(ArtistDragSelection, 1)
ArtistReplace = wx.NewEventType()
TD_EVT_ARTIST_REPLACE = wx.PyEventBinder(ArtistReplace, 1)
ThreadStart = wx.NewEventType()
TD_EVT_THREAD_START = wx.PyEventBinder(ThreadStart, 1)
ShowPage = wx.NewEventType()
TD_EVT_SHOWPAGE = wx.PyEventBinder(ShowPage, 1)
PageShown = wx.NewEventType()
TD_EVT_PAGESHOWN = wx.PyEventBinder(PageShown, 1)
RangeChanged = wx.NewEventType()
TD_EVT_RANGECHANGED = wx.PyEventBinder(RangeChanged, 1)
OpenBook = wx.NewEventType()
TD_EVT_OPENBOOK = wx.PyEventBinder(OpenBook, 1)
CloseBook = wx.NewEventType()
TD_EVT_CLOSEBOOK = wx.PyEventBinder(CloseBook, 1)
FileChanged = wx.NewEventType()
TD_EVT_FILECHANGED = wx.PyEventBinder(FileChanged, 1)
PV_DrawRequest = wx.NewEventType()
PV_EVT_DrawRequest = wx.PyEventBinder(PV_DrawRequest, 1)
PV_DeleteFigobj = wx.NewEventType()
PV_EVT_DeleteFigobj = wx.PyEventBinder(PV_DeleteFigobj, 1)
PV_AddFigobj = wx.NewEventType()
PV_EVT_AddFigobj = wx.PyEventBinder(PV_AddFigobj, 1)
CV_CanvasSelected = wx.NewEventType()
CV_EVT_CanvasSelected = wx.PyEventBinder(CV_CanvasSelected, 1)
InteractiveAxesSelection = wx.NewEventType()
TD_EVT_IAXESSELECTION = wx.PyEventBinder(InteractiveAxesSelection, 1)
NewHistory = wx.NewEventType()
TD_EVT_NEWHISTORY = wx.PyEventBinder(NewHistory, 1)
RemoteCommand = wx.NewEventType()
REMOTE_COMMAND = wx.PyEventBinder(RemoteCommand, 1)
EvtTDDict = wx.NewEventType()
TD_EVT = wx.PyEventBinder(EvtTDDict, 1)
# undo/redo event
EvtUndo = wx.NewEventType()
TD_EVT_UNDO = wx.PyEventBinder(EvtUndo, 1)
EvtRedo = wx.NewEventType()
TD_EVT_REDO = wx.PyEventBinder(EvtRedo, 1)
FileSystemChanged = wx.NewEventType()
TD_EVT_FILESYSTEMCHANGED = wx.PyEventBinder(FileSystemChanged, 1)
CANVAS_DrawRequest = wx.NewEventType()
CANVAS_EVT_DRAWREQUEST = wx.PyEventBinder(CANVAS_DrawRequest, 1)
CloseBookRequest = wx.NewEventType()
TD_EVT_CLOSEBOOKREQUEST = wx.PyEventBinder(CloseBookRequest, 1)
#WorkerStartRequest= wx.NewEventType()
#EVT_WORKER_START_REQUEST = wx.PyEventBinder(WorkerStartRequest, 1)


class TreeDictEvent(wx.PyCommandEvent):
    """
    event for treedict to request edit a file
    """

    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
        self.dt = None
        self.event_name = ''
        self.time = time.time()
        self.BookViewerFrame_Processed = False

    def GetTreeDict(self):
        return self.dt

    def SetTreeDict(self, dt):
        self.dt = dt


def post_process_event(evt, handler, useProcessEvent=False):
    t = threading.current_thread()

    if t.name == 'MainThread':
        if not useProcessEvent:
            #             print 'posting event', evt.event_name
            wx.PostEvent(handler, evt)
        else:
            #             print 'processing event',evt.event_name
            handler.ProcessEvent(evt)
    else:
        if not useProcessEvent:
            wx.PostEvent(handler, evt)
        else:
            wx.CallAfter(handler.ProcessEvent, evt)


def SendSimpleTDEvent(evt, td=None, w=None, useProcessEvent=False, code='', handler=None):
    #    if td.get_root_parent().app is None: return

    if evt is None:
        evt = TreeDictEvent(EvtTDDict, wx.ID_ANY)
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    evt.code = code
    if handler is None:
        handler = wx.GetApp().TopWindow.GetEventHandler()
    post_process_event(evt, handler, useProcessEvent)


def SendSimpleTDEvent2(evt, td=None, w=None, useProcessEvent=False):
    #    if td.get_root_parent().app is None: return

    evt = TreeDictEvent(EditFile, wx.ID_ANY)
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    handler = wx.GetApp().TopWindow.GetEventHandler()
#    handler=td.get_root_parent().app.GetEventHandler()
    post_process_event(evt, handler, useProcessEvent)
#    if useProcessEvent:
#       handler.ProcessEvent(evt)
#    else:
#       wx.PostEvent(handler, evt)


def SendEditFileEvent(td, w=None, file=None, readonly=False):
    #    if td.get_root_parent().app is None: return
    if file is None: return

    handler = td.get_root_parent().app.GetEventHandler()
    evt = TreeDictEvent(EditFile, wx.ID_ANY)
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    evt.file = file
    evt.readonly = readonly
    post_process_event(evt, handler, True)
#    handler.ProcessEvent(evt)


def SendCloseFileEvent(td, w=None, file=None):
    if td.get_root_parent().app is None:
        return
    if file is None: return
    
    handler = td.get_root_parent().app.GetEventHandler()
    evt = TreeDictEvent(CloseFile, wx.ID_ANY)
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    evt.file = file
    post_process_event(evt, handler, True)
#    handler.ProcessEvent(evt)


def SendSelectionEvent(td, w=None, selections=[], multi_figobj=None, 
                       mode='replace', useProcessEvent=True):
    # events sent when figobj is selected
    # selections can be self.selection or self.axes_selection
    if td is None:
        return
    if td.get_root_parent().app is None:
        return

    evt = TreeDictEvent(ArtistSelection,
                        wx.ID_ANY)
    evt.selections = selections
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    evt.event_name = 'selection'
    evt.mode = mode
    evt.multi_figobj=multi_figobj
    handler = td.get_root_parent().app.GetEventHandler()
    post_process_event(evt, handler, useProcessEvent)
#    handler.ProcessEvent(evt)

def SendDragSelectionEvent(td, w=None, selections=[], axes = None, useProcessEvent=True,
                           selected_index = None):
    # events sent when figobj is selected
    # selections can be self.selection or self.axes_selection
    if td is None:
        return
    if td.get_root_parent().app is None:
        return
    
    viewer = w.GetTopLevelParent()
    if viewer is None: return
    
    evt = TreeDictEvent(ArtistDragSelection, wx.ID_ANY)
    evt.selections = selections
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    evt.event_name = 'multiselection'
    evt.mode = 'multi'
    evt.selected_index = selected_index

    handler = viewer.GetEventHandler()    
    post_process_event(evt, handler, useProcessEvent)

def SendReplaceEvent(td, w=None, a1=None, a2=None,
                     hl=False, a1all=None, a2all=None):
    # events sent when figobj replaces its artist
    # this event is processed immediately using
    # process event in order to keep data consisntency

    if td.get_root_parent().app is None:
        return

    app = td.get_root_parent().app
    book = td.get_root_figobj()
    viewer = app.find_bookviewer(book)
    if viewer is None:
        return

    evt = TreeDictEvent(ArtistReplace,
                        wx.ID_ANY)
    evt.a1 = a1
    evt.a2 = a2
    evt.hl = hl
    evt.a1all = a1all
    evt.a2all = a2all
    evt.SetTreeDict(td)
    if w is not None:
        evt.SetEventObject(deref_proxy(w))
    else:
        evt.SetEventObject(viewer)
    handler = viewer.GetEventHandler()
    post_process_event(evt, handler, True)
#    handler.ProcessEvent(evt)


def SendChangedEvent(td, w=None, useProcessEvent=False):
    # print 'sending changed event', td
    # traceback.print_stack()

    # I wanted to avoid issuing this event too many.
    # so it records if this event is already in event
    # queue.
    # However, if the event is not processed properly,
    # this approach could make a dead-lock.
    # Not running mainloop is one such case.
    # there may be a better way to do this...
    if not wx.GetApp().IsMainLoopRunning():
        return

    global changed_in_queue
    try:
        if td.get_root_parent().app is None:
            return
    except:
        return
#    if changed_in_queue: return
#    traceback.print_stack()
    evt = TreeDictEvent(Changed, wx.ID_ANY)
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))

    handler = td.get_root_parent().app.GetEventHandler()
    post_process_event(evt, handler, useProcessEvent)
    changed_in_queue = changed_in_queue + 1


def SendVar0ChangedEvent(td, w=None):
    #    if td.get_root_parent().app is None: return
    if not hasattr(td.get_root_parent(), 'app'):
        return
    if td.get_root_parent().app is None:
        return

    evt = TreeDictEvent(Var0Changed, wx.ID_ANY)
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))

    handler = td.get_root_parent().app.GetEventHandler()
#    handler.ProcessEvent(evt)
    post_process_event(evt, handler, False)
#    wx.PostEvent(handler, evt)
#    wx.Yield()


def SendThreadStartEvent(td, w=None, thread=None, useProcessEvent=False):
    if td.get_root_parent().app is None:
        return

    handler = td.get_root_parent().app.GetEventHandler()
    evt = TreeDictEvent(ThreadStart, wx.ID_ANY)
    evt.thread = thread
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    post_process_event(evt, handler, useProcessEvent)


def SendFileChangedEvent(td, w=None, operation=None, param=None):
    '''
    opeartion 
    1) rename  : param = { "oldname": xxx , "newname": 
    2) delete  : param = { "oldname": xxx }
    '''

    if td.get_root_parent().app is None:
        return

    handler = td.get_root_parent().app.GetEventHandler()
    evt = TreeDictEvent(FileChanged, wx.ID_ANY)
    evt.op = operation
    evt.param = param
    evt.SetTreeDict(td)
    evt.SetEventObject(deref_proxy(w))
    post_process_event(evt, handler, False)
#    wx.PostEvent(handler, evt)


def SendShowPageEvent(td, w=None, inc='0'):
    try:
        app = td.get_root_parent().app
    except:
        return
    if app is None:
        return

    #inc = 1, -1, 'last', 'first'
    evt = TreeDictEvent(ShowPage, wx.ID_ANY)
    evt.SetTreeDict(td)
    if w is None:
        book = td.get_figbook()
        w = app.find_bookviewer(book).canvas
    evt.SetEventObject(deref_proxy(w))
    evt.inc = inc

    if w is None:
        handler = td.get_root_parent().app.GetEventHandler()
    else:
        handler = w
    evt.BookViewerFrame_Processed = False
    post_process_event(evt, handler, True)
#    handler.ProcessEvent(evt)


def SendRangeChangedEvent(td, w=None, name=''):
    evt = TreeDictEvent(RangeChanged, wx.ID_ANY)
    evt.name = name
    SendSimpleTDEvent(evt, td=td, w=w)
    print('send range change event')


def SendOpenBookEvent(td, w=None, viewer=BookViewer, param=None,
                      useProcessEvent=False, ipage=0, size=None, pos=None,
                      isPropShown=None, **kwargs):
    evt = TreeDictEvent(OpenBook, wx.ID_ANY)
    evt.viewer = viewer
    evt.param = param
    evt.ipage = ipage
    evt.size = size
    evt.pos = pos
    evt.isPropShown = isPropShown
    evt.kwargs = kwargs
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=useProcessEvent)


def SendCloseBookEvent(td, w=None):
    evt = TreeDictEvent(CloseBook, wx.ID_ANY)
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=True)


def SendIdleEvent(td, w=None):
    evt = wx.IdleEvent()
    handler = td.get_root_parent().app.GetEventHandler()
    wx.PostEvent(handler, evt)


def SendNewHistoryEvent(td, w=None):
    evt = TreeDictEvent(NewHistory, wx.ID_ANY)
    evt.event_name = 'newhistory'
    SendSimpleTDEvent(evt, td=td, w=w, handler=w.GetTopLevelParent())


def SendPageShownEvent(td, w=None):
    evt = TreeDictEvent(PageShown, wx.ID_ANY)
    SendSimpleTDEvent(evt, td=td, w=w)


def SendPVDrawRequest(td, w=None, wait_idle=False, refresh_hl=False,
                      useProcessEvent=False, caller=''):
    evt = TreeDictEvent(PV_DrawRequest, wx.ID_ANY)
    evt.wait_idle = wait_idle
    evt.refresh_hl = refresh_hl
    evt.caller = caller
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=useProcessEvent)


def SendPVAddFigobj(td, w=None, useProcessEvent=False):
    evt = TreeDictEvent(PV_AddFigobj, wx.ID_ANY)
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=useProcessEvent)


def SendPVDeleteFigobj(td, w=None, useProcessEvent=False):
    evt = TreeDictEvent(PV_DeleteFigobj, wx.ID_ANY)
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=useProcessEvent)


def SendCanvasSelected(td, w=None, useProcessEvent=True):
    evt = TreeDictEvent(CV_CanvasSelected, wx.ID_ANY)
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=useProcessEvent)


def SendInteractiveAxesSelection(td, w=None, callback=None, figaxes=None, handler=None):
    evt = TreeDictEvent(InteractiveAxesSelection, wx.ID_ANY)
    evt.callback = callback
    evt.figaxes = figaxes
    SendSimpleTDEvent(evt, td=td, w=w, handler=handler)


def SendRemoteCommandEvent(td, command=''):
    evt = TreeDictEvent(RemoteCommand, wx.ID_ANY)
    evt.command = command
    SendSimpleTDEvent(evt, td=td)


def SendUndoEvent(td, w=None, name=''):
    evt = TreeDictEvent(EvtUndo, wx.ID_ANY)
    evt.name = name
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=True)


def SendRedoEvent(td, w=None, name=''):
    evt = TreeDictEvent(EvtRedo, wx.ID_ANY)
    evt.name = name
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=True)


def SendFileSystemChangedEvent(td, w=None, name='', reload=True):
    evt = TreeDictEvent(FileSystemChanged, wx.ID_ANY)
    evt.owndir = td.owndir()
    evt.reload = reload
    SendSimpleTDEvent(evt, td=td, w=w, useProcessEvent=False)


def SendCanvasDrawRequest(w, all=False, delay=0.0, refresh_hl=False):
    evt = TreeDictEvent(CANVAS_DrawRequest, wx.ID_ANY)
    evt.all = all
    evt.delay = delay
    evt.refresh_hl = refresh_hl
    SendSimpleTDEvent(evt, w=w, handler=w)


def SendCloseBookRequest(w):
    evt = TreeDictEvent(CloseBookRequest, wx.ID_ANY)
    handler = wx.GetApp().TopWindow
    SendSimpleTDEvent(evt, w=w, handler=handler)
