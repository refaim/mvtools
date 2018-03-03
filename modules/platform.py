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

def execute(command, capture_output=True):
    cmd_encoding = locale.getpreferredencoding()
    if isinstance(command, list):
        result_command = [cmd.escape(arg).encode(cmd_encoding) for arg in command]
    else:
        result_command = command.encode(cmd_encoding)
    output_buffer = subprocess.PIPE if capture_output else None
    process = subprocess.Popen(result_command, stdout=output_buffer, stderr=output_buffer, shell=True)
    stdout, stderr = process.communicate()
    if process.returncode != 0 or capture_output and stderr:
        print_string(stderr.decode(locale.getpreferredencoding()), file=sys.stderr)
        raise Exception('Process execution error!')
    return stdout

def make_temporary_file(extension):
    return os.path.join(tempfile.gettempdir(), u'{}.{}'.format(uuid.uuid4(), extension.lstrip('.')))

def file_name(path):
    return os.path.splitext(os.path.basename(path))[0]

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

def clean_filename(filename):
    if not is_windows():
        return filename
    filename = filename.replace(u': ', u' - ').replace('"', "'")
    name, ext = os.path.splitext(filename)
    filename = name.rstrip(u'.').strip() + ext.strip()
    invalid_characters = set(r'<>:/\|?*')
    return u''.join(c for c in filename if c not in invalid_characters)
