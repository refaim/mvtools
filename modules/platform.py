from __future__ import print_function

import chardet
import locale
import os
import subprocess
import sys
import tempfile
import uuid

import cmd

def is_windows():
    return 'win' in sys.platform

def print_string(s, *args, **kwargs):
    assert isinstance(s, unicode)
    output = kwargs.get('file', sys.stdout)
    print(s.encode(output.encoding, errors='ignore'), *args, **kwargs)

def execute(command):
    cmd_encoding = locale.getpreferredencoding()
    if isinstance(command, list):
        result_command = [cmd.escape(arg).encode(cmd_encoding) for arg in command]
    else:
        result_command = command.encode(cmd_encoding)
    process = subprocess.Popen(result_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0 or stderr:
        print_string(stderr.decode(locale.getpreferredencoding()), file=sys.stderr)
        raise Exception('Process execution error!')
    return stdout

def make_temporary_file(extension):
    return os.path.join(tempfile.gettempdir(), u'{}.{}'.format(uuid.uuid4(), extension.lstrip('.')))

def file_ext(path):
    return os.path.splitext(path)[1].lower()

def detect_encoding(filepath):
    detector = chardet.UniversalDetector()
    for line in open(filepath, 'rb'):
        detector.feed(line)
        if detector.done:
            break
    detector.close()
    return detector.result
