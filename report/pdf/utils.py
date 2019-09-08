from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image
from reportlab.lib.pagesizes import inch
import urllib.request
from urllib.error import URLError
import os

import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
logging.getLogger("PIL.PngImagePlugin").setLevel(level=logging.INFO)


def get_image(path, data_dir, week, width=1 * inch):

    headshots_dir = os.path.join(data_dir, "week_" + str(week), "player_headshots")

    if not os.path.exists(headshots_dir):
        os.makedirs(headshots_dir)

    img_name = path.split(os.path.sep)[-1]
    local_img_path = os.path.join(headshots_dir, img_name)

    if not os.path.exists(local_img_path):
        try:
            urllib.request.urlretrieve(path, local_img_path)
        except URLError:
            logger.error("Unable to retrieve player headshot at url {}".format(path))
            local_img_path = os.path.join("resources", "photo-not-available.jpeg")

    img = ImageReader(local_img_path)
    iw, ih = img.getSize()
    aspect = ih / float(iw)

    scaled_img = Image(local_img_path, width=width, height=(width * aspect))

    return scaled_img

