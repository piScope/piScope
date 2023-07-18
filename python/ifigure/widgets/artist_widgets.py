from __future__ import print_function
#
#   collection of widgets for artists
#
import wx
import weakref
import numpy as np
from ifigure.utils.edit_list import EditListPanel, EDITLIST_CHANGED, ScrolledEditListPanel
from ifigure.utils.cbook import FindFrame

from ifigure.widgets.undo_redo_history import GlobalHistory
from ifigure.widgets.undo_redo_history import UndoRedoArtistProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjProperty
from ifigure.widgets.undo_redo_history import UndoRedoFigobjMethod

from ifigure.mto.fig_text import FigText
from ifigure.mto.fig_axes import FigAxes
from ifigure.mto.fig_axes import FigInsetAxes
from ifigure.mto.fig_axspan import FigAxspan
from ifigure.mto.fig_axline import FigAxline
from ifigure.mto.fig_axlinec import FigAxlineC
from ifigure.mto.fig_plot import FigPlot
from ifigure.mto.fig_contour import FigContour
from ifigure.mto.fig_image import FigImage
from ifigure.mto.fig_page import FigPage
from ifigure.mto.fig_legend import FigLegend
from ifigure.mto.fig_axes import FigColorBar

import ifigure.utils.debug as debug
dprint1, dprint2, dprint3 = debug.init_dprints('ArtistWidgets')

# definition of parameter for edit_list
# listparam[0:3] : parameters to be sent to editlist
# listparam[0]   : label
# listparam[1]   : value
# listparam[2]   : mode
# listparam[3]   : setting
# listparam[4]   : property name
# listparam[5]   :
#    flag : -1: do nothing
#            0: use set_xxx of artist
#           10: use set_xxx of artist (applied to all artists)
#            1: use setp/getp of FigObj
#            2: call method (set_xxx/get_xxx) of FigObj
#               xxx is property name. these methods should
#               have the following signature
#               set_xxx(self, value, artist)
#               get_xxx(self, artist)
#            3: call method (set_xxx/get_xxx) of FigObj
#               extension of flag = 2
#               set_xxx(self, (tab, value), artist)
#               get_xxx(self, artist, tab)
#           12: the same as 2, but bypass history
#           13: the same as 3, but bypass history
# listparam[6] = menu_name
listparam = {}
#s = {"minV": 0.,"maxV": 359., "val" : 90, "res" : 1, "text_box" : False}
s_fontsize = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
              "choices": ["7", "8", "9", "10", "11", "12", "14",
                          "16", "18", "20", "22", "24", "26", "28",
                          "36", "48", "72"]}
s_fontsize2 = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
               "choices": ["default", "7", "8", "9", "10", "11", "12", "14",
                           "16", "18", "20", "22", "24", "26", "28",
                           "36", "48", "72"]}
s_markersize = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                "choices": ["5", "6", "7", "8", "9", "10", "11", "12", "14",
                            "16"]}
s_markeredgewidth = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                     "choices": ["0.5", "1", "2", "3", "4", "5"]}
s_imageinterp = {"style": wx.CB_READONLY,
                 "choices": ["nearest", "linear", "cubic"]}
s_shading = {"style": wx.CB_READONLY,
             "choices": ["flat", "gouraud"]}
s_axxpos = {"style": wx.CB_READONLY, "choices": ["bottom", "top"]}
s_axypos = {"style": wx.CB_READONLY, "choices": ["left", "right"]}
s_splineinterp = {"style": wx.CB_DROPDOWN,
                  "choices": ["linear", "spline"]}
s_multialignment = {"style": wx.CB_DROPDOWN,
                    "choices": ["left", "center", "right"]}


###
listparam["multialignment"] = ["alignment", "left",
                               4,  s_multialignment, 'multialignment', 2]
listparam["spinterp"] = ["interpolation", "spline",
                         4, s_splineinterp, 'sp_interp', 2]
listparam["axxpos"] = ["position", ("bottom", True, True, None),
                       26, s_axxpos, 'ax_pos', 3, 'axpos']
listparam["axypos"] = ["position", ("left", True, True, None),
                       26, s_axypos, 'ax_pos', 3, 'axpos']

listparam["rotation"] = ["rotation", '0',   25,  {}, 'rotation', 0]
listparam["text"] = ["text",         '',  200, {}, 'text', 0]
listparam["legendtitle"] = ["text",         '',  200, {}, 'title', 2]
s = {"text": 'shadow'}
listparam["legendshadow"] = [None,   False,  3, s, 'shadow', 2]

listparam["color"] = ["color",      'red',  6, {}, 'color', 0]
#listparam["linecolor"] = ["color",  'red', 406, {}, 'color', 0]
listparam["ecolor"] = ["color",      'red',  6, {}, 'ecolor', 2]
listparam["alpha"] = ["alpha",       1.0, 105, {}, 'alpha', 0]


listparam["facecolor"] = ["fill",      'red', 106, {}, 'facecolor', 0]
listparam["edgecolor"] = ["edge",      'red',  6, {}, 'edgecolor', 0]
listparam["pedgecolor_2"] = ["edge",     'red', 306, {},  'edgecolor', 2]

listparam["xtcolor"] = ["tick",      'red',  6, {}, 'xtcolor', 2]
listparam["ytcolor"] = ["tick",      'red',  6, {}, 'ytcolor', 2]
listparam["xlcolor"] = ["label",      'red',  6, {}, 'xlcolor', 2]
listparam["ylcolor"] = ["label",      'red',  6, {}, 'ylcolor', 2]

listparam["linewidth"] = ["line width", 2.,  7, {}, 'linewidth', 0]
listparam["linewidthz_0"] = ["line width", 2.,  107, {}, 'linewidth', 0]
listparam["linewidthz"] = ["line width", 2.,  107, {}, 'linewidth', 2]
listparam["elinewidth"] = ["line width", 2.,  7, {}, 'elinewidth', 2]
listparam["linestyle"] = ["line style", 'red',  8, {}, 'linestyle', 0]
listparam["marker"] = ["marker",      'red',  9, {}, 'marker',  0]
listparam["markerfacecolor"] = ["fill",  'red', 106, {}, 'markerfacecolor', 0]
listparam["markeredgecolor"] = ["edge",  'red',  6, {}, 'markeredgecolor', 0]
listparam["markersize"] = ["size",  "6",  104, s_markersize, 'markersize', 0]
listparam["markeredgewidth"] = [
    "edge width",  2.,  7, {}, 'markeredgewidth', 0]
