from __future__ import print_function
from ifigure.utils.images2gif import writeGif
#from PIL import Image
import os
from ifigure.utils.cbook import image_to_pil
dither = 1


def save_animation(func, params, canvas, filename='animation.gif',
                   duration=0.2, dither=1):
    images = []
    for p in params:
        func(p)
        image = canvas.canvas.bitmap.ConvertToImage()
        images.append(image_to_pil(image))

    print(writeGif.__doc__)
    writeGif(filename, images, duration=duration, dither=dither)
