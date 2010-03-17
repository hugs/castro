import os
try:
    import json
except ImportError:
    import simplejson as json
import tempfile

class MessageBoard:
    def __init__(self, filename):
        storage_dir = os.environ.get('CASTRO_DATA_DIR',
                                     tempfile.gettempdir())
        self.filepath = os.path.join (storage_dir,
                                      'castro-messageboard-%s' % filename)
        open(self.filepath,'a').close()

    def write(self, writable):
        file = open(self.filepath,'w')
        writable_json = json.dumps(writable, indent=4)
        file.write(writable_json)
        file.close()
        return None
    
    def read(self):
        file = open(self.filepath,'r')
        readable_json = file.read()
        file.close()
        try:
            readable = json.loads(readable_json)
        except ValueError:
            readable = None 
        return readable

recording_should_continue = MessageBoard('recording_should_continue.txt')