listparam["plinestyle"] = ["line style", 'dotted',  10, {}, 'linestyle', 0]

s = {"text": 'fill'}
listparam["fill"] = ["fill area", True,  3, s, 'fill', 0]
s = {"text": 'closed'}
listparam["closepoly"] = ["closed", True,  3, s, 'closepoly', 2]
s = {"minV": 0., "maxV": 30., "val": 10, "res": 1, "text_box": False}
listparam["contour_nlevel"] = ["level", '0',   24,  s, 'contour_nlevel', 2]
s["expand_space"] = 1
mmm = [[None, '0',   24,  s], ]
mm2 = [[None, '0',  100,  s], ]
listparam["contour_nlevel2"] = ["levels",  (False, ['7'], ['10']), 27,
                                ({"text": 'use expression'},
                                 {"elp": mm2}, {"elp": mmm}),
                                "contour_nlevel2", 2]
mm21 = [['   ',   'red', 106, {}], ]
mm2 = [['size', '10',  104,  s_fontsize],
       [None, (False, ['red']), 27,
        ({"text": 'use fixed color'}, {"elp": mm21})],
       ['inline', True,  3, {'text': 'on'}],
       ['spaceing', '5', 24,
        {"minV": 1., "maxV": 30., "val": 5, "res": 1, "text_box": False}],
       ['format', '%1.3f',   0, {}],
       ['skip', '0', 24,
        {"minV": 0., "maxV": 5., "val": 0, "res": 1, "text_box": True}], ]
init_v = [8.0, (False, [(0.0, 0.0, 0.0, 1.0)]), True, 5.0, u'%1.3f', '0']
s_decimate = {"text": 'on'}
listparam['decimate'] = ["decimate", True,  3, s_decimate, 'decimate', 2]

listparam['clabel_param'] = [None,  (False, init_v), 27,
                             ({"text": 'use labels'}, {"elp": mm2}),
                             "clabel_param", 2]
#listparam["contour_alpha"] =["alpha",  1.0 , 105, {}, 'alpha', 1]
s = {"text": 'fill'}
listparam["contour_fill"] = ["fill area", True,  3, s, 'contour_fillmode', 2]
s = {"text": 'shade'}
listparam["surf_shade"] = ["shade", True,  3, s, 'shade', 2]
s = {"minV": 5., "maxV": 30., "val": 12, "res": 1, "text_box": False}
listparam["size"] = ["size", "12",  104,  s_fontsize, 'size', 0]
listparam["textsize"] = ["size", "12",  104,  s_fontsize, 'size', 1]
listparam["xlsize"] = ["size", "12",  104,  s_fontsize, 'xlsize', 2]
listparam["ylsize"] = ["size", "12",  104,  s_fontsize, 'ylsize', 2]

listparam["cmap"] = ["color map", 3, 12, {}, 'cmap', 2]
listparam["cmap3"] = ["color map", 3, 12, {}, 'cmap3', 3, 'cmap']

listparam["caxis"] = ["color axis", 'c', 28, None, 'selected_caxis', 2]
listparam["image_interp"] = ["interpolation", "linear",
                             4, s_imageinterp, 'interp', 2]
listparam["tripcolor_shading"] = ["interpolation", "flat",
                                  4, s_shading, 'shading', 1]

s_shading2 = {"style": wx.CB_READONLY,
              "choices": ["flat", "linear"]}
listparam["solid_shade"] = ["interpolation", "flat", 4, s_shading2,
                            "shade", 2]
s = {"values": ['data', 'axes']}
listparam["switchtrans"] = ["coord",        0, 1, s, 'switchtrans', 2]
s = {"values": ['data', 'axes', 'figure'], "orientation": 'vertical'}
listparam["inset_switchtrans"] = ["coord",        0, 1, s, 'switchtrans', 2]
listparam["inset_size"] = ["size(x, y, w, h)",     '', 0, {}, 'insetsize', 2]
listparam["title"] = ["title",        None,  115, {}, 'title', 2]
s = {"values": ['auto', 'equal']}
listparam["aspect"] = ["aspect",        0,  1, s, 'aspect', 2]
s = {"text": 'suppress clipping by 3D cut-plane'}
listparam["noclip3d"] = [None,        0,  3, s, 'noclip3d', 1]
s = {"text": 'show'}
listparam["frame"] = ["frame",        0,  3, s, 'frame_on', 0]
listparam["axis"] = ["axis",        0,  3, s, 'axis_onoff', 2]
listparam["xlabel"] = ["label",      None,   15, {}, 'xlabel', 2]
listparam["ylabel"] = ["label",      None,   15, {}, 'ylabel', 2]

listparam["xscale"] = ["scale", 'linear',  14,  None, 'xscale', 2]
listparam["yscale"] = ["scale", 'linear',  14,  None, 'yscale', 2]
listparam["xrange"] = ["range", ('0', '1'),  13,  None, 'xlim', 2]
listparam["yrange"] = ["range", ('0', '1'),  13,  None, 'ylim', 2]
s = {"text": 'on'}
listparam["fancybox"] = ["fancybox", True,  3, s, 'fancybox', 1]
listparam["fbalpha"] = ["alpha",      1.0, 105, {}, 'fbalpha', 1]
listparam["fbcolor"] = ["face",      'red',  6, {}, 'fbcolor', 1]
listparam["fbecolor"] = ["edge",   'red',  6, {}, 'fbecolor', 1]
s = {"style": wx.CB_READONLY,
     "choices": ["larrow", "rarrow", "round", "round4",
                 "roundtooth", "sawtooth", "square"]}
listparam["fbstyle"] = ["shape", 'square',  4, s, 'fbstyle', 1]
s = {"minV": 0.1, "maxV": 0.7, "val": 0.3, "res": 0.05, "text_box": False}
listparam["fbpad"] = ["pad", 0.3,   24,  s, 'fbpad', 1]
listparam["arrowstyle"] = ["", 'simple',   16,  None, 'arrowstyle', 2]
listparam["mdssource"] = [None, None,   18,  None, 'mdssource', 2]
s = {"style": wx.CB_READONLY,
     "choices": ["plot", "contour", "image", "axline", "axspan"]}
