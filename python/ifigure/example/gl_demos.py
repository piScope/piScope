import numpy as np

def image_demo():
   from ifigure.interactive import image, threed, figure, hold

   figure(gl = True)
   threed('on')
   hold('on')    
   X = np.linspace(-5, 5, 40)
   Y = np.linspace(-5, 5, 40)
   X, Y = np.meshgrid(X, Y)
   R = np.sqrt(X**2 + Y**2)
   Z = np.sin(R)    
   image(Z, cmap='coolwarm', im_center = [0,0,1])
   image(Z, cmap='coolwarm', im_center = [0,0,1],
         im_axes = ([0,0,1], [0,1,0]))
   image(Z, cmap='coolwarm', im_center = [0,0,1],
         im_axes = ([1/np.sqrt(2), 0,1/np.sqrt(2)],
                    [0, 1, 0]))

def surf_demo(**kwargs):
   from ifigure.interactive import surf, threed, figure, hold

   figure(gl = True)
   threed('on')
#   X = np.arange(-5, 5, 0.25)
#   Y = np.arange(-5, 5, 0.25)
   X = np.linspace(-5, 5, 40)
   Y = np.linspace(-5, 5, 40)
   X, Y = np.meshgrid(X, Y)
   R = np.sqrt(X**2 + Y**2)
   Z = np.sin(R)    
   surf(X, Y, Z, cmap='coolwarm', **kwargs)
#  Debug to draw flat plane....   
#   hold(1)
#   surf(np.array([-5.0,-5, -5.0]), np.array([-5, 0, 5]), np.array([[1,0, -1],[1, 0, -1],[1, 0, -1]]), cmap='coolwarm', **kwargs)
#   surf(np.array([5.0, 5, 5.0]), np.array([-5, 0, 5]), np.array([[1,0, -1],[1, 0, -1],[1, 0, -1]]), cmap='coolwarm', **kwargs)      


def surf_demo2(**kwargs):   
   from mpl_toolkits.mplot3d import Axes3D
   import numpy as np

   from ifigure.interactive import surf, threed, figure

   figure(gl = True)
   threed('on')
   u = np.linspace(0, 2 * np.pi, 100)
   v = np.linspace(0, np.pi, 100)

   x = 10 * np.outer(np.cos(u), np.sin(v))
   y = 10 * np.outer(np.sin(u), np.sin(v))
   z = 10 * np.outer(np.ones(np.size(u)), np.cos(v))
   surf(x, y, z, rstride=4, cstride=4,  color='b')

def contour_demo(**kwargs):
    import mpl_toolkits.mplot3d.axes3d as axes3d
    from ifigure.interactive import contour, threed, figure
    X, Y, Z = axes3d.get_test_data(0.05) 
    v = figure(gl = True)
    threed('on')
    contour(X, Y, Z)

def contourf_demo(**kwargs):
    import mpl_toolkits.mplot3d.axes3d as axes3d
    from ifigure.interactive import contourf, threed, figure
    X, Y, Z = axes3d.get_test_data(0.05) 
    v = figure(gl = True)
    threed('on')
    contourf(X, Y, Z)

def contour_demo2(**kwargs):
    import mpl_toolkits.mplot3d.axes3d as axes3d
    from ifigure.interactive import contourf, threed, figure, hold
    X, Y, Z = axes3d.get_test_data(0.05) 
    v = figure(gl = True)
    threed('on')
    hold('on')
    contourf(X, Y, Z)    
    contourf(X, Y, Z, zdir = 'x', offset = -40)

def revolve_demo(**kwargs):
    m = np.linspace(0, np.pi*2, 30)
    r = 1.0 + 0.2*np.cos(m)
    z = 0.25 * np.sin(m)
    from ifigure.interactive import revolve, figure, threed
    v = figure(gl = True)
    threed('on')
    revolve(r, z, raxis = [0.5, 1], rtheta = [0, 2*np.pi/3])
    v.xlim(-1.5, 1.5)
    v.ylim(-1.5, 1.5)
    v.zlim(-1.5, 1.5)    

 
def solid_demo(**kwargs):
    from stl import mesh
    from ifigure.interactive import solid, figure, threed
    import ifigure, os
    from os.path import dirname
    path = dirname(dirname(dirname(ifigure.__file__)))
    mymesh = mesh.Mesh.from_file(os.path.join(path, 'example', 'D_antenna.stl'))
    v = figure()
    threed('on')
    solid(mymesh.vectors, alpha = 0.5, **kwargs)

