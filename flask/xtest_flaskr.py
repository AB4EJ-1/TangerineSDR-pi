import os
import tempfile

import pytest

#from flaskr import create_app
from flaskr.db import init_db


from importlib.machinery import SourceFileLoader
mymodule = SourceFileLoader('app1','./app.py').load_module()

from app1 import create_app


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({'TESTING': True, 'DATABASE': db_path})

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)
    
def test_empty_db(client):
    """Start with a blank database."""

    rv = client.get('/')
    assert b'Posts' in rv.data
    
def test_restart(client):
    rv = client.get('/restart')
    assert b'restarted' in rv.data
    
    
def login(client, username, password):
    return client.post('/login', data=dict(
        username=username,
        password=password
    ), follow_redirects=True)
    
def test_login_logout(client):
    """Make sure login and logout works."""

  #  username = flaskr.app.config["USERNAME"]
  #  password = flaskr.app.config["PASSWORD"]


    username = "username"
    password = "password"
    
    rv = login(client, username, password)
    assert b'Log In' in rv.data

    
