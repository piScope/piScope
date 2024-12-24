## &pi;Scope
&pi;Scope is a python based workbench for data analysis and modeling.
(S Shiraiwa, T Fredian, J Hillairet, J Stillerman, "&pi;Scope: Python based scientific workbench with MDSplus data visualization tool", Fusion Engineering and Design 112, 835 (2016) https://doi.org/10.1016/j.fusengdes.2016.06.050)

Goal of piScope includes
* Data browsing (scope) application for MDSplus data system (www.mdsplus.org)
* Lego blocks for gluing up large simulation codes using python
* User frontend platform for Petra-M (MFEM based finite element simulation).

and for the above purposes, &pi;Scope is equipped with
* a data analysis environment (= python shell, editor, data structure browser, and matplotlib figure)
* various GUI componetns to work with matplotlib based figures which allows to 
 * save/load a figure as a figure file.
 * edit artists using GUI palette for plot, contour, image, triplots and so on.
 * change panel layout via an interactive layout editor
 * cut/paste of plot, axes, or an entire page.
 * export data from plot to python shell by one click
 * interactively annotate figure using text, arrow, lines,,,
 * draw 3D (OpenGL) in matplotlib canvas.

&pi;Scope is also used for Petra-M finiete element analysis platform built on MFEM.
     
Requirements
*  Python >3.6
*  wxPython 4.2
*  matplotlib 3.6.2
*  PyOpenGL
*  ... and others.

Typical pip command list...

```
 pip install attrdict
 pip install wxPython
 pip install piScope
```

Directories:
* ../python/ifigure             core program
* ../python/ifigure/example              examples
* ../bin/                        scripts to run &pi;Scope
* ../example/                   example data to look in &pi;Scope


