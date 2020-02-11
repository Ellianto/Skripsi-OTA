from flask import Flask, redirect, url_for

app = Flask(__name__)

# app.debug = True
# To enable debug support (auto server reload when code changes)
# Also spawns debugger for error tracking

@app.route('/')
def hello_world():
    return 'Hello, World!'

# Taking a URL path as a parameter
@app.route('/hello/<name>/')
def hello_name(name):
    return 'Hello %s!' % name

# You can specify the data type of the parameter
@app.route('/blog/<int:id>/')
def show_num(id):
    return 'ID Number %d!' % id

@app.route('/rev/<float:no>/')
def revision(no):
    return 'Number %f' % no

# By specifying the trailing slash, the route can catch both
# the URL with or without the trailing slash. But if it is not
# specified, it will trigger a 404 when the user accesses the URL
# with the trailing slash

# URL Building

@app.route('/admin/')
def hello_admin():
    return 'Hello Admin'

# By default, the data type will be string
@app.route('/guest/<guest>/')
def hello_guest(guest):
    return 'Hello %s as Guest' % guest

# The parameter name has to be the same as the
# one specified in the URL Route

# Reads the passed parameter, and redirects accordingly
@app.route('/user/<name>/')
def hello_user(name):
    if name == 'admin':
        print(url_for('hello_admin'))
        return redirect(url_for('hello_admin'))
    else:
        print(url_for('hello_guest', guest=name))
        return redirect(url_for('hello_guest', guest=name))

# To accommodate other HTTP Methods
from flask import request

@app.route('/somepath', methods = ['POST', 'GET'])
def some_func():
    if request.method == 'POST':
        val = request.form['some_key']
    else:
        val = request.args.get('some_key')

if __name__ == '__main__':
    app.run()