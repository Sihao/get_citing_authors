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

    # Check which radio option is selected
    option = request.form['option']

    # Get list of authors and cited PMIDs from database
    author_list, cited_PMIDs, citing_PMIDs = get_author_list_counts_search(search_string, option)

    # Split author list with cite counts into two separate lists
    author_names, cite_counts = list(zip(*author_list.items()))

    # Convert cited_PMIDs to list of tuples
    cited_PMIDs = [tuple(PMIDs) for PMIDs in cited_PMIDs]
    citing_PMIDs = [tuple(PMIDs) for PMIDs in citing_PMIDs]

    # Zip author names, citation counts, cited PMIDs and citing_PMIDs into one tuple
    output_list = list(zip(author_names,cite_counts,cited_PMIDs, citing_PMIDs))

    # Sort list in descending citation count order
    output_list = sorted(output_list, key=lambda x: x[1], reverse=True)

    if (request.form['action'] == "Download"):
        return output_csv(output_list)

    elif (request.form['action'] == "View"):
        return render_template('list_view.html', dict=output_list)


@app.route('/author_list_counts_PMIDs', methods = ['POST'])
def return_authorListCounts():
    """Present user with download for get_author_list_counts() output

       Input from form field 'searchString' is passed to get_author_list_counts()
       whose output is written to a csv file which is made available for download.


       :return: csv file containing rows of authors together with number of times they have cited
                papers given by input PMIDs
       """


    # Get list of input PMIDs from form field
    ## Input comma seperated PMIDs need to be transformed from set to list
    input_PMID_list = request.form['input_PMID_List'].split(',')

    # Check if drop_source_author checkbox is ticked
    if 'drop_source_authors' in request.form:
        boolean = True
    else:
        boolean = False

    # Get list of authors and cited PMIDs from database
    author_list, cited_PMIDs, citing_PMIDs = get_author_list_counts(input_PMID_list, drop_source_authors=boolean)

    # Split author list with cite counts into two separate lists
    author_names, cite_counts = list(zip(*author_list.items()))

    # Convert cited_PMIDs to list of tuples
    cited_PMIDs = [tuple(PMIDs) for PMIDs in cited_PMIDs]
    citing_PMIDs = [tuple(PMIDs) for PMIDs in citing_PMIDs]

    # Zip author names, citation counts, cited PMIDs and citing PMIDs into one tuple
    output_list = list(zip(author_names, cite_counts, cited_PMIDs, citing_PMIDs))

    # Sort list in descending citation count order
    output_list = sorted(output_list, key=lambda x: x[1], reverse=True)

    if (request.form['action'] == "Download") :
        return output_csv(output_list)

    elif (request.form['action'] == "View"):
        return render_template('list_view.html', dict=output_list)

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



