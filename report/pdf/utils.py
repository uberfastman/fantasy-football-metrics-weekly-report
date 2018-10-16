from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image
from reportlab.lib.pagesizes import inch


def get_image(path, width=1 * inch):
    img = ImageReader(path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return Image(path, width=width, height=(width * aspect))
