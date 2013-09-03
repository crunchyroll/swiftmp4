import urlparse
from StringIO import StringIO
from swiftmp4.streaming.StreamMp4 import SwiftStreamMp4

from swift.common import swob
from swift.common.http import HTTP_BAD_REQUEST

def get_err_response():
    resp = swob.Response(content_type='text/xml')
    resp.status = HTTP_BAD_REQUEST
    resp.body = '<?xml version="1.0" encoding="UTF-8"?>\r\n<Error>\r\n  ' \
                    '<Code>%s</Code>\r\n  <Message>%s</Message>\r\n</Error>\r\n' \
                    % (HTTP_BAD_REQUEST, 'Unable to process requested MP4')
    return resp


class SwiftMp4Middleware(object):
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
    
    def make_start_request(self, env):
        # Request first 4 MB of Object
        # TODO: Make this a configuration option later
        environ = env.copy()
        environ['HTTP_RANGE'] = 'bytes=0-4194304'
        def start_response(status, headers, *args):
            if not status.startswith('2'):
                env['swift.start_error'] = True
            env['swift.start_response'] = (status, headers)
        
        return self.app(environ, start_response)
    
    def make_range_request(self, env, start, stop):
        # Makes a ranged request
        environ = env.copy()
        environ['HTTP_RANGE'] = 'bytes=%s-%s' % (start, stop)
        def start_response(status, headers, *args):
            if not status.startswith('2'):
                env['swift.range_error'] = True
            env['swift.range_response'] = (status, headers)
        
        return self.app(environ, start_response)
    
    def __call__(self, env, start_response):
        try:
            return self.handle_request(env, start_response)
        except Exception, e:
            pass
        return 
    
    def handle_request(self, env, start_response):
        parts = urlparse.parse_qs(env.get('QUERY_STRING') or '')
        start = parts.get('start', [''])[0]
        # TODO: Check that the file requested is a MP4
        if start and env['REQUEST_METHOD'] == 'GET':
            # Get the MP4 metadata
            start_resp = self.make_start_request(env)
            start_file = StringIO(''.join(start_resp))
            if env.get('swift.start_error'):
                raise Exception('Invalid start response %r' %
                                env['swift.start_response'])
            status, headers = env['swift.start_response']
            for header, value in headers:
                if header == 'content-range':
                    content_length = int(value.split('/')[-1])
                if header == 'content-type':
                    content_type = value
            
            # Parse MP4 metadata
            mp4stream = SwiftStreamMp4(start_file, content_length, start)
            mp4stream._parseMp4()
            
            # Verify MP4 metadata
            if mp4stream._verifyMetadata():
                # Update the metadata
                mp4stream._updateAtoms()
                
                # Start creating the response
                status = '200 OK'
                headers = [('content-type', content_type)]
                start_response(status, headers)
                
                # Return iterator of mp4 data
                def content_iter():
                    try:
                        # Yield modified mp4 metadata
                        for i, chunk in enumerate(mp4stream._yieldMetadataToStream()):
                            yield chunk
                        # Make a ranged request for the actual MP4 content data
                        start, stop = mp4stream._getByteRangeToRequest()
                        range_resp = self.make_range_request(env, start, stop)
                        for chunk in range_resp:
                            yield chunk
                    except Exception, e:
                        # TODO: Figure out how this exception should be handled
                        pass
                
                return content_iter()
            else:
                raise Exception('Invalid MP4 metadata')
        else:
            return self.app(env, start_response)
    


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    
    def swiftmp4_filter(app):
        return SwiftMp4Middleware(app, conf)
    
    return swiftmp4_filter
