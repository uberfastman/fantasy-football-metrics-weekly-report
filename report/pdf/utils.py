from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image
from reportlab.lib.pagesizes import inch
import urllib.request
import os


def get_image(path, test_dir, week, width=1 * inch):

    img_name = path.split("/")[-1]
    local_img_path = test_dir + "/week_" + week + "/player_headshots/" + img_name

    if not os.path.exists(local_img_path):
        urllib.request.urlretrieve(path, local_img_path)

    img = ImageReader(local_img_path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)

    scaled_img = Image(local_img_path, width=width, height=(width * aspect))

    return scaled_img

