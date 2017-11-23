from __future__ import print_function

import codecs
import datetime
import sys
import traceback

class Logger(object):
    def __init__(self, filepath=None, stderr=False):
        self.filepath = filepath
        self.stderr = stderr

    def info(self, message):
        self._entry('INFO', message)

    def header(self, message):
        self._entry('INFO', message, header=True)

    def warning(self, message):
        self._entry('WARNING', message)

    def error(self, message):
        self._entry('ERROR', message)

    def _entry(self, category, message, header=False):
        if not isinstance(message, unicode):
            raise Exception('Non-unicode string encountered')
        if header:
            decorator = u'=' * 10
            message = u'{} {} {}'.format(decorator, message, decorator)
        output = u'[{}] [{}] {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), category, message)
        try:
            if self.filepath is not None:
                with codecs.open(self.filepath, 'a', 'utf-8') as fobj:
                    fobj.write(output + '\n')
            if self.stderr:
                print(output, file=sys.stderr)
        except UnicodeEncodeError:
            print(traceback.format_exc(), file=sys.stderr)
        sys.stderr.flush()
