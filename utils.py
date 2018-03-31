import requests
import xml.etree.cElementTree as ET

import pandas as pd
from itertools import chain

from io import StringIO
from flask import make_response
import csv

def get_author_list_counts_search(search_string):
    """Returns a list of authors that have cited papers from search result


    :param search_string: PubMed search string to use for the database search
    :return: dict containing author names as keys and number of occurrences as values
    """

    # Get source PMIDs (PubMed ID) with search term
    source_PMIDs = search_DB(search_string)

    return get_author_list_counts(source_PMIDs)



def get_author_list_counts(source_PMIDs):
    """Returns a list of authors that have cited papers from list of PMIDs

    Constructs a pandas DataFrame using data returned by PubMed API

    TODO: output df

    :param source_PMIDs: Comma separated string of PMIDs or list of PMIDs
    :return: dict containing author names as keys and number of occurrences as values
    """

    # Get list of articles that sort each PMID from source list
    cited_by_list = get_cited_by_PMIDs(source_PMIDs)

    # Get cite counts per PMID for grouping authors later
    citations_per_PMID = [len(PMID) for PMID in cited_by_list]

    # Flatten list
    flat_cited_by_list = list(chain.from_iterable(cited_by_list))


    # Get metadata for each of the articles that cite the source articles (authors and titles)
    citing_author_list_per_PMID, _ = get_PMIDs_metadata(flat_cited_by_list) # Contains citing author list for all source PMIDs

    # Group author list per source PMID
    citing_author_list_per_PMID_grouped = group_list_elements(citing_author_list_per_PMID, citations_per_PMID)


    # Construct DataFrame using extracted data
    df = pd.DataFrame(data = {'PMID': source_PMIDs, 'citing_PMIDs':cited_by_list, 'citing_author_list':citing_author_list_per_PMID_grouped})

    # Total citations per source PMID
    df["tot_citations"] = [len(row) for row in df["citing_PMIDs"]]


    # Getting the full list of unique citing authors with counts
    ## Flatten list of lists for each source PMID
    full_authorList = [author for article in df["citing_author_list"].tolist() for authorList in article for author in authorList]


    ## Get counts
    from collections import Counter
    author_list_counts = dict(Counter(full_authorList))
    cited_PMIDs = [find_cited_article(author, df) for author in author_list_counts.keys()]


    return author_list_counts, cited_PMIDs


def get_cited_by_PMIDs(input_PMID_list):
    """Request "cited by" table for list of PMIDs from PubMed API

    :param input_PMID_list: Comma separated string of PMIDs or list of PMIDs
    :return: List with sublists. One sublist per input PMID, the sublist contains PMIDs of papers that have cited
             the input PMID
    """

    # Base URL of the API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

    # Parameters for API call
    ## Might need to add API key in the future: https://www.ncbi.nlm.nih.gov/books/NBK25497/
    params = {
        "dbfrom": "pubmed",
        "linkname": "pubmed_pubmed_citedin",
        "id": input_PMID_list,
        "retmax": 100000,
        "api_key": None
    }

    # Request the XML response from the API
    response = requests.get(base_url, params = params)

    # Construct ElementTree for parsing XML
    tree= ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()


    LinkSets = root.findall('LinkSet')

    # Iterate over input PMIDs and store the PMIDs of the articles that cite the input article
    cited_by_list = []
    for LinkSet in LinkSets:
        citedBy = []

        # Check if PMID has been cited, only find citing PMIDs if source PMID has been cited
        if LinkSet.find('LinkSetDb'):
            for id in LinkSet.find('LinkSetDb').iter('Id'):
                citedBy.append(id.text)

        cited_by_list.append(citedBy)


    return cited_by_list

def get_PMIDs_metadata(input_PMID_list):
    """Get metadata for list of PMIDs from PubMed API


    :param input_PMID_list:  Comma separated string of PMIDs or list of PMIDs
    :return: Tuple with 2 values:
                - List containing sublists, one sublist per input PMID. Sublist contains authors of input PMID
                - List containing titles of input PMIDs
    """


    # Base URL of the API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    input_PMID_list = ','.join(map(str, input_PMID_list))

    # Parameters for API call

    params = {
        "db": "pubmed",
        "id": input_PMID_list,
        "retmax": 100000,
        "api_key": None

    }
    # Request the XML response from the API
    response = requests.post(base_url, data=params)

    # Construct ElementTree for parsing XML
    tree = ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()

    citing_authorListPerPMID = []
    citing_articleTitlePerPMID = []
    for node in root.findall('.//Item'):
        # Find AuthorList node and extract all the author names
        if node.attrib['Name'] == "AuthorList":
            authorList = []
            for author in node.findall('Item'):
                authorList.append(author.text)
            citing_authorListPerPMID.append(authorList)
        # Find Title node
        if node.attrib['Name'] == 'Title':
            citing_articleTitlePerPMID.append(node.text)


    return (citing_authorListPerPMID, citing_articleTitlePerPMID)



def search_DB(search_term):
    """Searches PubMed database for articles using searchTerm

    The returned articles are the same if you use searchTerm on the PubMed website

    :param search_term: String to search the database with
    :return: List of PMIDs
    """

    # Base URL of the API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    # Parameters for API call
    params = {
        "db": "pubmed",
        "term": search_term,
        "retmax": 100000,
        "api_key": None

    }

    response = requests.get(base_url, params=params)

    # Construct ElementTree for parsing XML
    tree= ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()


    id_list = root.find('IdList')

    PMID_List = []
    for PMID in id_list:
        PMID_List.append(PMID.text)

    return PMID_List


# Finding cited paper by citing author

def find_cited_article(search_string, df):
    """Find the PMID that a given author has cited based on what is saved in df (DataFrame)

    :param search_string: string containing name of author (has to be in the same format PubMed saves author names in)
    :param df: DataFrame object where citing relations are stored
    :return: List of PMIDs that author given in search_string has cited
    """

    matched_PMIDs = []
    for i, article in enumerate(df["citing_author_list"]):
        for authorList in article:
            if search_string in authorList:
                matched_PMIDs.append(df.iloc[i]["PMID"])
    return matched_PMIDs



# Group elements of list into of sublists
def group_list_elements(input_list, group_sizes):
    """Makes sublists within a list

    Sizes of sublists are defined by list elements of group_sizes.

    TODO: Account for size discrepancies. Enforce sum(group_sizes) == len(input_list)

    :param input_list: List that you want to make sublists in
    :param group_sizes:  List containing the size you want each sublist to be
    :return: New list with elements of inputList as sublists of sizes defined in group_sizes
    """

    from itertools import islice
    it = iter(input_list)

    grouped_list = [list(islice(it, 0, i)) for i in group_sizes]

    return grouped_list

def output_csv(author_list):
    """
    Takes an author list dict and outputs a csv as a download
    :param author_list: input dict containing authors as keys and citation counts as values
                        or list containing tuples with 2 values, author and citation count respectively
    :return: csv file to download
    """
    # Create IO object to write file to
    si = StringIO()

    # Write csv file
    writer = csv.writer(si, delimiter=',')
    writer.writerows(author_list)

    # Construct file output
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    output.headers["Content-type"] = "text/csv"

    return output