listparam["mdsfiguretype"] = [None,  'plot',  31, s, 'mdsfiguretype', 12]
listparam["mdsrange"] = [None,  ((False, (-1, 1)),
                                 (False, (-1, 1))),
                         32, None, 'mdsrange', 2]
#listparam["mdstxt"]   = [None,   'This is a MDSplus data object',  2,   {}, None, -1]
listparam["mdsevent"] = ["update",   '',  0,   {}, 'mdsevent',  2]
s = {"style": wx.CB_READONLY,
     "choices": ["circle", "ellipse"]}
listparam["circle_type"] = ["type", 'circle',  4, s, 'circletype', 2]
s = {"style": wx.TE_PROCESS_ENTER,
     "choices": ["0", "30", "45", "60", "90", "120", "135",
                 "150", "180"]}
listparam["circle_angle"] = ["angle", 0,  104, s, 'circleangle', 2]
s = {"style": wx.CB_READONLY,
     "choices": ["square", "rectangle"]}
listparam["box_type"] = ["type", 'square',  4, s, 'boxtype', 2]

#listparam["legendlabelcolor"] = ["color",  'red',  6, {}, 'legendlabelcolor', 3]
#listparam["legendlabel"]  = ["text",         '',   0, {}, 'legendlabel', 3]
s1 = {"style": wx.CB_READONLY,
      "choices": ["serif", "sans-serif",
                  "cursive", "fantasy", "monospace", "default"]}
s2 = {"style": wx.CB_READONLY,
      "choices": ["ultralight", "light", "normal",
                  "regular", "book", "medium",
                  "roman", "semibold", "demibold",
                  "demi", "bold", "heavy",
                  "extra bold", "black", "default"]}
s3 = {"style": wx.CB_READONLY,
      "choices": ["normal", "italic", "oblique", "default"]}
s4 = {"style": wx.TE_PROCESS_ENTER,
      "choices": ["5", "7", "8", "9", "12", "15",
                  "18", "20", "24", "36", "48"]}


listparam["cxclipunder"] = ["Under", (False, 'white'), 38,  ({"text": "Clip"}, {}),
                            'cxclipunder', 3, 'clipunder']
listparam["cxclipover"] = ["Over",  (False, 'white'),   38, ({"text": "Clip"}, {}),
                           'cxclipover',  3, 'clipover']

s = {"elp": (("text",   '',     0, {}),
             ("color",  'red',  6, {}),)}

ss = {"elp": (("font",   'default',  4, s1,),
              ("weight", 'default',  4, s2,),
              ("style",  'default',  4, s3,),
              ("size",     10,      104,  s4),)}

listparam["legendloc"] = [None, '',   19,  None, 'legendloc', 2]
listparam["legendentry"] = [None,  (-1, ('1',),
                                    (('', 'red'),)),
                            227, s, 'legendentry', 2]
listparam["legendlabelprop"] = [None,
                                ('default', 'default', 'default', 12),
                                33, ss, 'legendlabel_prop', 2]


s_spec_nfft = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
               "choices": ["64", "128", "256", "512", "1024", "2048", "4096",
                           "8192", "16384"]}
s_spec_nfft16 = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                 "choices": ["16", "32", "64", "128", "256", "512", "1024", "2048", "4096",
                             "8192", "16384"]}
s_spec_nfft_none = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                    "choices": ["none", "64", "128", "256", "512", "1024", "2048", "4096",
                                "8192", "16384"]}
s_spec_window = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                 "choices": ["none", "hanning", "hamming", "blackman", "bartlett"]}
s_spec_sided = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                "choices": ["onesided", "twosided"]}
s_spec_detrend = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
                  "choices": ["none", "mean", "linear"]}
elp_spec_fftp = [["NFFT", "256",  104,  s_spec_nfft],
                 ["PadTo", "256",  104,  s_spec_nfft_none]]
listparam["spec_fftp"] = [None, ("256", "256"),  33,  {
    "elp": elp_spec_fftp}, 'spec_fftp', 2]
listparam["spec_noverlap"] = ["Overlap", "128",
                              104,  s_spec_nfft16, 'spec_noverlap', 2]
listparam["spec_window"] = ["Window", "hanning",
                            4,  s_spec_window, 'spec_window', 2]
listparam["spec_sided"] = ["Sides", "onesided",
                           4,  s_spec_sided, 'spec_sides', 2]
listparam["spec_detrend"] = ["Detrend", "none",
                             4,  s_spec_detrend, 'spec_detrend', 2]

listparam["axrangeparam13"] = [None,    None,
                               20, {}, 'axrangeparam13', 13, 'axrangeparam']
listparam["axrangeparam13o"] = [None,    None,   20, {'check_range_order': True},
                                'axrangeparam13', 13, 'axrangeparam']
listparam["axcrangeparam13"] = [None,    None,   20, {'check_range_order': True},
                                'axcrangeparam13', 13, 'axcrangeparam']

s2 = {"style": wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER,
      "choices": ["default", "scalar", "scalar(mathtext)", "log",  "log(mathtext)", "log(exp)",
                  "none"]}

listparam["axformat"] = ["format", "default",  4,  s2, 'axformat', 3]
listparam["axlabel"] = ["label",      None,  115, {}, 'axlabel', 3]
listparam["axlsize"] = ["size", "12",   104,  s_fontsize2, 'axlsize', 3]
listparam["axotsize"] = ["size", "12",   104,  s_fontsize2, 'axotsize', 3]
listparam["axlotsize"] = ["size", "12",   42,  s_fontsize2, 'axlotsize', 3]
listparam["axtcolor"] = ["tick", 'red', 206, {}, 'axtcolor', 3]

listparam["axlcolor"] = ["label", None, 506, {}, 'axlcolor', 3]
listparam["axtlcolor"] = [None,  None, 606, {}, 'axtlcolor', 3]
listparam["axticks"] = ["tick loc", 'Auto', 37, {}, 'axticks', 3]

listparam["axis_bgedgenone"] = [None, "background",  2,  {}, 'none',  -1]
listparam["axis_bgcolor"] = ["face", 'red', 206, {}, 'axis_bgfacecolor', 2]
listparam["axis_bgedgecolor"] = [
    "edge",   'red', 206, {}, 'axis_bgedgecolor', 2]
