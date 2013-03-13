"""
This is a script that will test real upload with PUT request.
It was created initially because:
 - Django's unittest Client does not encode data, mo matter what media-type used
 - When making request from Django's UnitTest there is no real request.environ['wsgi.input'] that was used initially to
 solve uploads using PUT request. The final solution does not require to use wsgi.input.
"""
import requests

# Define valid toke key here
TOKEN_KEY = '123'
# Image being uploaded during the test.
IMAGE_FILE_PATH = 'photos/test_photos/death-valley-sand-dunes.jpg'

AUTH_HEADER = 'Token {0}'.format(TOKEN_KEY)
HEADERS = {"Authorization": AUTH_HEADER}

# Get upload URL
r = requests.post("http://127.0.0.1:8000/photos/upload_request/", headers=HEADERS)
upload_url = r.json()[0]['upload_url']


# Upload
f = open (IMAGE_FILE_PATH)
r = requests.put(url = upload_url, data =  {'data':'data'},  files =  {'photo':f}, headers=HEADERS)