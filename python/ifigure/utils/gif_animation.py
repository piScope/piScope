from __future__ import print_function
from ifigure.utils.images2gif import writeGif
#from PIL import Image
import os
from ifigure.utils.cbook import image_to_pil
import six
dither = 1


def save_animation(func, params, canvas, filename='animation.gif',
                   duration=0.2, dither=1):
    images = []
    for p in params:
        func(p)
        image = canvas.canvas.bitmap.ConvertToImage()
        images.append(image_to_pil(image))
    
    if six.PY2:
        writeGif(filename, images, duration=duration, dither=dither)
    else:
        # we use PIL's implementation in PY3
        images[0].save(filename,
                       save_all=True,
                       append_images=images[1:],
                       optimize=False,
                       duration=duration*1000,  # this parameter is ms
                       loop=0)
