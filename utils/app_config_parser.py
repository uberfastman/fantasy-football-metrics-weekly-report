import logging
import os
import re
from collections import defaultdict
from configparser import ConfigParser, NoOptionError, NoSectionError

logger = logging.getLogger(__name__)

# Used in parser getters to indicate the default behaviour when a specific
# option is not found it to raise an exception. Created to enable `None` as
# a valid fallback value.
_UNSET = object()

_default_dict = dict
DEFAULTSECT = "DEFAULT"


class AppConfigParser(ConfigParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.comment_map = defaultdict(dict)

    # noinspection PyShadowingBuiltins
    def get(self, section, option, *, raw=False, vars=None, fallback=_UNSET):
        """Get an option value for a given section.

        If `vars' is provided, it must be a dictionary. The option is looked up
        in `vars' (if provided), `section', and in `DEFAULTSECT' in that order.
        If the key is not found and `fallback' is provided, it is used as
        a fallback value. `None' can be provided as a `fallback' value.

        If interpolation is enabled and the optional argument `raw' is False,
        all interpolations are expanded in the return values.

        Arguments `raw', `vars', and `fallback` are keyword only.

        The section DEFAULT is special.
        """
        try:
            d = self._unify_values(section, vars)
        except NoSectionError:
            if fallback is _UNSET:
                raise
            else:
                return fallback
        option = self.optionxform(option)
        try:
            value = d[option]
        except KeyError:

            if fallback is _UNSET:
                if section == "Report" and \
                        (str(option).startswith("league") or
                         str(option).startswith("report") or
                         str(option).startswith("team")):
                    logger.warning(
                        f"MISSING CONFIGURATION VALUE: \"{section}: {option}\"! Setting to default value of \"False\". "
                        f"To include this section, update \"config.ini\" and try again."
                    )
                    return "False"
                else:
                    raise NoOptionError(option, section)
            else:
                return fallback

        if raw or value is None:
            return value
        else:
            return self._interpolation.before_get(self, section, option, value, d)

    def read(self, filenames, encoding=None):
        """Read and parse a filename or an iterable of filenames.

        Files that cannot be opened are silently ignored; this is
        designed so that you can specify an iterable of potential
        configuration file locations (e.g. current directory, user's
        home directory, system-wide directory), and all existing
        configuration files in the iterable will be read.  A single
        filename may also be given.

        Return list of successfully read files.
        """
        if isinstance(filenames, (str, bytes, os.PathLike)):
            filenames = [filenames]
        read_ok = []
        for filename in filenames:
            try:
                with open(filename, encoding=encoding) as fp:
                    section = None
                    key_comments = []
                    lines = fp.readlines()
                    for line in lines:
                        if str(line).startswith("["):
                            section = re.sub("[\\W_]+", "", line)
                            self.comment_map[section] = {}
                        else:
                            if str(line).startswith(";"):
                                key_comments.append(line)
                            else:
                                if "=" in line:
                                    key = line.split("=")[0].strip()
                                    self.comment_map[section][key] = key_comments
                                    key_comments = []
                    fp.seek(0)
                    self._read(fp, filename)
            except OSError:
                continue
            if isinstance(filename, os.PathLike):
                filename = os.fspath(filename)
            read_ok.append(filename)
        return read_ok

    def _write_section(self, fp, section_name, section_items, delimiter):
        """Write a single section to the specified `fp`."""
        fp.write(f"[{section_name}]\n")
        section_comments_map = self.comment_map.get(section_name)

        for key, value in section_items:
            value = self._interpolation.before_write(self, section_name, key, value)
            if value is not None or not self._allow_no_value:
                value = delimiter + str(value).replace('\n', '\n\t')
            else:
                value = ""

            if key in section_comments_map.keys():

                key_comments = section_comments_map.get(key)
                for comment in key_comments:
                    fp.write(comment)

            fp.write(f"{key}{value}\n")
        fp.write("\n")
