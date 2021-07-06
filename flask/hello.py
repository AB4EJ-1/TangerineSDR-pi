# hello.py
# this is purely for validating unit test environment
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'
