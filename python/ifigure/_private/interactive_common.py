"""Static help strings for ifigure.interactive wrappers."""

from textwrap import dedent

# Keep raw multiline text here for readability.
_RAW_DOCS = {
    'addpage': '''
        add a page to current book
    ''',
    'annotate': '''
        annotate(s, xy, xytext=None, xycoords='data',
                textcoords='data', arrowprops=None,
                **kargs)
        xycoords, textcoords : 'data', 'figure', 'axes'
          'figure' and 'axes' is from 0 to 1 (fraction)
          other opstions are not supported
    ''',
    'arrow': '''
        arrow : add arrow to current axes

        arrow(x1, y1, x2, y2)
    ''',
    'axline': '''
        axline : axhline or axvline


        axline(x) or axline([x1,x2,x3...])  : vline
        axline([], y) or axline([], [y1,y2,y3...]) : hline
        axline([x1, x2...],[y1, y2...]) : mixed vline and hline

        (note) lines created by one axline commads shares
               color, marker, alpha, and other attirbute.
    ''',
    'axlinec': '''
        axlinec: editable axline
    ''',
    'axspan': '''
        axspan : axhspan or axvspan

        axspan([x1,x2])     : v-span
        axspan([], [y1,y2]) : h-span
        axspan([x1, x2], [y1,y2]) : mixed v-span h-span

        multiple v-span and h-span can be created at once
        axspan([[x1, x2], [x3, x4]...], [[y1,y2], [y3, y4]...])

        (note) artists created by one axspan commands
              shares color, marker, alpha, and other attirbute.
              drag is also applied to all artists.
    ''',
    'axspanc': '''
        axspanc: a user control version of axspan
                 see help(axspan) for the details of argments

                 a user can add/drag/remove the patch object and edit
                 values from GUI
    ''',
    'cauto': '''
        auto scale c
    ''',
    'cbar': '''
        toggle cbar of current plot
            cbar()
            cbar('c2')  # to specify caxis name

        keywords:
            position : position of color bar (normalized to axis)
            size : size of color bar (normalized to axis)
            direction : h or v (horizontal, or vertical)
            lcolor : text color
            lsize : text size
            olcolor : offset text color
            olsize : offset text size

        example:
            cbar(position=(0.1, 0.1), size=(0.7, 0.05), lsize=16,
                 lcolor='red', olsize=19, olcolor='b',direction='h')
    ''',
    'cla': '''
        clear current axis
    ''',
    'clabel': '''
        set caxis label
           clabel(txt)
           clabel(txt, 'c2')
    ''',
    'clf': '''
        clear current page. page annotations are not
        deleted
        isec is moved to 0
    ''',
    'clim': '''
        clim change range of caxis
        example) clim(min, max) , clim((min, max)), or clim([min, max])
    ''',
    'clinear': '''
        set cscale linear
        clinear()
        clinear(False) # makes log scale
    ''',
    'clog': '''
        set ylog
        clog()
        clog(False)
    ''',
    'close':'''
        close()
        close(1)   : close all figure window
        close(all) : close all figure window
    ''',
    'cls': '''
        cls() is the same as clf()
        isec is moved to 0
    ''',
    'cnames': '''
        return list of c axis name of current plot
    ''',
    'contour': '''
        contour : contour line plot  (see also contourf)
        contour(z, n)
        contour(x, y, z, n)
        contour(z, v)
        contour(x, y, z, v)

        n: number of levels
        v: a list of contour levels
    ''',
    'contourf': '''
        contourf : contour fill plot
        contourf(z, n)
        contourf(x, y, z, n)
        contourf(z, v)
        contourf(x, y, z, v)

        n: number of levels
        v: a list of contour levels
    ''',
    'csymlog': '''
        set symlog in c
        [x,y, z, c]symlog(base = None, linthresh = None, linscale = None, name  = 'c')
    ''',
    'ctitle': '''
        set caxis label
           ctitle(txt)
           ctitle(txt, 'c2')
    ''',
    'delpage': '''
        delete current page
    ''',
    'errorbar': '''
        errorbar : xy plot with errorbar

        errorbar(x, y, xerr=xerr, yerr=yerr)

        options for xerr and yerr
            ### assign 0.1 for all points)
            xerr = 0.1
            ### assign different value of error
            xerr = [0.1, 0.2, ....]
            ### assign upper and lower error separately
            xerr = [[0.1, 0.2, ...],[0.4, 0.7...]]

        identical to calling plot with mpl_command = 'errorbar'
    ''',
    'errorbarc': '''
        errorbar creates a line plot similar to errorbar.
        however, it has extra menus to edit points
    ''',
    'figarrow': '''
        figarrow : add arrow to current page

        figarrow(x1, y1, x2, y2)
    ''',
    'figtext': '''
        figtext : add text to current figure

        figtext(x, y, s) : type string s to (x, y)
    ''',
    'figure': '''
        create a new book and open it in a new figure window
             figure()  : open empty figure
             figure('***.bfz') : open book file
             figure(proj.book) : open FigBook object
             figure(1)  : open (or make) book1 under proj
             figure(1, parent)  : open (or make) book1 under parent
    ''',
    'fill': '''
        fill(x, y)
    ''',
    'fill_between': '''
        fill_between(x, y,  y2=[0]*len(x), where=None)
    ''',
    'fill_between_3d': '''
        fill_between_3d(x1, y1, z1, x2, y, z2, c='b')
    ''',
    'fill_betweenx': '''
        fill_betweenx(y, x, x2=[0]*len(y), where=None)
        (note): order of x and y is different from MPL?
    ''',
    'hist': '''
        histgram
    ''',
    'hold': '''
        hold controls if existing plots are deleted bofore
        adding a new one
            hold("on"), hold(1), hold(True)  -> hold is on
            hold("off"),hold(0), hold(False) -> hold is off
    ''',
    'image': '''
        image : show image

        image(z)
        image(x, y, z)
    ''',
    'isec': '''
        isce/isection control current axes.
        if i is give, it sets current axes and returns ax
        otherwize it returns current ax
    ''',
    'isection': '''
        isce/isection control current axes.
        if i is give, it sets current axes and returns ax
        otherwize it returns rrent ax
    ''',
    'ispline': '''
        ispline : xy plot
        ispline(x, y)
    ''',
    'legend': '''
        legend: add legend box to current figure

        legend('label1') : legend for a single artist
        legend(['label1', 'label2']) for multiple aritsts
        legend(['label1', 'label2'], axes2 = True) for multiple aritsts
    ''',
    'lighting': '''
        set lighting of 3D scene (it affects only artists drawn on OpenGL canvas)
          lighting(ambient = 0.4)  : amibient lighting intensity
          lighting(light   = 0.4)  : lighting source intensity
          lighting(light_direction = (1, 0., 1, 0)) : lighting source direction
          lighting(specular = 1.0) : specular reflection intensity
          lighting(light_color = (1.0, 1, 1)) : light source color
          lighting(wireframe = 0)  : #0 normal mode
                                     #1 wireframe + hidden line elimination
                                     #2 wireframe
    ''',
    'loglog': '''
        make loglog plot
        loglog(x, y, s)
    ''',
    'nsec': '''
        nsec is the same as subplot
        see subplot help (type 'subplot(' to show help)
    ''',
    'nsection': '''
        nsection is the same as subplot
        see subplot help (type 'subplot(' to show help)
    ''',
    'oerrorbar': '''
        oerrrobar:
            overplot errorbar
        see errorbar for all arguments
    ''',
    'oplot': '''
        oplot :
            overplot
        see plot for all arguments
    ''',
    'plot': '''
            plot : xy plot

            plot(y)
            plot(x, y)
            plot(y, s)
        `   plot(x, y, s)
            plot(x, y, z)
            plot(x, y, z, cz=True)

            s is a format string. For example 'bo-' means to use blue solid line with
            circle marker. The format string is directly passed to matplotlib.
            See http://piscope.psfc.mit.edu/index.php/Interactive_commands#plot for
            detail

            cz is option to change the color along a line using z.

            When x and y are expression, it evaulate x and y and the answer
            should be 1D data.
            If x and y are given as numbers, following handling
            is done
                  x.ndim == 2 and y.ndmi ==1
                    x is sliced using the first row and multiple lines
                    are generated
                  x.ndim == 1 and y.ndmi ==2
                    y is sliced using the first row and multiple lines
                    are generated
                  x.ndim == 2 and y.ndmi ==2
                    both x and y are sliced using the first row and multiple lines
                    are generated

            see also: errorbar
    ''',
    'plotc': '''
        plotc creates a line plot similar to plot.
        however, it has extra menus to edit points
    ''',
    'property': '''
        property set or get property of target object

          property(obj) : return a list of editable property
          property(obj, name) : get an object property
          property(obj, name, value : set an object property
    ''',
    'quiver': '''
        quiver : quiver plot
        for 2D:
           quiver(u, v)
           quiver(u, v, c)
           quiver(x, y, u, v)
           quiver(x, y, u, v, c)

        for 3D:
           quiver(X, Y, Z, U, V, W, **kwargs)

           X, Y, Z:
               The x, y and z coordinates of the arrow locations (default is
               tip of arrow; see *pivot* kwarg)
           U, V, W:
               The x, y and z components of the arrow vectors
    ''',
    'quiver3d': '''
        quiver3D is threed('on') + quiver
        quiver3D(x, y, z, u, v, w,  cz = False, cdata = None)

        if cz is True and cdata is None, z is used for color
    ''',
    'revolve': '''
        revolve r, z : revolve (r, z) data

          keywords to define revolve
             rcenter: [0,0]
             rtheta:  [0, 2*pi]
             raxis:   [0,  1]
             rmesh:   100.
    ''',
    'savedata': '''
        save dataset as hdf file

          savedate(filename) # filename must be *.hdf
    ''',
    'savefig': '''
        save figure as image

           savefig(filename)

           filename must be one of following
              .eps
              .pdf  (support multipage pdf)
              .svg
              .jpeg
              .png
              .gif  (animation gif)
    ''',
    'scatter': '''
        scatter plot

        scatter(x, y, s = 20, c = 'b')

        s : scalar or array_like (same length as x, y)
            size in points^2.
        c : color or sequence of color
            if c is a 1D array, it is normalized using c-axis range
            c can also be RGBA values (in which rows are RGB or RGBA)
    ''',
    'semilogx': '''
        make semilog (xaxis is log scale) plot
        semilogx(x, y, s)
    ''',
    'semilogy': '''
        make semilog (yaxis is log scale) plot
        semilogy(x, y, s)
    ''',
    'server': '''
        server : control server mode
            server('on') : start server
            server('on', hostname) : start server
                 in this case, server process is binded
                 to hostname, allowing connection over
                 network.
            server('off'): stop server
            server()     : show server information
    ''',
    'showpage': '''
        show ipage
    ''',
    'solid': '''
        solid: plot soild volume complsed by triangle/quad

        solid(v, cz=False, cdata=None, **kargs):
        solid(v, idxset, cz=False, cdata=None, **kargs):

        v : 3D array of verteics
            v[ielement, ivertex,  xyz]
        cz : define color data separately
            when cz =true, 3rd dim of v should be four
            v[ielement, ivertex,  xyzc]

        Using idxset, vertices and index set to define the element shape
        is given separately. v[:, xyz] and idxset[ielement, ivertex]
        will be expanded as if v is v[idexset,...]. This allows to reduce
        the number of vertices passed to GPU

        if third dim is 2:
            v[ielement, ivertex,  xy]
            and
            z needs to be given as zvalue keyword argument

        cdata: used with cz  cdata[ielement, ivertex]

        draw_last : draw this artists last on GL canvas, useful for getting
                    cleanin line smoothing
        facecolor: use solid facecolor
        edgecolor: use solid edgecolor

        example:

           (indexed array)
           ptx = np.array([[0, 0], [0,1], [1,1], [1,0]])
           box = np.array([[0,1,2,3]])
           figure();solid(ptx, box)
    ''',
    'spec': '''
        spectram
        spec(t, v)
        spec(v)
    ''',
    'specgram': '''
        plot spectrogram. Run matplotlib.pyplot.specgram
        and call image using the returnd spectrum.
        keywords are the same as specgram.
    ''',
    'subplot': '''
        set page section format.
           subplot(3)     3 rows
           subplot(1, 3)     3 columns
           subplot(2, 3)  2x3
           subplot(2, 3, (0,1)) 2x3 and (0,1) merged
           subplot(2, 3, (0,1), (2, 3)) 2x3 and (0,1), (2, 3) merged

           'sort' = 'col' or 'column' or 'c' : sort result in column
           'sort' = 'row' or 'r' :             sort result in row

           dx and dy are optional arguments to determine the
           width and height of each column and row
           if these are used, the number of dx and dy should be
           ncol-1, nrow-1, respectively

           example: subplot(2,2, (0,1), dx=0.4)
    ''',
    'suptitle': '''
        set page  title
    ''',
    'surf': '''
        surf or surface : surface plot in 3D
                          using mplot3d
        surf(x, y, z, **kargs):
    ''',
    'surface': '''
        surf/surface : surface plot in 3D
                          using mplot3d
        surf(x, y, z, **kargs):
    ''',
    'text': '''
        text : add text to current axes

        text(x, y, s) : type string s to (x, y)
    ''',
    'threed': '''
        turn on/off three-D axis mode
    ''',
    'timetrace': '''
        timetrace: special plot for time
                   it supports decimation
        timetrace(y)
        timetrace(x, y)
    ''',
    'title': '''
        set section  title
    ''',
    'tricontour': '''
        tri-contour plot

        tricontour(x, y, z, n)
        tricontour(x, y, z, v)
        tricontour(tri, x, y, z, n)
        tricontour(tri, x, y, z, v)
        tri can be evaluated by tri = delaunay(x, y) beforehand
    ''',
    'tricontourf': '''
        tri-contour plot with fill mode

        tricontourf(x, y, z, n)
        tricontourf(x, y, z, v)
        tricontourf(tri, x, y, z, n)
        tricontourf(tri, x, y, z, v)
        tri can be evaluated by tri = delaunay(x, y) beforehand
    ''',
    'tripcolor': '''
        tricolor : show image using triangulation

        tripcolor(z)
        tripcolor(x, y, z)
        tripcolor(tri, z)
        tripcolor(tri, x, y, z)

        tri can be evaluated by tri = delaunay(x, y) beforehand
    ''',
    'triplot': '''
        triplot : plot triangles

        triplot(x, y)
        triplot(x, y, mask = mask, ...)
        triplot(tri, x, y)
    ''',
    'trisurf': '''
        triangle surface plot
        trisurf(z, **kargs):
        trisurf(x, y, z, **kargs):
        trisurf(tri, x, y, z, **kargs):
        trisurf(tri, z, **kargs):
    ''',
    'twinx': '''
        twinx
    ''',
    'twiny': '''
        twinx
    ''',
    'update': '''
       update controls if it draws screen after interactive
       command.
          update('on'), update(1), update(True) : automatic update on
          update('off'), update(0), update(False) : automatic update off
    ''',
    'video': '''
    video viewer is to look video image (3D array)
        video(x, y, z) or video(z)
    ''',
    'videoviewer': '''
    open videoviewer. if bookfile (*.bfz) is passed, it opens the bookfile
    in videoviewer
    ''',
    'view': '''
        set 3D view
           view() : return current setting
           view(elev, azim, upvec)
           view('xy')
           view('yx')
           view('xz')
           view('yz')
           view('default')
           view('frustum')
           view('ortho')
           view('updown')
           view('equal')   # equal aspect ratio
           view('auto')    # auto aspect ratio
           view('clip')
           view('noclip')
    ''',
    'waveviewer':'''
    open waveviewer. if bookfile (*.bfz) is passed, it opens the bookfile
    in waveviewer
    ''',
    'xauto': '''
        auto scale x
    ''',
    'xlabel': '''
        set xaxis label
           xlabel(txt)
           xlabel(txt, name = 'x2')
           xlabel(txt, size=10, color='red')
    ''',
    'xlim': '''
        xlim change range of xaxis

        kargs:
            tposition : tick position ('top', 'bottom')
            ticks : tick values
            tcolor : tick color
            color : text color
            size : text size
            ocolor : offset text color
            osize : offset text size

        example)
            xlim(min, max) , xlim((min, max)), or xlim([min, max])
            xlim([0, 3], size=25, color='red', tcolor='red', ticks=[0,1, 3], tposition='top')
    ''',
    'xlinear': '''
        set xscale linear
        xlinear()
        xlinear(False) # makes log scale
    ''',
    'xlog': '''
        set xlog
        xlog()
        xlog(False)
    ''',
    'xnames': '''
        return list of x axis name of current plot
    ''',
    'xsymlog': '''
        set symlog in x

        [x,y, z, c]symlog(base = None, linthresh = None, linscale = None, name  = 'x')
    ''',
    'xtitle': '''
        set xaxis label
           xtitle(txt)
           xtitle(txt, name = 'x2')
           xtitle(txt, size=10, color='red')
    ''',
    'yauto': '''
        auto scale y
    ''',
    'ylabel': '''
        set yaxis label
           ylabel(txt)
           ylabel(txt, name = 'y2')
           ylabel(txt, size=10, color='red')
    ''',
    'ylim': '''
        ylim change range of yaxis
        kargs:
            tposition : tick position ('left', 'right')
            ticks : tick values
            tcolor : tick color
            color : text color
            size : text size
            ocolor : offset text color
            osize : offset text size

        example)
            ylim(min, max) , ylim((min, max)), or ylim([min, max])
            ylim([0, 3], size=25, color='red', tcolor='red', ticks=[0,1, 3], tposition='left')
    ''',
    'ylinear': '''
        set yscale linear
        ylinear()
        ylinear(False) # makes log scale
    ''',
    'ylog': '''
        set ylog
        ylog()
        ylog(False)
    ''',
    'ynames': '''
        return list of y axis name of current plot
    ''',
    'ysymlog': '''
        set symlog in y
        [x,y, z, c]symlog(base = None, linthresh = None, linscale = None, name  = 'y')
    ''',
    'ytitle': '''
        set yaxis label
           ytitle(txt)
           ytitle(txt, name = 'y2')
           ytitle(txt,  size=10, color='red')
    ''',
    'zauto': '''
        auto scale z
    ''',
    'zlabel': '''
        set zaxis label
           zlabel(txt)
           zlabel(txt, size=10, color='red')
    ''',
    'zlim': '''
        zlim change range of zaxis

        kargs:
            tposition : tick position ('top', 'bottom')
            ticks : tick values
            tcolor : tick color
            color : text color
            size : text size
            ocolor : offset text color
            osize : offset text size

        example) zlim(min, max) , zlim((min, max)), or zlim([min, max])
    ''',
    'zlinear': '''
        set zscale linear
        zlinear()
        zlinear(False) # makes log scale
    ''',
    'zlog': '''
        set zlog
        zlog()
        zlog(False)
    ''',
    'znames': '''
        return list of z axis name of current plot
    ''',
    'zsymlog': '''
        set symlog in z
        [x,y, z, c]symlog(base = None, linthresh = None, linscale = None,  name  = 'z')
    ''',
    'ztitle': '''
        set zaxis label
           ztitle(txt)
           ztitle(txt, size=10, color='red')
    ''',
}

