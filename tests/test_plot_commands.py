'''
Plotting command smoke tests for piScope interactive API.
'''

import numpy as np
import pytest

import ifigure.interactive as interactive

from tests.test_utils import check_prop_read, check_prop_write, piscope_session


pytestmark = [pytest.mark.quick]


TWO_D_PLOTTING_COMMANDS = [
    'plot', 'loglog', 'semilogy', 'semilogx', 'plotc', 'errorbar', 'errorbarc',
    'triplot', 'contour', 'contourf', 'scatter', 'hist', 'tricontour',
    'tricontourf', 'image', 'quiver', 'specgram', 'spec', 'tripcolor',
    'axline', 'axlinec', 'axspan', 'axspanc', 'text', 'arrow', 'figarrow',
    'figtext', 'legend', 'fill', 'fill_between', 'fill_betweenx', 'timetrace',
]


THREE_D_PLOTTING_COMMANDS = [
    'quiver3d', 'fill_between_3d', 'surf', 'surface', 'revolve', 'trisurf',
    'solid',
]


ALL_PLOTTING_COMMANDS = TWO_D_PLOTTING_COMMANDS + THREE_D_PLOTTING_COMMANDS

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
        # time.sleep(0.5)

    if failures:
        lines = ['{}: {}'.format(name, err) for name, err in failures]
        raise AssertionError('plotting smoke failures:\n' + '\n'.join(lines))

def test_plotting_command_inventory():
    two_d = set(TWO_D_PLOTTING_COMMANDS)
    three_d = set(THREE_D_PLOTTING_COMMANDS)
    all_cmd = set(ALL_PLOTTING_COMMANDS)

    overlap = two_d.intersection(three_d)
    assert len(overlap) == 0, 'overlap in command groups: {}'.format(sorted(overlap))

    covered = two_d.union(three_d)
    missing = sorted(all_cmd.difference(covered))
    extra = sorted(covered.difference(all_cmd))
    assert len(missing) == 0, 'commands missing from matrix: {}'.format(missing)
    assert len(extra) == 0, 'unknown commands in matrix: {}'.format(extra)


def test_plotting_command_presence():
    missing = [name for name in ALL_PLOTTING_COMMANDS
               if not hasattr(interactive, name)]
    assert len(missing) == 0, 'missing interactive plotting commands: {}'.format(missing)


def _build_2d_cases():
    x, y, y2, X, Y, Z, u, v2 = _sample_data()
    qx = X[::4, ::4]
    qy = Y[::4, ::4]
    qu = u[::4, ::4]
    qv = v2[::4, ::4]
    xf = X.ravel()
    yf = Y.ravel()
    zf = Z.ravel()

    return [
        ('plot', lambda vv: vv.plot(x, y)),
        ('loglog', lambda vv: vv.loglog(x + 0.1, np.abs(y) + 0.1)),
        ('semilogy', lambda vv: vv.semilogy(x + 0.1, np.abs(y) + 0.1)),
        ('semilogx', lambda vv: vv.semilogx(x + 0.1, y)),
        ('plotc', lambda vv: vv.plotc(x, y)),
        ('errorbar', lambda vv: vv.errorbar(x, y, yerr=0.1*np.ones_like(y))),
        ('errorbarc', lambda vv: vv.errorbarc(x, y, yerr=0.1*np.ones_like(y))),
        ('triplot', lambda vv: vv.triplot(xf, yf)),
        ('contour', lambda vv: vv.contour(X, Y, Z)),
        ('contourf', lambda vv: vv.contourf(X, Y, Z)),
        ('scatter', lambda vv: vv.scatter(x, y)),
        ('hist', lambda vv: vv.hist(y, bins=10)),
        ('tricontour', lambda vv: vv.tricontour(xf, yf, zf, 8)),
        ('tricontourf', lambda vv: vv.tricontourf(xf, yf, zf, 8)),
        ('image', lambda vv: vv.image(Z)),
        ('quiver', lambda vv: vv.quiver(qx, qy, qu, qv)),
        ('specgram', lambda vv: vv.specgram(y)),
        ('spec', lambda vv: vv.spec(y)),
        ('tripcolor', lambda vv: vv.tripcolor(xf, yf, zf)),
        ('axline', lambda vv: vv.axline(0.5)),
        ('axlinec', lambda vv: vv.axlinec(0.3)),
        ('axspan', lambda vv: vv.axspan([0.2, 0.4])),
        ('axspanc', lambda vv: vv.axspanc([0.5, 0.7])),
        ('text', lambda vv: vv.text(0.2, 0.2, 'txt')),
        ('arrow', lambda vv: vv.arrow(0.2, 0.2, 0.8, 0.8)),
        ('figarrow', lambda vv: vv.figarrow(0.2, 0.2, 0.8, 0.8)),
        ('figtext', lambda vv: vv.figtext(0.5, 0.5, 'txt')),
        ('legend', lambda vv: (vv.plot(x, y), vv.legend('sig'))),
        ('fill', lambda vv: vv.fill(x, y)),
        ('fill_between', lambda vv: vv.fill_between(x, y, y2)),
        ('fill_betweenx', lambda vv: vv.fill_betweenx(x, y, y2)),
        ('timetrace', lambda vv: vv.timetrace(x, y)),
    ]


