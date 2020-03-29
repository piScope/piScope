from __future__ import print_function
from ifigure.utils.images2gif import writeGif

import os
from ifigure.utils.cbook import image_to_pil
import six
import numpy as np

dither = 1

if six.PY2:
    assert False, "This module does not work with Py2"
    
from PIL import Image

def save_transition(im1, im2, filename='animation.gif',
                    duration=2000, dither=1, steps = 5,
                    twoway_transition = True):
    '''
    im1, im2 : wx.Image
    '''
    iim1 = image_to_pil(im1)
    iim2 = image_to_pil(im2)

    images = []

    if twoway_transition:
        fac = np.hstack((np.linspace(0, 1, steps)[:-1],
                         np.linspace(1, 0, steps)[:-1]))
        print(fac)
        dd = np.array([1] + [0.2]*(steps-2) + [1] + [0.2]*(steps-2))
        print(duration)
    else:
        fac = np.linspace(0, 1, steps)
        dd = np.array([1] + [0.2]*(steps-2) + [1])
        
    for f in fac:
        image = Image.blend(iim1, iim2, f)
        images.append(image)

    duration = duration * dd
    images[0].save(filename,
                   save_all=True,
                   append_images=images[1:],
                   optimize=False, duration=list(duration),
                   loop=0)
