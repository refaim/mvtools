import enzyme
import os

def movies(path):
    for root, dirs, files in os.walk(path):
        for filename in sorted(files):
            if filename.endswith('.mkv'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'rb') as fileobj:
                    yield (filepath, enzyme.MKV(fileobj))
