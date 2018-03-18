from flask import Flask, render_template, make_response, request

from utils import *

from io import StringIO

import csv
app = Flask(__name__)

@app.route('/', methods = ['GET'])
def index():
    """Render the index page

    :return: HTML for the index page
    """
    return render_template('index.html')

@app.route('/author_list_counts_search', methods = ['POST'])
def return_author_list_counts_search():
    """Present user with download for get_author_list_counts_search() output

    Input from form field 'searchString' is passed to get_author_list_counts_search()
    whose output is written to a csv file which is made available for download.


    :return: csv file containing rows of authors together with number of times they have cited papers returned by search
    """

    # Get searchString from form field
    searchString = request.form['search_string']

    # Create IO object to write file to
    si = StringIO()

    # Write csv file
    writer = csv.writer(si, delimiter=',')
    writer.writerows(get_author_list_counts_search(searchString).items())

    # Construct file output
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"

    return output


@app.route('/author_list_counts_PMIDs', methods = ['POST'])
def return_authorListCounts():
    """Present user with download for get_author_list_counts() output

       Input from form field 'searchString' is passed to get_author_list_counts()
       whose output is written to a csv file which is made available for download.


       :return: csv file containing rows of authors together with number of times they have cited
                papers given by input PMIDs
       """


    # Get list of input PMIDs from form field
    inputPMIDList = request.form['input_PMID_List']

    # Create IO object to write file to
    si = StringIO()

    # Write csv file
    writer = csv.writer(si, delimiter=',')
    writer.writerows(get_author_list_counts({inputPMIDList}).items())

    # Construct file output
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"

    return output


if __name__ == '__main__':
    app.run(debug=True)



