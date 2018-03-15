from flask import Flask, render_template, make_response, request

from utils import *

from io import StringIO

import csv
app = Flask(__name__)

@app.route('/', methods = ['GET'])
def index():
    return render_template('index.html')

@app.route('/', methods = ['POST'])
def return_authorList():
    searchString = request.form['searchString']
    si = StringIO()

    writer = csv.writer(si, delimiter=',')

    writer.writerows(get_authorListCounts(searchString).items())

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"

    return output


if __name__ == '__main__':
    app.run(debug=True)



