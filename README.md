## &pi;Scope
&pi;Scope is a python based workbench for data analysis and modeling.

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
     
### Install

```
 pip install piScope

 or
 
 git clone git@github.com:piScope/piScope.git; cd piScope
 pip install .
```

### LLM sessions

To enable an LLM agent to control a persistent piScope session, copy the
plotting skill into that agent's user skill directory:

```
mkdir -p <LLM_SKILLS_DIR>/piscope-plotting
cp skills/piscope-plotting/SKILL.md <LLM_SKILLS_DIR>/piscope-plotting/
```

The skill documents how to start and send commands to a piScope LLM session.


### Directories

* ../python/ifigure             core program
* ../python/ifigure/example              examples
* ../bin/                        scripts to run &pi;Scope
* ../example/                   example data to look in &pi;Scope

### Reference

(S Shiraiwa, T Fredian, J Hillairet, J Stillerman, "&pi;Scope: Python based scientific workbench with MDSplus data visualization tool", Fusion Engineering and Design 112, 835 (2016) https://doi.org/10.1016/j.fusengdes.2016.06.050)