listparam["axis_bglinewidth"] = [
    "width",     0, 107, {}, 'axis_bglinewidth', 2]
listparam["axis_bglinestyle"] = [
    "style",   'solid', 10, {}, 'axis_bglinestyle', 2]
listparam["axis_bgalpha"] = ["alpha",       1.0, 105, {}, 'axis_bgalpha', 2]
listparam["axis3d_bgcolor"] = ["b.g.(3D)", ('grey', 'grey', 'grey'),
                               23, {}, 'axis3d_bgcolor', 2]
listparam["axis3d_bgalpha"] = ["alpha(3D)", "1",
                               105, {}, 'axis3d_bgalpha', 2]
s1 = {"style": wx.CB_READONLY,
      "choices": ["serif", "sans-serif",
                  "cursive", "fantasy", "monospace"]}
s2 = {"style": wx.CB_READONLY,
      "choices": ["ultralight", "light", "normal",
                  "regular", "book", "medium",
                  "roman", "semibold", "demibold",
                  "demi", "bold", "heavy",
                  "extra bold", "black"]}
s3 = {"style": wx.CB_READONLY,
      "choices": ["normal", "italic", "oblique"]}
listparam["fontfamily"] = ["font",    s1["choices"][0], 4,
                           s1, 'fontfamily', 1]
listparam["fontweight"] = ["weight",  s2["choices"][0], 4,
                           s2, 'fontweight', 1]
listparam["fontstyle"] = ["style",   s3["choices"][0], 4,
                          s3, 'fontstyle',  1]
listparam["epsscale"] = ["scale",   (True, True, 100, 100), 29,
                         None, 'epsscale',  2]

listparam["anchor"] = ["anchor",   (0, 0), 30,  None, 'anchor',  2]
listparam["arrowstyle"] = ["", 'simple',   16,  None, 'arrowstyle', 2]

sscale_setting = {"minV": 0.1, "maxV": 20., "val": 1.0,
                  "res": 0.01, 'motion_event': True}
listparam["scatter_sscale"] = ["size", 1.0, 124, sscale_setting, 'sscale', 2]

mm = [[None, 'simple',  16, None], ]
listparam["curvearrow1"] = [None,  (False, ['simple']), 27,
                            ({"text": 'show arrow1'}, {"elp": mm}), 'curvearrow1', 2]
listparam["curvearrow2"] = [None,  (False, ['simple']), 27,
                            ({"text": 'show arrow2'}, {"elp": mm}), 'curvearrow2', 2]
# make "_2" version
name_ones = ("color", "linestyle", "linewidth",
             "marker", "alpha", "fill", "facecolor",
             "edgecolor", "plinestyle",
             "markerfacecolor", "markeredgecolor",
             "markersize", "markeredgewidth")
# for quivers
s3 = {"style": wx.CB_READONLY,
      "choices": ["xy", "uv"]}
listparam["qangles"] = ["angles",    s1["choices"][0], 4, s3, 'angles',  2]
s = {"minV": 1., "maxV": 8., "val": 5, "res": 1, "text_box": False}
listparam["qheadlength"] = ["headlength", '1',   300,  {}, 'headlength', 2]
listparam["qheadaxislength"] = [
    "headaxislength", '1',   24,  s, 'headaxislength', 2]
listparam["qheadwidth"] = ["headwidth", '1',   24,  s, 'headwidth', 2]

spivot = {"style": wx.CB_READONLY,
          "choices": ["tail", "mid", "tip"]}
listparam["qpivot"] = ["pivot", spivot['choices'][0],   4,
                       spivot, 'pivot', 2]
listparam["q3dlength"] = ["length", 1.,   300, {}, 'q3dlength', 2]
listparam["q3dratio"] = ["length ratio", '0.3',   24,
                         {"minV": 0.05, "maxV": 0.9, "val": 0.3, "res": 0.01,
                          "text_box": False}, 'q3dratio', 2]

# page and axes properties.
# property editor treat these differently.
listparam["bgcolor"] = ["color", 'white', 6, {}, 'facecolor', 0]
# 8 is used in property command and call with nodelete=True
listparam["page_title_size"] = ["titlesize", 12, 104, {}, 'title_size', 8]
listparam["page_ticklabel_size"] = [
    "ticklabel_size", 12, 104, {}, 'ticklabel_size', 8]
listparam["page_axeslabel_size"] = [
    "axeslabel_size", 12, 104, {}, 'axeslabel_size', 8]
listparam["page_axesbox_width"] = [
    "axesbox_width", 1, 104, {}, 'axesbox_width', 8]
listparam["page_axestick_width"] = [
    "axestick_width", 1, 104, {}, 'axestick_width', 8]

listparam["gl_lighting"] = [None,   None, 40,  None, 'gl_lighting',  2]
listparam["gl_view"] = [None,   None, 44,  None, 'axes3d_viewparam',  2]

for name in name_ones:
    v = [x for x in listparam[name]]
    v[5] = 2
    listparam[name + "_2"] = v

# add default undo/redo menu name
# note : this menu name is used also in property commannd
for key in listparam:
    if len(listparam[key]) == 6:
        if key[-2:] == '_1':
            name = key[:-2]
        elif key[-2:] == '_2':
            name = key[:-2]
        else:
            name = key
        listparam[key].append(name)


def call_getter(artist, ll, tab=''):
    sw = ll[5]
#             sw = self.list[k][i][5]
    if sw > 9:
        sw = sw-10
    if sw == 0:
        try:
            m = getattr(artist, 'get_'+ll[4])
            return m()
        except AttributeError:
            return None
        except:
            import traceback
            traceback.print_exc()
            return None
#             elif sw == 10:
#                m = getattr(artist, 'get_'+self.list[k][i][4])
#                value[i] = m()
    elif sw == 1:
        return artist.figobj.getp(ll[4])
    elif sw == 2:
        m = getattr(artist.figobj, 'get_'+ll[4])
        return m(artist)
    elif sw == 3:
        m = getattr(artist.figobj, 'get_'+ll[4])
        return m(artist, tab)
######


