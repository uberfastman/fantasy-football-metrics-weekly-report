import logging
import logging.handlers as handlers
import os
import sys
import time
# from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler


# class taken from stackoverflow: https://stackoverflow.com/a/8468041
# noinspection PyPep8Naming,PyUnresolvedReferences
class SizedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Handler for logging to a set of files, which switches from one file
    to the next when the current file reaches a certain size, or at certain
    timed intervals
    """

    def __init__(self, filename, maxBytes=0, backupCount=0, encoding=None, delay=0, when='h', interval=1, utc=False):
        handlers.TimedRotatingFileHandler.__init__(self, filename, when, interval, backupCount, encoding, delay, utc)
        self.maxBytes = maxBytes
        self.stream = None

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        Basically, see if the supplied record would cause the file to exceed
        the size limit we have.
        """
        if self.stream is None:                 # delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:                   # are we rolling over?
            msg = "%s\n" % self.format(record)
            # due to non-posix-compliant Windows feature
            self.stream.seek(0, 2)
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return 1
        t = int(time.time())
        if t >= self.rolloverAt:
            return 1
        return 0


def get_logger(module_name=None, propagate=True):

    log_file_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

    log_file_name = "webapp_out.log"
    log_file = os.path.join(log_file_dir, log_file_name)

    if not os.path.exists(log_file_dir):
        os.makedirs(log_file_dir)

    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    sh = logging.StreamHandler(stream=sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(log_formatter)

    # 10*1024*1024 = 10mb
    # 1*1024*1024 = 1mb

    # # rotate logs WITHOUT timed rotation
    # rfh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)

    # rotate logs WITH timed rotation
    rfh = SizedTimedRotatingFileHandler(
        log_file,
        when="h",
        interval=1,
        maxBytes=10*1024*1024,
        backupCount=5,
        # encoding='bz2'  # uncomment for bz2 compression
    )

    rfh.setLevel(logging.DEBUG)
    rfh.setFormatter(log_formatter)

    if module_name:
        logger = logging.getLogger(module_name)
    else:
        logger = logging.getLogger()

    if logger.hasHandlers():
        logger.handlers = []

    logger.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    logger.addHandler(rfh)

    if not propagate:
        logger.propagate = False

    return logger
