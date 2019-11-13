from __future__ import print_function
from ifigure.utils.images2gif import writeGif
#from PIL import Image
from ifigure.utils.cbook import image_to_pil
import six
dither = 1
import tempfile
import os
import wx
import shutil

def save_animation(func, params, canvas, filename='animation.png', duration=0.2):

    path = tempfile.mkdtemp()
    images = []
    for k, p in enumerate(params):
        func(p)
        image = canvas.canvas.bitmap.ConvertToImage()
        fname = os.path.join(path, 'frame_'+str(k)+'.png')
        image.SaveFile(fname, wx.BITMAP_TYPE_PNG)
        images.append(fname)


    from apng import APNG
    APNG.from_files(images,  delay=int(duration)).save(filename)
    shutil.rmtree(path)