def _build_3d_cases():
    x, y, y2, X, Y, Z, u, v2 = _sample_data()
    qx = X[::4, ::4].ravel()
    qy = Y[::4, ::4].ravel()
    qz = Z[::4, ::4].ravel()
    qu = u[::4, ::4].ravel()
    qv = v2[::4, ::4].ravel()
    qw = np.ones_like(qu)

    x1 = x
    y1 = y
    z1 = np.linspace(0.0, 1.0, len(x))
    x2 = x
    y2_line = y + 0.2
    z2 = z1 + 0.2

    return [
        ('quiver3d', lambda vv: vv.quiver3d(qx, qy, qz, qu, qv, qw)),
        ('fill_between_3d', lambda vv: vv.fill_between_3d(x1, y1, z1, x2, y2_line, z2)),
        ('surf', lambda vv: vv.surf(X, Y, Z)),
        ('surface', lambda vv: vv.surface(X, Y, Z)),
        ('revolve', lambda vv: vv.revolve(np.linspace(0.5, 1.0, len(x)), z1)),
        ('trisurf', lambda vv: vv.trisurf(X.ravel(), Y.ravel(), Z.ravel())),
        ('solid', lambda vv: vv.solid(np.zeros((3, 3, 3)))),
    ]


def test_plotting_commands_2d_all(piscope_session):
    cases = _build_2d_cases()
    case_names = set(name for name, _ in cases)
    assert case_names == set(TWO_D_PLOTTING_COMMANDS), (
        '2D case matrix mismatch: missing={} extra={}'.format(
            sorted(set(TWO_D_PLOTTING_COMMANDS).difference(case_names)),
            sorted(case_names.difference(set(TWO_D_PLOTTING_COMMANDS))),
        )
    )

    cases = [
        c for c in cases
    ]

    v = interactive.figure()
    _run_smoke_cases(v, cases)


def test_plotting_commands_3d_all(piscope_session):
    cases = _build_3d_cases()
    case_names = set(name for name, _ in cases)
    assert case_names == set(THREE_D_PLOTTING_COMMANDS), (
        '3D case matrix mismatch: missing={} extra={}'.format(
            sorted(set(THREE_D_PLOTTING_COMMANDS).difference(case_names)),
            sorted(case_names.difference(set(THREE_D_PLOTTING_COMMANDS))),
        )
    )

    cases = [c for c in cases]

    v = interactive.figure()
    v.threed('on')
    _run_smoke_cases(v, cases)


def test_ax(piscope_session):
    v = interactive.figure()
    ax = v.get_axes()
    v.plot(np.arange(30))

    ret = check_prop_read(ax)
    check_prop_write(ax, ret)