def solid_demo2(**kwargs):
    '''
      solid_demo2(cz = True, linewidths = 1.0, edgecolor='red')
      solid_demo2(facecolor='b', linewidths = 1.0, edgecolor='red')

    '''
    from ifigure.interactive import solid, figure, threed
    import ifigure, os

    # preparing the data, the same as mplot3d demo
    theta = np.linspace(0, 2.0 * np.pi, endpoint=True, num=50)
    r = np.linspace(0.01, 4.0, endpoint=True, num=50)
    # This is the Mobius mapping, taking a u, v pair and returning an x, y, z
    # triple
    THETA, R = np.meshgrid(theta, r)
    X = R*np.cos(THETA)
    Y = R*np.sin(THETA)
    Z = np.exp(- R*R)

    import matplotlib.tri as mtri
    tri = mtri.Triangulation(X.flatten(), Y.flatten())
    # Triangulate parameter space to determine the triangles

    if 'cz' in kwargs and kwargs['cz']: 
        v = np.dstack((tri.x[tri.triangles], 
                   tri.y[tri.triangles],
                   Z.flatten()[tri.triangles],))
        kwargs['cdata'] =  5*Z.flatten()[tri.triangles]
        kwargs['cz'] = True

        # or #
        v = np.dstack((tri.x[tri.triangles], 
                   tri.y[tri.triangles],
                   Z.flatten()[tri.triangles],
                   5 * Z.flatten()[tri.triangles],))
    elif 'twod' in kwargs and kwargs['twod']: 
        v = np.dstack((tri.x[tri.triangles], 
                   tri.y[tri.triangles]),)
        kwargs.pop('twod')
        kwargs['zvalue'] = 1.0
    else:
        v = np.dstack((tri.x[tri.triangles], 
                   tri.y[tri.triangles],
                   Z.flatten()[tri.triangles],))

    viewer = figure()
    threed('on')
    solid(v, **kwargs)


def trisurf3d_gl_demo(**kwargs):
    from matplotlib import cm
    import numpy as np
    from ifigure.interactive import figure, threed, trisurf   

    # preparing the data, the same as mplot3d demo
    n_angles = 36
    n_radii = 8
    radii = np.linspace(0.125, 1.0, n_radii)
    angles = np.linspace(0, 2*np.pi, n_angles, endpoint=False)
    angles = np.repeat(angles[...,np.newaxis], n_radii, axis=1)
    x = np.append(0, (radii*np.cos(angles)).flatten())
    y = np.append(0, (radii*np.sin(angles)).flatten())
    z = np.sin(-x*y)

    v = figure()
    threed('on')
    #return v.get_axes()._artists[0].plot_trisurf(x, y, z, cmap=cm.jet, linewidth=0.2)
    trisurf(x, y, z, cmap=cm.jet, linewidth=0.2)

def trisurf3d_demo2(**kwargs): 
    import numpy as np
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.tri as mtri
    from ifigure.interactive import figure

    # preparing the data, the same as mplot3d demo
    u = (np.linspace(0, 2.0 * np.pi, endpoint=True, num=50) * np.ones((10, 1))).flatten()
    v = np.repeat(np.linspace(-0.5, 0.5, endpoint=True, num=10), repeats=50).flatten()
    # This is the Mobius mapping, taking a u, v pair and returning an x, y, z
    # triple
    x = (1 + 0.5 * v * np.cos(u / 2.0)) * np.cos(u)
    y = (1 + 0.5 * v * np.cos(u / 2.0)) * np.sin(u)
    z = 0.5 * v * np.sin(u / 2.0)
    # Triangulate parameter space to determine the triangles
    tri = mtri.Triangulation(u, v)
    
    v = figure(gl = True)
    v.nsec(2)
    v.isec(0)
    v.threed('on')
    v.trisurf(x, y, z, triangles=tri.triangles, cmap=plt.cm.Spectral)

    # First create the x and y coordinates of the points.
    n_angles = 36
    n_radii = 8
    min_radius = 0.25
    radii = np.linspace(min_radius, 0.95, n_radii)

    angles = np.linspace(0, 2*np.pi, n_angles, endpoint=False)
    angles = np.repeat(angles[...,np.newaxis], n_radii, axis=1)
    angles[:,1::2] += np.pi/n_angles

    x = (radii*np.cos(angles)).flatten()
    y = (radii*np.sin(angles)).flatten()
    z = (np.cos(radii)*np.cos(angles*3.0)).flatten()

    # Create the Triangulation; no triangles so Delaunay triangulation created.
    triang = mtri.Triangulation(x, y)

    # Mask off unwanted triangles.
    xmid = x[triang.triangles].mean(axis=1)
    ymid = y[triang.triangles].mean(axis=1)
    mask = np.where(xmid*xmid + ymid*ymid < min_radius*min_radius, 1, 0)
    triang.set_mask(mask)

    v.isec(1)
    v.threed('on')
    v.trisurf(triang, z, cmap=plt.cm.CMRmap)


def quiver_demo(**kwargs):
   '''
   quiver_demo(length = 1.0, 
               normalize = True,
               facecolor = 'b',
               edgecolor = None,
               arrow_length_ratio = 0.3,
               shaftsize = 0.01,
               headsize = 0.01)    

   '''
   from ifigure.interactive import quiver, threed, figure
   
   x, y, z = np.meshgrid(np.arange(-0.8, 1, 0.2),
                      np.arange(-0.8, 1, 0.2),
                      np.arange(-0.8, 1, 0.8))

   u = np.sin(np.pi * x) * np.cos(np.pi * y) * np.cos(np.pi * z)
   v = -np.cos(np.pi * x) * np.sin(np.pi * y) * np.cos(np.pi * z)
   w = (np.sqrt(2.0 / 3.0) * np.cos(np.pi * x) * np.cos(np.pi * y) *
     np.sin(np.pi * z))

   figure()
   threed('on')
   quiver(x, y, z, u, v, w, **kwargs)
