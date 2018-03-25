import os
import sys

import lang
import platform

class Error(Exception):
    pass

def argparse_path(bytestring):
    return os.path.abspath(os.path.expandvars(bytestring.decode(sys.getfilesystemencoding())))

def argparse_lang(value):
    if value not in lang.LANGUAGES:
        raise Error(u'Unknown language "{}"'.format(value))
    return value

def run(main):
    error = None
    return_code = 0
    try:
        return_code = main()
    except Error as e:
        error = e.message
    except KeyboardInterrupt:
        error = u'Interrupted by user'
    if error is not None:
        platform.print_string(error)
        return_code = 1
    sys.exit(return_code)
