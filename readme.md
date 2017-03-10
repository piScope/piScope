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
     
Requirements
*  python 2.7
*  wxPython 3.0.1
*  matplotlib > 1.5
*  PyOpenGL
*  ... and others.
  
Wiki page : http://piscope.psfc.mit.edu/

Directories:
* ../python/ifigure             core program
* ../python/ifigure/example              examples
* ../bin/                        scripts to run &pi;Scope
* ../example/                   example data to look in &pi;Scope


