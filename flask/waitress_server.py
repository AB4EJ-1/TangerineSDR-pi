from waitress import serve
import app
import webbrowser

webbrowser.open('http://localhost:5000/restart')
serve(app.app, host='0.0.0.0', port = 5000)
