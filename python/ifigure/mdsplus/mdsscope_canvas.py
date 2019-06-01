from ifigure.widgets.canvas.ifigure_canvas import ifigure_canvas
from .fig_mds import FigMds
from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod
from ifigure.widgets.undo_redo_history import UndoRedoGroupUngroupFigobj
from ifigure.widgets.undo_redo_history import UndoRedoAddRemoveArtists


def get_figmds(obj):
    p = obj.get_parent()
    while p is not None:
        if isinstance(p, FigMds):
            return p
        p = p.get_parent()
    return p


class MDSScopeCanvas(ifigure_canvas):
    def change_figobj_axes(self, figobj, value, direction):
        if len(self.selection) == 0:
            return
        h = []
        if direction != 'c':
            for a in self.selection:
                h.append(UndoRedoFigobjMethod(a(), 'container_idx', value))
            figmds = get_figmds(a().figobj)
            if figmds is not None:
                if len(figmds._artists) > 0:
                    h.append(UndoRedoFigobjMethod(
                        figmds._artists[0], 'container_idx', value))
        else:
            for a in self.selection:
                h.append(UndoRedoFigobjMethod(a(), 'caxis_idx', value))
        ax = a().axes
        h.append(UndoRedoFigobjMethod(ax, 'adjustrange', None))

        window = self.GetTopLevelParent()
        GlobalHistory().get_history(window).make_entry(h, use_reverse=False)
