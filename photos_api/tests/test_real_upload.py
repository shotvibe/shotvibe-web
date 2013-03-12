"""
This is a script that will test real upload.
"""
import base64
import urllib2

HOST = '127.0.0.1'
PORT = "8000"
BASE_URL = 'http://127.0.0.1:8000/'
LOGIN = 'v.prudnikov@gmail.com'
PASS = '123'
import httplib, urllib





request = urllib2.Request("{0}photos/upload_request/".format(BASE_URL))
base64string = base64.encodestring('%s:%s' % (LOGIN, PASS)).replace('\n', '')
request.add_header("Authorization", "Basic %s" % base64string)
result = urllib2.urlopen(request)
print result




