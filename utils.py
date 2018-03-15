import requests
import xml.etree.cElementTree as ET

import pandas as pd
from itertools import chain

def get_authorListCounts(searchString):
    # Get source PMIDs with search term

    sourcePMIDs = searchDB(searchString)

    # Get list of articles that sort each PMID from source list
    citedByList = getCitedByPMIDs(sourcePMIDs)

    # Get cite counts per PMID for grouping authors later
    citationsPerPMID = [len(PMID) for PMID in citedByList]

    # Flatten list
    flat_citedByList = list(chain.from_iterable(citedByList))


    # Get metadata for each of the articles that cite the source articles (authors and titles)
    citing_authorListPerPMID, _ = getPMIDsMetaData(flat_citedByList) # Contains citing author list for all source PMIDs

    # Group author list per source PMID
    citing_authorListPerPMIDGrouped = groupListElements(citing_authorListPerPMID, citationsPerPMID)


    # Construct DataFrame using extracted data
    df = pd.DataFrame(data = {'PMID': sourcePMIDs, 'citing_PMIDs':citedByList, 'citing_authorList':citing_authorListPerPMIDGrouped})

    # Total citations per source PMID
    df["tot_citations"] = [len(row) for row in df["citing_PMIDs"]]


    # Getting the full list of unique citing authors with counts
    ## Flatten list of lists for each source PMID
    full_authorList = [author.encode('utf-8') for article in df["citing_authorList"].tolist() for authorList in article for author in authorList]


    ## Get counts
    from collections import Counter
    authorListCounts = dict(Counter(full_authorList))

    return authorListCounts





def getCitedByPMIDs(inputPMIDList):


    # Base URL of the API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

    # Parameters for API call
    ## Might need to add API key in the future: https://www.ncbi.nlm.nih.gov/books/NBK25497/
    params = {
        "dbfrom": "pubmed",
        "linkname": "pubmed_pubmed_citedin",
        "id": inputPMIDList,
        "retmax": 100000,
        "api_key": "f818626ea79d1dfa33c18960ae05dbc8f808"
    }

    # Request the XML response from the API
    response = requests.get(base_url, params = params)

    # Construct ElementTree for parsing XML
    tree= ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()


    LinkSets = root.findall('LinkSet')

    # Iterate over input PMIDs and store the PMIDs of the articles that cite the input article
    citedByList = []
    for LinkSet in LinkSets:
        citedBy = []

        # Check if PMID has been cited, only find citing PMIDs if source PMID has been cited
        if LinkSet.find('LinkSetDb'):
            for id in LinkSet.find('LinkSetDb').iter('Id'):
                citedBy.append(id.text)

        citedByList.append(citedBy)


    return citedByList

def getPMIDsMetaData(inputPMID):
    # Base URL of the API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    inputPMID = ','.join(map(str, inputPMID))

    # Parameters for API call
    params = {
        "db": "pubmed",
        "id": inputPMID,
        "retmax": 100000,
        "api_key": "f818626ea79d1dfa33c18960ae05dbc8f808"

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



def searchDB(searchTerm):
    # Base URL of the API
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    # Parameters for API call
    params = {
        "db": "pubmed",
        "term": searchTerm,
        "retmax": 100000,
        "api_key": "f818626ea79d1dfa33c18960ae05dbc8f808"

    }

    response = requests.get(base_url, params=params)

    # Construct ElementTree for parsing XML
    tree= ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()


    IdList = root.find('IdList')

    PMIDList = []
    for PMID in IdList:
        PMIDList.append(PMID.text)

    return PMIDList


# Finding cited paper by citing author

def find_citedArticle(search_string, df):

    matched_PMIDs = []
    for i, article in enumerate(df["citing_authorList"]):
        for authorList in article:
            if search_string in authorList:
                matched_PMIDs.append(df.iloc[i]["PMID"])
    return matched_PMIDs



# Group elements of list into of sublists
def groupListElements(inputList, groupSizes):

    from itertools import islice
    it = iter(inputList)

    groupedList = [list(islice(it, 0, i)) for i in groupSizes]

    return groupedList

