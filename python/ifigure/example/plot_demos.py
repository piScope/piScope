import numpy as np
import wx


def spec_demo():
    '''
    the demo in matplotlib. But calls
    interactive.specgram
    '''
    from pylab import arange, sin, where, logical_and, randn, pi

    dt = 0.0005
    t = arange(0.0, 20.0, dt)
    s1 = sin(2*pi*100*t)
    s2 = 2*sin(2*pi*400*t)

    # create a transient "chirp"
    mask = where(logical_and(t > 10, t < 12), 1.0, 0.0)
    s2 = s2 * mask

    # add some noise into the mix
    nse = 0.01*randn(len(t))

    x = s1 + s2 + nse  # the signal
    NFFT = 1024       # the length of the windowing segments
    Fs = int(1.0/dt)  # the sampling frequency

    from ifigure.interactive import figure, spec, nsec, plot, isec, clog, hold

    figure()
    hold(True)
    nsec(2)
    isec(0)
    plot(t, x)
    isec(1)
    spec(t, x, NFFT=NFFT, noverlap=900)
    clog()


def specgram_demo():
    '''
    the demo in matplotlib. But calls
    interactive.specgram
    '''
    from pylab import arange, sin, where, logical_and, randn, pi

    dt = 0.0005
    t = arange(0.0, 20.0, dt)
    s1 = sin(2*pi*100*t)
    s2 = 2*sin(2*pi*400*t)

    # create a transient "chirp"
    mask = where(logical_and(t > 10, t < 12), 1.0, 0.0)
    s2 = s2 * mask

    # add some noise into the mix
    nse = 0.01*randn(len(t))

    x = s1 + s2 + nse  # the signal
    NFFT = 1024       # the length of the windowing segments
    Fs = int(1.0/dt)  # the sampling frequency

    from ifigure.interactive import figure, specgram, nsec, plot, isec, clog, hold

    figure()
    hold(True)
    nsec(2)
    isec(0)
    plot(t, x)
    isec(1)
    specgram(x, NFFT=NFFT, Fs=Fs, noverlap=900)
    clog()


def image_demo():
    from ifigure.interactive import image, figure
    x = np.linspace(-5, 5, 41)
    y = np.linspace(-5, 5, 41)
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X*X + Y*Y)
    z = np.cos(r/10.*6*3.14)*np.exp(-r/3)
    figure()
    image(x, y, z)


def image_video_demo():
    from ifigure.interactive import image, figure
    x = np.linspace(-5, 5, 41)
    y = np.linspace(-5, 5, 41)
    X, Y = np.meshgrid(x, y)

    z = []
    for shift in np.linspace(-2., 2, 10):
        r = np.sqrt((X-shift)**2 + Y*Y)
        d = np.cos(r/10.*6*3.14)*np.exp(-r/3)
        z.append(d[np.newaxis, :, :])
    z = np.vstack(z)
    from ifigure.widgets.video_viewer import VideoViewer
    v = figure(viewer=VideoViewer)
    v.image(x, y, z)


def triplot_demo():
    from ifigure.interactive import triplot
    v = np.linspace(0.1, 10, 20)
    t = np.linspace(0, 3.1415, 20)

    V, T = np.meshgrid(v, t)
    x = (V*np.cos(T)).flatten()
    y = (V*np.sin(T)).flatten()

    triplot(x, y)


def tripcolor_demo():
    from ifigure.interactive import tripcolor
    v = np.linspace(0.1, 10, 80)
    t = np.linspace(0, 3.1415, 80)

    V, T = np.meshgrid(v, t)
    x = (V*np.cos(T)).flatten()
    y = (V*np.sin(T)).flatten()
    r = np.sqrt(x*x + y*y)
    z = np.cos(r/10.*6*3.14)*np.exp(-r/3)

    tripcolor(x, y, z)


def tripcolor_phasor_demo():
    from ifigure.interactive import tripcolor
    import time
    v = np.linspace(0.1, 10, 80)
    t = np.linspace(0, 3.1415, 80)

    V, T = np.meshgrid(v, t)
    x = (V*np.cos(T)).flatten()
    y = (V*np.sin(T)).flatten()
    r = np.sqrt(x*x + y*y)
    z = np.exp(1j*r/10.*6*3.14)*np.exp(-r/3)

    p = tripcolor(x, y, z)

    # aviewer import must be here. When there
    # is no window, tripcolor above will create
    # a viewer and aviewer in ifigure.interactive
    # is set.
    from ifigure.interactive import aviewer

    phase = np.linspace(0, np.pi*2, 30)
    for ph in phase:
        p.set_phasor(ph)
        p.get_figaxes().set_bmp_update(False)
        aviewer.draw()
        time.sleep(1)


def tripcolor_phasor_demo2():
    '''
    Example using wave viewer
    '''
    from ifigure.interactive import figure

    v = np.linspace(0.1, 10, 80)
    t = np.linspace(0, 3.1415, 80)

    V, T = np.meshgrid(v, t)
    x = (V*np.cos(T)).flatten()
    y = (V*np.sin(T)).flatten()
    r = np.sqrt(x*x + y*y)
    z = np.exp(1j*r/10.*6*3.14)*np.exp(-r/3)

    from ifigure.widgets.wave_viewer import WaveViewer
    v = figure(viewer=WaveViewer)
    v.tripcolor(x, y, z)


def tricontour_demo(**kwargs):
    from ifigure.interactive import tricontour

    X = np.linspace(-5, 5, 40)
    Y = np.linspace(-5, 5, 40)
    X, Y = np.meshgrid(X, Y)
    R = np.sqrt(X**2 + Y**2)
    Z = np.sin(R)
    tricontour(X, Y, Z, cmap='coolwarm', **kwargs)


def contour_demo(**kwargs):
    from ifigure.interactive import contour

    X = np.linspace(-5, 5, 40)
    Y = np.linspace(-5, 5, 40)
    X, Y = np.meshgrid(X, Y)
    R = np.sqrt(X**2 + Y**2)
    Z = np.sin(R)
    contour(X, Y, Z, cmap='coolwarm', **kwargs)


def scatter_demo(**kwargs):
    from ifigure.interactive import scatter

    x = np.random.random_sample(100)
    y = np.random.random_sample(100)
    c = np.random.random_sample(100)
    s = np.random.random_sample(100)*100+10

    scatter(x, y, c=c, s=s, cmap='coolwarm')


def hist_demo(**kwargs):
    from ifigure.interactive import hist, nsec, isec

    x1 = np.random.random_sample(4000)
    x2 = np.random.random_sample(400)*3
    hist(x1)
    nsec(3)
    isec(1)
    hist([x1, x2])
    isec(2)
    hist(x1.reshape(1000, 4))


def surf_demo(**kwargs):
    from ifigure.interactive import surf, threed

    threed('on')
    X = np.linspace(-5, 5, 40)
    Y = np.linspace(-5, 5, 40)
    X, Y = np.meshgrid(X, Y)
    R = np.sqrt(X**2 + Y**2)
    Z = np.sin(R)
    surf(X, Y, Z, cmap='coolwarm', shade=True, **kwargs)