class base_artist_widget(object):
    def __init__(self, target_type=1):
        self.target_artist = None
        self.target_artist_mul = None   # multiple selection
        self.target_type = target_type  # 1: first aritst 0: any artist
        self.target_figobj = None
        self.target_figobj_type = ''

    def set_value(self,  artist=None, value=None):
        # this shouuld define how to update
        # gui based on the data in ifigure_canvas
        pass

        #   def get_value(self,  artist=None):
        # pass
        # this shouuld define how to update

        # ifigure_canvas based on GUI

    def set_artist_property(self, evt):
        # routine to set property of artist based on
        # evt happend on aritst_widgets
        print(("debug", "set_artist_property", self))
        pass

    def set_target_artist(self, a, td=None):
        self.target_artist = weakref.ref(a)
        if td is None:
            td = a.figobj
        self.target_figobj = weakref.ref(td)

    def set_target_artist_mul(self, sels):
        if len(sels) > 1:
            self.target_artist_mul = sels
        else:
            self.target_artist_mul = None

    def get_target_artist(self):
        if self.target_artist is None:
            return None
        return self.target_artist()

    def replace_target_artist(self, evt):

        a1 = evt.a1
        a2 = evt.a2

#       print  'here', a1, a2, self.target_type, self
        td = evt.GetTreeDict()
        if self.target_type == 1:
            if td is self.target_figobj():
                self.set_target_artist(a2, td)
#            self.target_artist() = a2
#            self.target_figobj = td
        elif self.target_type == 0:
            if self.target_artist() is a1:
                self.set_target_artist(a2, td)
#            self.target_artist = a2
#            self.target_figobj = td

    def onEL_Changed(self, evt):
        evt.artist_panel = self
        evt.Skip()


class artist_panel(wx.Panel):
    #  define setter/getter for a panel made by
    #  two editlist panels
    #   def __init__(self, *args, **kargs):
    #       print 'artist_panel__init__'
    #       wx.Panel.__init__(self, *args, **kargs)
    def make_panel(self):
        self.target_artist = None
        self.elp = [None]*len(self.list)
        if (self.tab[0]) != '':
            nb = wx.Notebook(self)
            self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onNBChanged)

        else:
            nb = wx.Panel(self, wx.ID_ANY)
            nb.SetSizer(wx.BoxSizer(wx.VERTICAL))

        i = 0

        for list in self.list:
            self.elp[i] = ScrolledEditListPanel(nb, [x[0:4] for x in list])
            # self.elp[i].SetScrollRate(0,5)
            if (self.tab[0]) != '':
                #          if len(self.list) != 1 :
                nb.AddPage(self.elp[i], self.tab[i])
                # self.elp[i].SetScrollRate(0,5)
                # self.elp[i].SetupScrolling()
            else:
                nb.GetSizer().Add(self.elp[i], 1,
                                  wx.EXPAND, 0)
            i = i+1
        if (self.tab[0]) != '':
            nb.ChangeSelection(0)
#       if len(self.list) > 1: nb.ChangeSelection(0)
        pansizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(pansizer)
        pansizer.Add(nb, 1, wx.EXPAND | wx.ALL,
                     0)
        self.Layout()
        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        self.Layout()
        self.Enable(False)
        self.nb = nb

    def Enable(self, value):
        wx.Panel.Enable(self, value)
        for elp in self.elp:
            elp.Enable(value)

    def build_editlist_list(self, obj, ret):
        self.target_figobj_type = type(obj)
        if isinstance(ret, tuple):
            tab = ret[0]
            props = ret[1]
        else:
            tab = ['']
            props = [ret]

        ret = []

        for plist in props:
            l = []
            for p in plist:
                l.append(listparam[p])
            ret.append(l)
#       if tab is None:
#          return ret
#       else:
        return tab, ret

    def set_value(self, artist):
        #
        #   artist/figobj -> palette
        #
        if not isinstance(artist.figobj, self.target_figobj_type):
            return

        self.adjust_elp(artist)
        for k in range(len(self.list)):
            if not self.elp[k].IsEnabled():
                continue
            value = ['']*len(self.list[k])
            for i in range(len(value)):
                if self.list[k][i][4] == 'none':
                    value[i] = self.list[k][i][1]
                    continue

                if len(self.tab) > k:
                    value[i] = call_getter(
                        artist, self.list[k][i], self.tab[k])
                else:
                    value[i] = call_getter(artist, self.list[k][i])

                sw = self.list[k][i][5]
                if sw > 9:
                    sw = sw-10
                if sw == 0:
                    m = getattr(artist, 'get_'+self.list[k][i][4])
                    value[i] = m()
                elif sw == 1:
                    value[i] = artist.figobj.getp(self.list[k][i][4])
                elif sw == 2:
                    m = getattr(artist.figobj, 'get_'+self.list[k][i][4])
                    value[i] = m(artist)
                elif sw == 3:
                    m = getattr(artist.figobj, 'get_'+self.list[k][i][4])
                    value[i] = m(artist, self.tab[k])
            self.elp[k].SetValue(value)

    def set_artist_property(self, evt):
        #
        #   palette -> artist/figobj
        #
        #   artist/figobj will be modified in an
        #   undoalbe way using undo_redo_history
        #
        from ifigure.utils.cbook import isDescendant

        if self.target_artist is None:
            return None, None
        if self.target_artist() is None:
            return None, None
        if self.target_artist().figobj is None:
            self.target_artist = None
            return None, None
        c = 0
        for elp in self.elp:
            if isDescendant(elp, evt.GetEventObject()):
                k = c
                break
            c = c+1

        value = self.elp[k].GetValue()
        i = evt.widget_idx

        name = self.list[k][i][4]
        tab = self.tab[k]
        v = value[i]
        actions = []
        targets = ([self.target_artist] if self.target_artist_mul is None
                   else self.target_artist_mul)
        if self.list[k][i][5] == 0:
            for t in targets:
                action = UndoRedoArtistProperty(t(), name, v)
                actions.append(action)

        elif self.list[k][i][5] == 1:
            for t in targets:
                action = UndoRedoFigobjProperty(t(), name, v)
                actions.append(action)
        elif self.list[k][i][5] == 2:
            for t in targets:
                action = UndoRedoFigobjMethod(t(), name, v)
                actions.append(action)
        elif self.list[k][i][5] == 3:
            action = UndoRedoFigobjMethod(self.target_artist(),
                                          name, v)
            action.set_extrainfo(tab)
            actions.append(action)
        elif self.list[k][i][5] == 12:
            # print self.target_artist()
            m = getattr(self.target_artist().figobj, 'set_'+name)
            m(v, self.target_artist())
            return None, None
        elif self.list[k][i][5] == 13:
            m = getattr(self.target_artist().figobj, 'set_'+name)
            m((tab, v), self.target_artist())
            return None, None
        return actions, self.list[k][i][6]

    def add_action_to_history(self, evt, actions, name=''):
        window = evt.GetEventObject().GetTopLevelParent()
        hist = GlobalHistory().get_history(window)
        if hist is None:
            dprint1('!!! window does not have history!!!', window)
            return
        hist.make_entry(actions, menu_name='edit ' + name)

    def get_selected_page_text(self):
        i = self.nb.GetSelection()
        return self.nb.GetPageText(i)

    def set_selected_page_by_name(self, name):
        i = 0
        while i < self.nb.GetPageCount():
            txt = self.nb.GetPageText(i)
            if str(txt) == str(name):
                self.nb.SetSelection(i)
                return
            i = i+1

    def get_page_texts(self):
        return [str(self.nb.GetPageText(i))
                for i in range(self.nb.GetPageCount())]

    def adjust_elp(self, artist):
        pass

    def onNBChanged(self, evt):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            self.GetTopLevelParent().deffered_force_layout()
        evt.Skip()


