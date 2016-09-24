from wsgiref.simple_server import make_server
from sparrow import Sparrow

app = Sparrow()

@app.route('/a')
def hello_world():
    return "hello World!"

httpd = make_server('localhost', 8080, app)

httpd.serve_forever()