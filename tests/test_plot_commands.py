'''
Plotting command smoke tests for piScope interactive API.
'''

import pytest
import ifigure.interactive as interactive
import numpy as np
import traceback


ALL_PLOTTING_COMMANDS = [
    'plot', 'loglog', 'semilogy', 'semilogx', 'plotc', 'errorbar', 'errorbarc',
    'triplot', 'contour', 'contourf', 'scatter', 'hist', 'tricontour',
    'tricontourf', 'image', 'quiver', 'quiver3d', 'specgram', 'spec',
    'tripcolor', 'axline', 'axlinec', 'axspan', 'axspanc', 'text', 'arrow',
    'figarrow', 'figtext', 'legend', 'fill', 'fill_between', 'fill_betweenx',
    'fill_between_3d', 'surf', 'surface', 'revolve', 'trisurf', 'solid',
    'timetrace',
]


# Commands in this group are executed in CI-style smoke tests.
CORE_SMOKE_COMMANDS = [
    'plot', 'timetrace', 'loglog', 'semilogy', 'semilogx', 'plotc',
    'errorbar', 'errorbarc', 'scatter', 'hist', 'image', 'contour',
    'contourf', 'quiver', 'specgram', 'fill', 'fill_between', 'fill_betweenx',
    'text', 'arrow', 'figtext', 'legend',
]


# Deferred commands are intentionally excluded from automatic smoke execution
# until dedicated argument fixtures are prepared.
DEFERRED_COMMANDS = [
    'triplot', 'tricontour', 'tricontourf', 'quiver3d', 'spec', 'tripcolor',
    'axline', 'axlinec', 'axspan', 'axspanc', 'figarrow', 'fill_between_3d',
    'surf', 'surface', 'revolve', 'trisurf', 'solid',
]


def check_prop_read(obj):
    print('read property test :' + str(obj))
    props = interactive.property(obj)
    ret = {}
    for prop in props:
        try:
            val = interactive.property(obj, prop)
            print(str(prop) + ' : ' + str(val))
        except:
            print('reading '+str(prop) + ' failed')
            traceback.print_exc()
            return ret
        ret[prop] = val
    return ret


def check_prop_write(obj, data):
    print('write property test :' + str(obj))
    for prop in data:
        try:
            print(str(prop) + ' : ' + str(data[prop]))
            interactive.property(obj, prop, data[prop])
        except:
            print('writinging '+str(prop) + ' failed')


def _sample_data():
    x = np.linspace(0.0, 1.0, 32)
    y = np.sin(2.0*np.pi*x)
    y2 = np.cos(2.0*np.pi*x)

    xg = np.linspace(-1.0, 1.0, 20)
    yg = np.linspace(-1.0, 1.0, 24)
    X, Y = np.meshgrid(xg, yg)
    Z = np.sin(np.pi*X) * np.cos(np.pi*Y)

    u = np.cos(np.pi*X)
    v = np.sin(np.pi*Y)
    return x, y, y2, X, Y, Z, u, v


def _run_smoke_cases(v, cases):
    failures = []
    for name, fn in cases:
        try:
            fn(v)
        except Exception as exc:
            failures.append((name, str(exc)))

    if failures:
        lines = ['{}: {}'.format(name, err) for name, err in failures]
        raise AssertionError('plotting smoke failures:\n' + '\n'.join(lines))


@pytest.fixture(scope='module')
def piscope_session():
    try:
        interactive.launch()
    except Exception as exc:
        pytest.skip('piScope session could not be launched: {}'.format(exc))

    yield

    try:
        interactive.shutdown()
    except Exception:
        pass


def test_plotting_command_inventory():
    core = set(CORE_SMOKE_COMMANDS)
    deferred = set(DEFERRED_COMMANDS)
    all_cmd = set(ALL_PLOTTING_COMMANDS)

    overlap = core.intersection(deferred)
    assert len(overlap) == 0, 'overlap in command groups: {}'.format(sorted(overlap))

    covered = core.union(deferred)
    missing = sorted(all_cmd.difference(covered))
    extra = sorted(covered.difference(all_cmd))
    assert len(missing) == 0, 'commands missing from matrix: {}'.format(missing)
    assert len(extra) == 0, 'unknown commands in matrix: {}'.format(extra)


def test_plotting_command_presence():
    missing = [name for name in ALL_PLOTTING_COMMANDS
               if not hasattr(interactive, name)]
    assert len(missing) == 0, 'missing interactive plotting commands: {}'.format(missing)


def test_plotting_smoke_core_commands(piscope_session):
    x, y, y2, X, Y, Z, u, v2 = _sample_data()
    qx = X[::4, ::4]
    qy = Y[::4, ::4]
    qu = u[::4, ::4]
    qv = v2[::4, ::4]

    cases = [
        ('plot', lambda vv: vv.plot(x, y)),
        ('timetrace', lambda vv: vv.timetrace(x, y)),
        ('loglog', lambda vv: vv.loglog(x + 0.1, np.abs(y) + 0.1)),
        ('semilogy', lambda vv: vv.semilogy(x + 0.1, np.abs(y) + 0.1)),
        ('semilogx', lambda vv: vv.semilogx(x + 0.1, y)),
        ('plotc', lambda vv: vv.plotc(x, y)),
        ('errorbar', lambda vv: vv.errorbar(x, y, yerr=0.1*np.ones_like(y))),
        ('errorbarc', lambda vv: vv.errorbarc(x, y, yerr=0.1*np.ones_like(y))),
        ('scatter', lambda vv: vv.scatter(x, y)),
        ('hist', lambda vv: vv.hist(y, bins=10)),
        ('image', lambda vv: vv.image(Z)),
        ('contour', lambda vv: vv.contour(X, Y, Z)),
        ('contourf', lambda vv: vv.contourf(X, Y, Z)),
        ('quiver', lambda vv: vv.quiver(qx, qy, qu, qv)),
        ('specgram', lambda vv: vv.specgram(y)),
        ('fill', lambda vv: vv.fill(x, y)),
        ('fill_between', lambda vv: vv.fill_between(x, y, y2)),
        ('fill_betweenx', lambda vv: vv.fill_betweenx(x, y, y2)),
        ('text', lambda vv: vv.text(0.2, 0.2, 'txt')),
        ('arrow', lambda vv: vv.arrow(0.2, 0.2, 0.8, 0.8)),
        ('figtext', lambda vv: vv.figtext(0.5, 0.5, 'txt')),
        ('legend', lambda vv: (vv.plot(x, y), vv.legend('sig'))),
    ]

    v = interactive.figure()
    _run_smoke_cases(v, cases)


def test_ax():
    v = interactive.figure()
    ax = v.get_axes()
    v.plot(np.arange(30))

    ret = check_prop_read(ax)
    check_prop_write(ax, ret)
