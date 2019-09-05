from flask import Flask, jsonify, request
import requests

def send_audio():
    print('attempting to send audio')
    url = 'http://127.0.0.1:5000/api/audio'
    file = open('/Users/kaushikandra/laughter-detection/LaughDetection/crowd_laugh_1.wav', 'rb')
    headers = {'content-type': 'audio/wav'}
    payload = {'client_id': 1}
    files = {'file': file}
    r = requests.post(url, data=payload)
    print('sent request')
    print(r)
    print(r.text)

send_audio()
