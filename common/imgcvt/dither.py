from . import palette as Palette
import numpy as np
from enum import Enum

dithertype = Enum('dithertype',['NONE','BAYER2','BAYER4','BAYER4ODD','BAYER4EVEN','BAYER4SPOTTY','BAYER8','YLILUOMA1','CLUSTER','FLOYDSTEINBERG'])

######################################
# Custom ordered dither
# code derived from hitherdither
# custom Bayer matrixes taken from
# Project One

def B(m):
    """Get the Bayer matrix with side of length ``n``.
    Will only work if ``n`` is a power of 2.
    Reference: http://caca.zoy.org/study/part2.html
    :param int n: Power of 2 side length of matrix.
    :return: The Bayer matrix.
    """
    return (1 + m) / (1 + (m.shape[0] * m.shape[1]))

def custom_dithering(image, palette:Palette, thresholds, type:dithertype=dithertype.BAYER2):
    """Render the image using the ordered Bayer matrix dithering pattern.
    :param :class:`PIL.Image` image: The image to apply
        Bayer ordered dithering to.
    :param :class:`~hitherdither.colour.Palette` palette: The palette to use.
    :param thresholds: Thresholds to apply dithering at.
    :param int order: Custom matrix type.
    :return:  The Bayer matrix dithered PIL image of type "P"
        using the input palette.
    """
    dMatrix = np.asarray([
        [[4,1],[2,3]],  #Bayer 2x2
        [[1,13,4,16],[9,5,12,7],[3,15,2,14],[11,8,10,8]],   #Bayer 4x4
        [[1,2,3,4],[9,10,11,12],[5,6,7,8],[13,14,15,16]],   #Bayer 4x4 Odd
        [[1,9,4,12],[5,13,6,14],[3,11,2,10],[7,15,8,16]],   #Bayer 4x4 Even
        [[10,1,12,6],[4,9,3,15],[14,2,13,7],[8,11,5,16]],   #Bayer 4x4 Spotty
        [[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],  #Bayer 8x8
        [12,44,4,36,14,46,6,38],[60,28,52,20,62,30,54,22],
        [3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],
        [15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]], dtype=object)


    bayer_matrix = B(np.asarray(dMatrix[type.value-2]))
    ni = np.array(image, "uint8")
    thresholds = np.array(thresholds, "uint8")
    xx, yy = np.meshgrid(range(ni.shape[1]), range(ni.shape[0]))
    xx %= bayer_matrix.shape[0]
    yy %= bayer_matrix.shape[1]
    factor_threshold_matrix = np.expand_dims(bayer_matrix[yy, xx], axis=2) * thresholds
    new_image = ni + factor_threshold_matrix
    return palette.create_PIL_png_from_rgb_array(new_image)