# Exact backend exports from each implementation.
WXAPP_API = [
    'autoplay', 'aviewer', 'check_aviewer', 'clear', 'debug', 'delaunay',
    'draw', 'edit', 'exportv', 'futurize', 'get_axes', 'get_page',
    'get_shellvar', 'get_topwindow', 'glinfo', 'has_petra', 'importv',
    'ipage', 'newbook', 'petram', 'profile', 'server',
    'profile_start', 'profile_stop', 'put_shellvar', 'quit',
    'scope', 'scopenw', 'set_aviewer','setupmodel', 'tscope', 'twinc',
]

NOAPP_API = [
    'check_connection', 'connect', 'detach', 'execute',  'launch', 'shutdown'
]

COMMON_API = [
    'addpage', 'annotate', 'arrow', 'axline', 'axlinec', 'axspan', 'axspanc',
    'cauto', 'cbar', 'cla', 'clabel', 'clf', 'clim', 'clinear', 'clog',
    'close', 'cls', 'cnames', 'contour', 'contourf', 'csymlog', 'ctitle',
    'delpage', 'errorbar', 'errorbarc', 'figarrow', 'figtext', 'figure',
    'fill', 'fill_between', 'fill_between_3d', 'fill_betweenx', 'hist',
    'hold', 'image', 'isec', 'isection', 'ispline', 'legend',
    'lighting', 'loglog', 'nsec', 'nsection', 'oerrorbar', 'oplot',
    'plot', 'plotc', 'property', 'quiver', 'quiver3d',
    'revolve', 'savedata', 'savefig', 'scatter', 'semilogx', 'semilogy',
    'showpage', 'solid', 'spec', 'specgram', 'subplot', 'suptitle',
    'surf', 'surface', 'text', 'threed', 'timetrace', 'title',
    'tricontour', 'tricontourf', 'tripcolor', 'triplot', 'trisurf', 'twinx',
    'twiny', 'update', 'video', 'videoviewer', 'view', 'waveviewer',
    'xauto', 'xlabel', 'xlim', 'xlinear', 'xlog', 'xnames', 'xsymlog', 'xtitle',
    'yauto', 'ylabel', 'ylim', 'ylinear', 'ylog', 'ynames', 'ysymlog', 'ytitle',
    'zauto', 'zlabel', 'zlim', 'zlinear', 'zlog', 'znames', 'zsymlog', 'ztitle',
]

PUBLIC_API = list(dict.fromkeys(COMMON_API + WXAPP_API + NOAPP_API))

# Normalize all entries consistently in one place.
DOCS = {k: dedent(v).strip("\n") for k, v in _RAW_DOCS.items()}