class artist_image_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_image_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_image as fig_image
        obj = fig_image.FigImage([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_spec_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_spec_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_spec as fig_spec
        obj = fig_spec.FigSpec([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_contour_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_contour_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_contour as fig_contour
        obj = fig_contour.FigContour([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()
        self.target_type = 0

    def Enable(self, value):
        #       print 'enabling contour widget'
        wx.Panel.Enable(self, value)
        for elp in self.elp:
            elp.Enable(value)
        if not value:
            return
        if self.target_artist is None:
            return
        if self.target_artist() is None:
            return
        self.adjust_elp(self.target_artist())

    def set_value(self, artist):
        if type(artist.figobj) != self.target_figobj_type:
            print("wrong target")
            return
        self.adjust_elp(artist)
        return artist_panel.set_value(self, artist)

    def adjust_elp(self, artist):
        from matplotlib.collections import PathCollection
        from matplotlib.collections import LineCollection

        if isinstance(artist, PathCollection):
            self.elp[-2].Enable(True)
            self.elp[-1].Enable(False)
        else:
            self.elp[-2].Enable(False)
            self.elp[-1].Enable(True)


class artist_box_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_box_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_box as fig_box
        obj = fig_box.FigBox()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_circle_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_circle_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_circle as fig_circle
        obj = fig_circle.FigCircle()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_curve_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_curve_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_curve as fig_curve
        obj = fig_curve.FigCurve()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_spline_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_spline_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_spline as fig_spline
        obj = fig_spline.FigSpline([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_surface_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_surface_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        from ifigure.mto.fig_surface import FigSurface
        obj = FigSurface([0], [0], [0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_trisurface_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_trisurface_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        from ifigure.mto.fig_trisurface import FigTrisurface
        obj = FigTrisurface([0], [0], [0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_axline_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_axline_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axline as fig_axline
        obj = fig_axline.FigAxline([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_axlinec_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_axlinec_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axlinec as fig_axlinec
        obj = fig_axlinec.FigAxlineC([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_axspan_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_axspan_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axspan as fig_axspan
        obj = fig_axspan.FigAxspan([0, 1])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_axspanc_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_axspanc_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axspanc as fig_axspanc
        obj = fig_axspanc.FigAxspanC([0, 1])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_tripcolor_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_tripcolor_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_tripcolor as fig_tripcolor
        obj = fig_tripcolor.FigTripcolor([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_triplot_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_triplot_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_triplot as fig_triplot
        obj = fig_triplot.FigTriplot([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_scatter_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_scatter_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_scatter as fig_scatter
        obj = fig_scatter.FigScatter([0], [0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_timetrace_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_timetrace_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        from ifigure.mto.fig_plot import TimeTrace
        obj = TimeTrace([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_stepplot_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_stepplot_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        from ifigure.mto.fig_plot import StepPlot
        obj = StepPlot([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_plot_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_plot_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_plot as fig_plot
        obj = fig_plot.FigPlot([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()

    def set_value(self, artist):
        if type(artist.figobj) != self.target_figobj_type:
            return
        self.elp[0].Enable(True)
        self.elp[1].Enable(True)
        if artist.figobj._mpl_cmd == 'errorbar':
            self.elp[2].Enable(True)
        if artist.figobj._mpl_cmd == 'plot':
            self.elp[2].Enable(False)
#       self.elp[0].IsEnabled()

        from ifigure.mto.fig_plot import CZLineCollection
        if artist.figobj.getvar('cz'):
            self.Freeze()
            self.elp[0].Enable(True)  # set false of first two item
            self.elp[0].Enable([False, False])  # set false of first two item
            self.elp[1].Enable(False)
            self.Thaw()
        super(artist_plot_widget, self).set_value(artist)


class artist_plotc_widget(artist_plot_widget):
    def __init__(self, parent, *args):
        super(artist_plot_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_plotc as fig_plotc
        obj = fig_plot.FigPlotC([0, 0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_text_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_text_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_text as fig_text
        obj = fig_text.FigText('')
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_hist_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_hist_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_hist as fig_hist
        obj = fig_hist.FigHist(np.arange(100))
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_eps_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_eps_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_eps as fig_eps
        obj = fig_eps.FigEPS()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_quiver_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        import numpy as np
        super(artist_quiver_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_quiver as fig_quiver
        obj = fig_quiver.FigQuiver(np.array([[1, 1], [1, 1]]),
                                   np.array([[1, 1], [1, 1]]))
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_quiver3d_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        import numpy as np
        super(artist_quiver3d_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_quiver as fig_quiver
        obj = fig_quiver.FigQuiver3D(np.array([[1, 1], [1, 1]]),
                                     np.array([[1, 1], [1, 1]]),
                                     np.array([[1, 1], [1, 1]]),
                                     np.array([[1, 1], [1, 1]]),
                                     np.array([[1, 1], [1, 1]]),
                                     np.array([[1, 1], [1, 1]]))
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_legend_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_legend_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        obj = FigLegend()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_legendtext_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_legendtext_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_legendtext as fig_legendtext
        obj = fig_legendtext.FigLegendText()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_arrow_widget(artist_panel,  base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_arrow_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_arrow as fig_arrow
        obj = fig_arrow.FigArrow()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_arrange_widget(wx.Panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_arrange_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        list = [["", 'this is fake arrage palette', 1],
                ["text", '', 0],
                ["color", 'red', 0]]
        box = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(box)
        self.elp = EditListPanel(self, list)
        box.Add(self.elp, 1, wx.EXPAND)


class artist_axes_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, obj=None, *args):
        super(artist_axes_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axes as fig_axes
        if obj is None:
            obj = fig_axes.FigAxes()
        ret = obj.property_in_palette_axes()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_insetaxes_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_insetaxes_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axes as fig_axes
        obj = fig_axes.FigInsetAxes()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_colorbar_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_colorbar_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axes as fig_axes
        obj = fig_axes.FigColorBar()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_colorbar_axes_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_colorbar_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_axes as fig_axes
        obj = fig_axes.FigColorBar()
        ret = obj.property_in_palette_axes()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_mdssource_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_mdssource_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mdsplus.fig_mds as fig_mds
        obj = fig_mds.FigMds()
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_fill_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_fill_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_fill as fig_fill
        obj = fig_fill.FigFill([0])
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_solid_widget(artist_panel, base_artist_widget):
    def __init__(self, parent, *args):
        super(artist_solid_widget, self).__init__(parent, *args)
        base_artist_widget.__init__(self)
        import ifigure.mto.fig_solid as fig_solid
        obj = fig_solid.FigSolid(np.zeros((3, 3, 3)))
        ret = obj.property_in_palette()
        self.tab, self.list = self.build_editlist_list(obj, ret)
        self.make_panel()


class artist_widgets(wx.Panel):
    def __init__(self, parent, *args):
        super(artist_widgets, self).__init__(parent, *args)

        vbox = wx.BoxSizer(wx.HORIZONTAL)
        #vbox = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vbox)
        self.panels = {}
        for key in self.panels:
            self.panels[key].Hide()

#       self.panels[mode].Show()
#       self.GetSizer().Add(self.panels[mode], 1, wx.EXPAND)
        self.mode = ''
        self.artist = None
        self.Bind(EDITLIST_CHANGED, self.onEL_Changed)
        self.Enable(False)

    def build_panels(self, plist):
        for name, cls in plist:
            self.panels[name] = cls(self)

    def switch_panel(self, mode):

        if mode not in self.panels:
            return False
        if self.mode == mode:
            return True
        if self.mode != '':
            self.panels[self.mode].Hide()
            self.GetSizer().Detach(self.panels[self.mode])

        try:
            '''just in case'''
            self.GetSizer().Detach(self.panels[mode])
            self.panels[mode].Hide()
        except:
            print('cannnot remove')
        self.GetSizer().Add(self.panels[mode], 1, wx.EXPAND)
        for p in self.panels:
            self.panels[p].Hide()
        self.panels[mode].Show()
#       self.panels[mode].Layout()
        self.mode = mode

        FindFrame(self).Layout()
        return True

    #   self.Fit()
    def enable(self, val=True):
        self.Enable(val)
        if self.mode != '':
            self.panels[self.mode].Enable(val)

    def onTD_Replace(self, evt):
        for mode in self.panels:
            if self.panels[mode].target_artist is None:
                continue
            if self.panels[mode].target_artist() is None:
                continue
            self.panels[mode].replace_target_artist(evt)


class panel1(artist_widgets):
    plist = [('text', artist_text_widget),
             #               ('legendtext', artist_legendtext_widget),
             ('legend', artist_legend_widget),
             ('image', artist_image_widget),
             ('spec', artist_spec_widget),
             ('contour', artist_contour_widget),
             ('tricontour', artist_contour_widget),
             ('axline', artist_axline_widget),
             ('axlinec', artist_axlinec_widget),
             ('axspan', artist_axspan_widget),
             ('axspanc', artist_axspanc_widget),
             ('spline', artist_spline_widget),
             ('insetaxes', artist_insetaxes_widget),
             ('colorbar', artist_colorbar_widget),
             ('curve', artist_curve_widget),
             ('arrow', artist_arrow_widget),
             ('box', artist_box_widget),
             ('circle', artist_circle_widget),
             #               ('arrange', artist_arrange_widget),
             #               ('mdsplus', artist_mdssource_widget),
             ('plot', artist_plot_widget),
             ('plotc', artist_plot_widget),
             ('timetrace', artist_timetrace_widget),
             ('stepplot', artist_stepplot_widget),
             ('fill', artist_fill_widget),
             ('surface', artist_surface_widget),
             ('revolve', artist_surface_widget),
             ('trisurface', artist_trisurface_widget),
             ('tripcolor', artist_tripcolor_widget),
             ('triplot', artist_triplot_widget),
             ('eps', artist_eps_widget),
             ('quiver', artist_quiver_widget),
             ('quiver3d', artist_quiver3d_widget),
             ('hist', artist_hist_widget),
             ('scatter', artist_scatter_widget),
             ('solid', artist_solid_widget), ]

    try:
        import ifigure.mdsplus
        plist.append(('mdsplus', artist_mdssource_widget))
    except:
        pass

    plistd = {}
    for name, cls in plist:
        plistd[name] = cls

    def __init__(self, parent, quick, *args):
        super(panel1, self).__init__(parent, *args)

        if not quick:
            self.build_panels(panel1.plist)
        else:
            self.build_panels([panel1.plist[0]])
        self.artists = None

    def append_panel(self, mode):
        self.panels[mode] = panel1.plistd[mode](self)
        self.panels[mode].Show()
        self.panels[mode].Layout()

    def update_panel(self, mode=None):
        focus = self.FindFocus()
        if mode is None:
            mode = self.mode
        if self.artists is None:
            self.enable(False)
            return
        if len(self.artists) == 0:
            self.enable(False)
            return
        if self.artists[0]() is None:
            self.enable(False)
            return
        if self.artists[0]().figobj is None:
            self.artists = None
            self.enable(False)
            return
#        print self.artists[0]().figobj.get_figpage()
#        print self.GetTopLevelParent().canvas._figure.figobj
        if (self.artists[0]().figobj.get_figpage() is not
                self.GetTopLevelParent().canvas._figure.figobj):
            self.enable(False)
            return
        if mode in self.panels:
            if self.mode == mode:
                self.enable(True)
            self.panels[mode].set_value(self.artists[0]())
            self.panels[mode].set_target_artist(self.artists[0]())
            self.panels[mode].set_target_artist_mul(self.artists)
        if focus is not None:
            focus.SetFocus()

    def change_artist_panel(self, figobj):
        name = figobj.get_namebase()

        if name not in self.panels:
            if name in panel1.plistd:
                self.append_panel(name)
            else:
                self.enable(False)
                return

        self.switch_panel(name)
        self.enable(True)
        self.update_panel(name)

    def onTD_Selection(self, evt):
        if len(evt.selections) == 1:
            sel = evt.selections[0]()
            if sel is None:
                return
            if sel.figobj is None:
                return
            self.artists = evt.selections
            self.change_artist_panel(sel.figobj)

        elif len(evt.selections) == 0:
            # no selection -> disable
            self.enable(False)
        else:
            # multiple selection
            #  only enabled when all artists has same type of figobj
            #  and in the same axes
            self.enable(False)
            if any([obj() is None for obj in evt.selections]):
                return
            if any([obj().figobj is None for obj in evt.selections]):
                return

            figobjs = [obj().figobj for obj in evt.selections]
            parents = [obj().figobj.get_parent() for obj in evt.selections]

            if any([type(figobjs[0]) != type(obj) for obj in figobjs]):
                return
            if any([parents[0] is not p for p in parents]):
                return

            sel = evt.selections[0]()
            self.artists = evt.selections
            self.change_artist_panel(sel.figobj)

            self.enable(True)

    def onEL_Changed(self, evt):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)

        actions, name = evt.artist_panel.set_artist_property(evt)
        if actions is None:
            return
        evt.artist_panel.add_action_to_history(evt, actions, name)
#       self.GetTopLevelParent().canvas.draw()


class panel2(artist_widgets):
    def __init__(self, parent, *args, **kwargs):
        super(panel2, self).__init__(parent, *args, **kwargs)

        wd = artist_axes_widget(self)
        mode = 'ax'+'.'.join(wd.tab)
        self.panels = {mode: wd}
        self.mode = ''
        self.ax = None
        self._ax_tab = 'common'
        self._cb_tab = 'common'
        self._target_3d = False

    def mode_name(self, figobj):
        tab, item = figobj.property_in_palette_axes()
        if isinstance(figobj, FigColorBar):
            mode = 'cb'+'.'.join(tab)
        else:
            mode = 'ax'+'.'.join(tab)
        return mode

    def append_new_panel(self, figaxes):
        if self.mode in self.panels:
            self._ax_tab = self.panels[self.mode].get_selected_page_text()
        for p in self.panels:
            self.panels[p].Hide()
            self.GetSizer().Detach(self.panels[p])
        mode = self.mode_name(figaxes)
        self.panels[mode] = artist_axes_widget(self, obj=figaxes)
        self.panels[mode].set_selected_page_by_name(self._ax_tab)
        self.panels[mode].Enable(True)

    def update_panel(self):
        focus = self.FindFocus()
        if self.ax is None:
            return
        if self.ax() is None:
            self.enable(False)
            return
        if self.ax().figobj is None:
            self.ax = None
            self.enable(False)
            return

        self._ax_tab = self.panels[self.mode].get_selected_page_text()
        mode_name = self.mode_name(self.ax().figobj)

        if self.mode != mode_name:
            if not mode_name in self.panels:
                self.append_new_panel(self.ax().figobj)
            self.switch_panel(mode_name)
            self.Layout()

        self.panels[mode_name].set_target_artist(self.ax())
        self.panels[mode_name].set_value(self.ax())

        pos = [elp.GetViewStart() for elp in self.panels[mode_name].elp]
        self.panels[mode_name].set_selected_page_by_name(self._ax_tab)
        for p, elp in zip(pos, self.panels[mode_name].elp):
            elp.Scroll(p)
        self.enable(True)
        if focus is not None:
            focus.SetFocus()

    def onTD_Selection(self, evt):
        if not hasattr(evt.GetEventObject(), "axes_selection"):
            return
        axes = evt.GetEventObject().axes_selection
        disable = False
        if axes is None:
            disable = True
        elif axes() is None:
            disable = True
        elif not hasattr(axes(), "figobj"):
            disable = True
        elif axes().figobj is None:
            disable = True

        if disable:
            self.enable(False)
            return
        self.enable(True)

        if isinstance(evt.GetTreeDict(), FigPage):
            return
        if len(evt.GetTreeDict()._artists) == 0:
            self.ax = None
            self.enable(False)
            return

        ax = evt.GetTreeDict()._artists[0].axes
        if ax is None:
            self.ax = None
            self.enable(False)
        else:
            self.ax = weakref.ref(ax)
            self.enable(True)
            if self.mode in self.panels:
                self._ax_tab = self.panels[
                    self.mode].get_selected_page_text()

            self.update_panel()

    def set_axes(self, ax):
        if ax is None:
            self.ax = None
            self.enable(False)
        else:
            self.ax = weakref.ref(ax)
            self.enable(True)

    def onEL_Changed(self, evt):
        tw = wx.GetApp().TopWindow
        if tw.appearanceconfig.setting['generate_more_refresh']:
            wx.CallAfter(self.Update)

        actions, name = evt.artist_panel.set_artist_property(evt)
        if actions is None:
            return
        if hasattr(evt, 'signal'):
            if evt.signal == 'need_adjustscale':
                actions.append(UndoRedoFigobjMethod(self.ax(),
                                                    'adjustrange', None))
        evt.artist_panel.add_action_to_history(evt, actions, name)
        self.GetTopLevelParent().canvas.draw()
        if self.mode in self.panels:
            self._ax_tab = self.panels[
                self.mode].get_selected_page_text()
        # do I need this????
        # self.update_panel()
