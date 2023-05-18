# Palette.py
# Extends hitherdither.palette
import hitherdither
from PIL import Image
import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000
from enum import Enum


colordelta = Enum('colordelta',['EUCLIDEAN','CCIR','LAB'])

CCIR_LUMINOSITY = np.array([299.0, 587.0, 114.0])

class Palette(hitherdither.palette.Palette):
    
    colordelta = colordelta.EUCLIDEAN

    def color_compare(self,c1, c2):
        """Compare the difference of two RGB values, weight by CCIR 601 luminosity
        double ColorCompare(int r1,int g1,int b1, int r2,int g2,int b2)
        {
            double luma1 = (r1*299 + g1*587 + b1*114) / (255.0*1000);
            double luma2 = (r2*299 + g2*587 + b2*114) / (255.0*1000);
            double lumadiff = luma1-luma2;
            double diffR = (r1-r2)/255.0, diffG = (g1-g2)/255.0, diffB = (b1-b2)/255.0;
            return (diffR*diffR*0.299 + diffG*diffG*0.587 + diffB*diffB*0.114)*0.75
                + lumadiff*lumadiff;
        }
        :return: float
        """
        luma_diff = c1.dot(CCIR_LUMINOSITY) / (255.0 * 1000.0) - c2.dot(CCIR_LUMINOSITY) / (255.0 * 1000.0)
        diff_col = (c1 - c2) / 255.0
        return ((diff_col ** 2).dot(CCIR_LUMINOSITY / 1000.0) * 0.75) + (luma_diff ** 2)

    def DeltaE(self,c1,c2):

        Lab1 = rgb2lab(c1/255)
        Lab2 = rgb2lab(np.array([[c2/255]]))

        return deltaE_ciede2000(Lab2[0][0],Lab1, kL= 0.5,kC=0.75)
        

    def image_distance(self, image, order=2):
        ni = np.array(image, "float")
        distances = np.zeros((ni.shape[0], ni.shape[1], len(self)), "float")
        for i, colour in enumerate(self):
            if self.colordelta == colordelta.EUCLIDEAN:
                distances[:, :, i] = np.linalg.norm(ni - colour, ord=order, axis=2)
            elif self.colordelta == colordelta.CCIR:
                distances[:, :, i] = self.color_compare(ni,colour)
            else:
                distances[:, :, i] = self.DeltaE(ni,colour)
        return distances

    def image_closest_colour(self, image, order=2):
        return np.argmin(self.image_distance(image, order=order), axis=2)

    def create_PIL_png_from_rgb_array(self, img_array):
        """Create a ``P`` PIL image from a RGB image with this palette.
        Avoids the PIL dithering in favour of our own.
        Reference: http://stackoverflow.com/a/29438149
        :param :class:`numpy.ndarray` img_array: A ``[M x N x 3]`` uint8
            array representing RGB colours.
        :return: A :class:`PIL.Image.Image` image of mode ``P`` with colours
            available in this palette.
        """
        cc = self.image_closest_colour(img_array, order=2)
        pa_image = Image.new("P", cc.shape[::-1])
        pa_image.putpalette(self.colours.flatten().tolist())
        im = Image.fromarray(np.array(cc, "uint8")).im.convert("P", 0, pa_image.im)
        try:
            # Pillow >= 4
            return pa_image._new(im)
        except AttributeError:
            # Pillow < 4
            return pa_image._makeself(im)