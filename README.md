# get_citing_authors

Web app to get the a list of authors that cite a given list of papers through the [PubMed API](https://www.ncbi.nlm.nih.gov/home/develop/api/).

You can input papers either as a comma seperated list of PubMed IDs (PMIDs) or you can provide a PubMed search term and the app will get the authors that cite all of the search results.

Live example running on Heroku can be found [here](https://flask-fetch-citation.herokuapp.com/).

## Using locally

### Prerequisites
The app is written in Python 3.6, you may run into issues if you are running Python 2.7.

To install all the required packages, run the following in a terminal within the directory:

```
pip install -r requirements.txt
```

### Usage

Once you have all the prerequisites installed, you can run `main.py` in the terminal from the directory it is located in to start a local webserver.

```
python main.py
```

You could access the functions of the app in the `utils.py` file individually if you prefer that too.

The two main functions are `get_author_list_counts_search()` and `get_author_list_counts()`. These take a search term and a list of PMIDs respectively.

`get_author_list_counts_search()` will get a list of PMIDs from the PubMed API by searching the database using the search term provided.

The output will be a Python dictionary where the keys are author names and the values are the number of times that author has cited any of the input articles.


## API Key
Currently there is no API key used for all of the requests sent to the PubMed API. This [limits](https://www.ncbi.nlm.nih.gov/books/NBK25497/#_chapter2_Usage_Guidelines_and_Requiremen_) the number of requests you can make.

To register your personal API key, you will need to register a free NCBI account and generate one.
The functions `get_cited_by_PMIDs()`, `get_PMIDs_metadata()`, `search_DB()` in `utils.py` define an `api_key` value which is currently set to `None`. You will have to replace `None` with your API key given as a string.



## Deploying
To deploy on [Heroku](http://heroku.com), simply clone this repo to your Heroku repo.

## Contributing

Happy to take feature requests and pull requests!


## Authors

* **Sihao Lu** - [@SihaoLu](https://twitter.com/SihaoLu)

Project made possible by [Labrigger](http://labrigger.com/blog/)

