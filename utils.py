import requests
import xml.etree.cElementTree as ET

import pandas as pd
from itertools import chain

from io import StringIO
from flask import make_response
import csv

def get_author_list_counts_search(search_string, option = 'all'):
    """Returns a list of authors that have cited papers from search result


    :param search_string: PubMed search string to use for the database search

    :param options: string option for omitting source authors from output
                    three options: 'all', 'exclude_source', 'aggressive_exclude_source'
                    'all': include all results,
                    'exclude_source': exclude authors from source PMIDs,
                    'aggressive_exclude_source': exclude authors from source PMIDs and any authors who have
                    co-authored with any of the source authors

    :return: dict containing author names as keys and number of occurrences as values
    """

    # Get source PMIDs (PubMed ID) with search term
    source_PMIDs = search_DB(search_string)

    return get_author_list_counts(source_PMIDs, option)



def get_author_list_counts(source_PMIDs, option = 'all'):
    """Returns a list of authors that have cited papers from list of PMIDs

    :param options: string option for omitting source authors from output
                three options: 'all', 'exclude_source', 'aggressive_exclude_source'
                'all': include all results,
                'exclude_source': exclude authors from source PMIDs,
                'aggressive_exclude_source': exclude authors from source PMIDs and any authors who have
                co-authored with any of the source authors
    :return: dict containing author names as keys and number of occurrences as values


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
    df = create_dataframe(source_PMIDs, cited_by_list, citing_author_list_per_PMID_grouped)

    grouped = df.groupby('citing_author').aggregate(lambda x: ','.join(x).split(','))
    grouped['author_counts'] = grouped['PMID'].apply(lambda x: len(x))

    # Remove source authors if option is selected
    if option == 'exclude_source':
        remove_source_authors(grouped)
    elif option == 'aggressive_exclude_source':
        aggressive_remove_source_authors(grouped, citing_author_list_per_PMID_grouped)

    # Seperate cited and citing PMIDs into seperate lists
    cited_PMIDs = grouped['PMID']
    citing_PMIDs = grouped['citing_PMID']

    author_list_counts = dict(zip(grouped.index.tolist(), grouped['author_counts'].tolist()))

    return author_list_counts, cited_PMIDs, citing_PMIDs

def create_dataframe(source_PMIDs, cited_by_list, citing_author_list_per_PMID_grouped):

    df = pd.DataFrame(data={'PMID': source_PMIDs, 'citing_PMIDs': cited_by_list,
                            'citing_author_list': citing_author_list_per_PMID_grouped})

    cP = df.apply(lambda x: pd.Series(x['citing_PMIDs']), axis=1).stack().reset_index(level=1, drop=True)
    cAs = df.apply(lambda x: pd.Series(x['citing_author_list']), axis=1).stack().reset_index(level=1, drop=True)
    cP.name = 'citing_PMID'
    cAs.name = 'citing_authors'
    df = df.drop('citing_PMIDs', axis=1).drop('citing_author_list', axis=1).join(pd.concat([cP, cAs], axis=1))
    df = df.reset_index(drop=True)

    cA = df.apply(lambda x: pd.Series(x['citing_authors']), axis=1).stack().reset_index(level=1, drop=True)
    cA.name = 'citing_author'
    df = df.drop('citing_authors', axis=1).join(cA, how='right')
    df = df.reset_index(drop=True)

    return df

def remove_source_authors(df):
    """Remove authors from citing author list if they authored a paper in source PMIDs

        :param df: Dataframe holding citing PMIDs and authors per source PMID

        :return: Dataframe
    """

    # Get source PMIDs from Dataframe
    source_PMIDs = list(chain.from_iterable(df['PMID']))

    # Get all authors from source PMIDs
    author_list_per_PMID, _ = get_PMIDs_metadata(source_PMIDs)
    source_authors = set(chain.from_iterable(author_list_per_PMID))

    # Find intersection of source authors and citing authors
    citing_authors = set(df.index)

    citing_source_authors = source_authors.intersection(citing_authors)

    # Drop source authors from Dataframe
    df.drop(pd.Index(citing_source_authors), inplace=True)


    return df


def aggressive_remove_source_authors(df, grouped_citing_authors):
    """Remove authors from citing author list if they authored a paper in source PMIDs and remove any authors who have
                co-authored with any of the source authors

        :param df: Dataframe holding citing PMIDs and authors per source PMID
        :param grouped_source_authors: A list with sublists of source authors grouped per PMID

        :return: Dataframe
    """

    # Get source PMIDs from Dataframe
    source_PMIDs = list(chain.from_iterable(df['PMID']))

    # Get all authors from source PMIDs
    author_list_per_PMID, _ = get_PMIDs_metadata(source_PMIDs)
    source_authors = set(chain.from_iterable(author_list_per_PMID))

    source_authors_coauthors = set(find_coauthors(source_authors, grouped_citing_authors))

    # Find intersection of source authors and citing authors
    citing_authors = set(df.index)

    citing_source_authors_coauthors = source_authors_coauthors.intersection(citing_authors)

    # Drop source authors from Dataframe
    df.drop(pd.Index(citing_source_authors_coauthors), inplace=True)


    return df


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
        "api_key": None,
        "sort": 'relevance'
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
        "api_key": None,
        "sort": 'relevance'

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
        "retmax": 300,
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

def find_coauthors(author_list, grouped_author_list):
    """
    Finds all the co_authors for a given list of authors based on a list of authors per PMID
    :param author_list: list of authors
    :param grouped_author_list: a list of groups of authors, per citing PMID per source PMID
    :return: list of co-authors of the authors in author_list (includes the names in author_list)
    """
    coauthor_list = []

    # For each author, find if they are in the grouped_author_list, if they are, add entire group
    for author in author_list:
        # grouped_author_list is grouped by source PMIDs, citing PMIDs that cite the source PMIDs and authors of
        # citing PMIDs
        for source_PMID in grouped_author_list:
            if not source_PMID:  # Skip any  source PMIDs with not citations
                continue
            for citing_PMID in source_PMID:
                if author in citing_PMID:
                    coauthor_list.append(citing_PMID)


    # Flatten list and remove duplicates
    coauthor_list = list(set(chain.from_iterable(coauthor_list)))

    return coauthor_list

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

