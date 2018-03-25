from flask import Flask, render_template, make_response, request

from utils import *

import ast

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

    Input from form field 'search_string' is passed to get_author_list_counts_search()
    whose output is written to a csv file which is made available for download.


    :return: csv file containing rows of authors together with number of times they have cited papers returned by search
    """

    # Get search_string from form field
    search_string = request.form['search_string']

    # Sort author list in descending order
    author_list = get_author_list_counts_search(search_string)
    author_list = sorted(author_list.items(), key=lambda x: x[1], reverse=True)

    if (request.form['action'] == "Download"):
        return output_csv(author_list)

    elif (request.form['action'] == "View"):
        return render_template('list_view.html', dict=author_list)


@app.route('/author_list_counts_PMIDs', methods = ['POST'])
def return_authorListCounts():
    """Present user with download for get_author_list_counts() output

       Input from form field 'searchString' is passed to get_author_list_counts()
       whose output is written to a csv file which is made available for download.


       :return: csv file containing rows of authors together with number of times they have cited
                papers given by input PMIDs
       """


    # Get list of input PMIDs from form field
    input_PMID_list = request.form['input_PMID_List']

    # Sort author list in descending order
    author_list = get_author_list_counts({input_PMID_list})
    author_list = sorted(author_list.items(), key=lambda x: x[1], reverse=True)

    if (request.form['action'] == "Download") :
        return output_csv(author_list)

    elif (request.form['action'] == "View"):
        return render_template('list_view.html', dict=author_list)

@app.route('/return_csv', methods = ['POST'])
def return_csv():
    """
    Returns csv file of list posted to this route with name 'author_list'
    :return: csv file to download
    """

    author_list = request.form['author_list']

    # Convert string representation of list back to list object
    author_list = ast.literal_eval(author_list)

    return output_csv(author_list)

if __name__ == '__main__':
    app.run(debug=False)



