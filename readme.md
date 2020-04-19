## &pi;Scope
&pi;Scope is a python based workbench for data analysis and modeling.
Goal of piScope includes
* To build a data browsing (scope) application for MDSplus data system (www.mdsplus.org)
* To provide lego blocks for gluing up large simulation codes using python

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

&pi;Scope is also used for Petra-M finiete element analysis platform built on MFEM (https://piscope.psfc.mit.edu/index.php/Petra-M)
     
Requirements
*  Python >3.6
*  wxPython 4
*  matplotlib 
*  PyOpenGL
*  ... and others.

Typical pip command list...

```
 pip install wxPython
 pip install matplotlib
 pip install Pillow
 pip install scipy
 pip install hgapi
 pip install PyOpenGL
 pip install netCDF4
 pip install PyPDF2
 pip install pdfrw
 pip install h5py
```

Wiki page : http://piscope.psfc.mit.edu/

Directories:
* ../python/ifigure             core program
* ../python/ifigure/example              examples
* ../bin/                        scripts to run &pi;Scope
* ../example/                   example data to look in &pi;Scope


