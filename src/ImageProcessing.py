import math
import numpy as np
from PIL import Image
import os
import base64
from io import BytesIO
from scipy import stats


class ImageProcessing:
    __DEFAULT_LUMA_THRESHOLD_MAX = 0.3
    __DEFAULT_LUMA_THRESHOLD_MIN = 0
    __INVERTED_LUMA_THRESHOLD_MAX = 1
    __INVERTED_LUMA_THRESHOLD_MIN = 0.7
    __LUMA_THRESHOLD_MAX = __DEFAULT_LUMA_THRESHOLD_MAX
    __LUMA_THRESHOLD_MIN = __DEFAULT_LUMA_THRESHOLD_MIN
    DEFAULT_TEMP_DIR  = "../templates/"
    IMG_EXTS          = ['.png', '.jpg', '.gif']
    
    @staticmethod
    def binarize(img):
        new_img = np.zeros([img.shape[0], img.shape[1]])
        img = ImageProcessing.rgb2luma(img)
        for r in range(img.shape[0]):
            for c in range(img.shape[1]):
                if ImageProcessing.__LUMA_THRESHOLD_MAX > img[r,c] and \
                    img[r,c] > ImageProcessing.__LUMA_THRESHOLD_MIN:
                    new_img[r,c] = 1
        return new_img
            
    @staticmethod
    def rgb2luma(im):
        R_FACTOR = 0.2126
        G_FACTOR = 0.7152
        B_FACTOR = 0.0722
        bw_im = np.zeros([im.shape[1], im.shape[0]])
        for r in range(im.shape[1]):
            for c in range(im.shape[0]):
                bw_im[r,c] = (R_FACTOR*im[r,c,0]+G_FACTOR*im[r,c,1]+B_FACTOR*im[r,c,2])/255
        return bw_im    
    
    @staticmethod
    def set_luma_thres(img=None, inverted=False):
        if img:
            lumas = np.round(ImageProcessing.rgb2luma(np.array(img)), 1).flatten()
            fst_cmn_luma = stats.mode(lumas)[0]
            snd_cmn_luma = stats.mode(lumas[lumas!=fst_cmn_luma])[0]
            thres_luma = (fst_cmn_luma+snd_cmn_luma)/2
            if inverted:
                ImageProcessing.__LUMA_THRESHOLD_MIN = thres_luma
                ImageProcessing.__LUMA_THRESHOLD_MAX = 1
            else:
                ImageProcessing.__LUMA_THRESHOLD_MAX = thres_luma
                ImageProcessing.__LUMA_THRESHOLD_MIN = 0
        elif inverted:
            ImageProcessing.__LUMA_THRESHOLD_MIN = ImageProcessing.__INVERTED_LUMA_THRESHOLD_MIN
            ImageProcessing.__LUMA_THRESHOLD_MAX = ImageProcessing.__INVERTED_LUMA_THRESHOLD_MAX
        
    @staticmethod
    def get_imgs(dir=DEFAULT_TEMP_DIR, ext=IMG_EXTS):
        files = []
        for f in os.listdir(dir):
            for e in ext:
                if f.endswith(e):
                    files.append(os.path.join(dir, f))
        return files
        
    @staticmethod
    def img2base64(img):
        buffer = BytesIO()
        img.save(buffer, optimize=True, quality=0, format='WebP')
        return base64.b64encode(buffer.getvalue())
    
    @staticmethod
    def base642img(str):
        return Image.open(BytesIO(base64.b64decode(str)))
    
    @staticmethod
    def load(path, maxw, maxh):
        img = Image.open(path)
        img = img.resize((maxw, maxh))
        return np.array(img), img