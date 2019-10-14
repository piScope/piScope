from .backend_wxagg_gl import mixin_gl_renderer
from matplotlib.backends.backend_pdf import RendererPdf, PdfFile, Name, Op, pdfRepr
from matplotlib.backends.backend_ps import RendererPS
from matplotlib.backends.backend_svg import RendererSVG


def isPDFrenderer(renderer):
    return (hasattr(renderer, '_vector_renderer') and
            isinstance(renderer._vector_renderer, RendererPdf))


def isPSrenderer(renderer):
    return (hasattr(renderer, '_vector_renderer') and
            isinstance(renderer._vector_renderer, RendererPS))


def isSVGrenderer(renderer):
    return (hasattr(renderer, '_vector_renderer') and
            isinstance(renderer._vector_renderer, RendererSVG))


def isSupportedRenderer(renderer):
    if hasattr(renderer, '_gl_renderer'):
        return True
    elif isPDFrenderer(renderer):
        mixin_gl_renderer(renderer)
        return True
    elif isPSrenderer(renderer):
        mixin_gl_renderer(renderer)
        return True
    elif isSVGrenderer(renderer):
        mixin_gl_renderer(renderer)
        renderer.gl_svg_rescale = True
        return True
    return False
