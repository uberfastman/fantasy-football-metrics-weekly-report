import logging
from configparser import ConfigParser, NoOptionError, NoSectionError

logger = logging.getLogger(__name__)

# Used in parser getters to indicate the default behaviour when a specific
# option is not found it to raise an exception. Created to enable `None' as
# a valid fallback value.
_UNSET = object()


class AppConfigParser(ConfigParser):

    def get(self, section, option, *, raw=False, vars=None, fallback=_UNSET):
        """Get an option value for a given section.

        If `vars' is provided, it must be a dictionary. The option is looked up
        in `vars' (if provided), `section', and in `DEFAULTSECT' in that order.
        If the key is not found and `fallback' is provided, it is used as
        a fallback value. `None' can be provided as a `fallback' value.

        If interpolation is enabled and the optional argument `raw' is False,
        all interpolations are expanded in the return values.

        Arguments `raw', `vars', and `fallback' are keyword only.

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
                        "MISSING CONFIGURATION VALUE: \"{}: {}\"! Setting to default value of \"False\". To include "
                        "this section, update \"config.ini\" and try again.".format(section, option))
                    return "False"
                else:
                    raise NoOptionError(option, section)
            else:
                return fallback

        if raw or value is None:
            return value
        else:
            return self._interpolation.before_get(self, section, option, value, d)
