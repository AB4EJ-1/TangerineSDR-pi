# test_hello.py
import os, sys
BASE_DIR = os.getcwd()
print(BASE_DIR)
sys.path.append(BASE_DIR)

from hello import app
from app import app as app1

def test_hello():  # this merely is to validate the test environment
    response = app.test_client().get('/')
    assert response.status_code == 200
    assert response.data == b'Hello, World!'
    
def test_app1():
    response = app1.test_client().get('/')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    assert theResponse.__contains__('<strong>Main Control Panel</strong>')
    
def test_app1_config():
    response = app1.test_client().get('/config')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    assert theResponse.__contains__('Configure')
    
def test_is_numeric():
    import app
    assert app.is_numeric('1') == True
    assert app.is_numeric('a') == False
    
def test_logger():
    import app
    app.log("test message from unit testing",4)
    
def test_discovery():
    import app
    app.discover_DE()
    print("PortB=",app.DE_IP_portB)
    if app.DE_IP_portB == 0:
      print("*** DE or DE simulator apparently offline/unreachable ***")
    assert app.DE_IP_portB > 20000
    
def test_upd_configfile():
    import app
    parser = app.configparser.ConfigParser(allow_no_value=True)
    parser.read('config.ini')
    parser.set('profile', 'test_value',  'zzz')
    fp = open('config.ini', 'w')
    parser.write(fp)
    fp.close()
    parser.read('config.ini')
    print ("config test value=",parser['profile']['test_value'])
    assert parser['profile']['test_value'] == 'zzz'
    
def test_app1_cleanup():
    import app
    assert app.cleanup('" ''') == "_"

def test_app1_danger(): 
    response = app1.test_client().get('/danger')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>'Danger Zone' - Technical Configuration Items</strong>")
    
def test_app1_desetup(): 
    response = app1.test_client().get('/desetup')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>Data Collection Setup</strong>")
    
def test_app1_uploading(): 
    response = app1.test_client().get('/uploading')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>Uploading Setup</strong>")
    
def test_app1_magnet(): 
    response = app1.test_client().get('/magnet')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>Magnetometer Setup</strong>")
    
def test_app1_magnetdata(): 
    response = app1.test_client().get('/magnetdata')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse == "Connecting to magnetometer..."

def test_app1_magnetdata1(): 
    response = app1.test_client().get('/magnetdata1')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>Magnetometer Setup</strong>")
    
def test_app1_callsign(): 
    response = app1.test_client().get('/callsign')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>Callsign/Grid Monitor</strong>")
    
def test_app1_notification(): 
    response = app1.test_client().get('/notification')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>Notification</strong>")
    
def test_app1_propagation():   # this is FT8
    response = app1.test_client().get('/propagation')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>FT8 Setup</strong>")
    
def test_app1_propagation2():   # thsi is WSPR
    response = app1.test_client().get('/propagation2')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: ",theResponse)
    assert theResponse.__contains__("<strong>WSPR Setup</strong>")
    
def test_app1_ft8list():   # thsi is WSPR
    response = app1.test_client().get('/_ft8list')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: '" + theResponse + "'")
    assert theResponse == ''
    
def test_app1_wsprlist():   # thsi is WSPR
    response = app1.test_client().get('/_wsprlist')
    assert response.status_code == 200
    theResponse = response.data.decode('utf-8')
    print("Response: '" + theResponse + "'")
    assert theResponse == ''
    

    

    
    
