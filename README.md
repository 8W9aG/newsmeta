# newsmeta

<a href="https://pypi.org/project/newsmeta/">
    <img alt="PyPi" src="https://img.shields.io/pypi/v/newsmeta">
</a>

A python module for parsing HTML into news components.

## Dependencies :globe_with_meridians:

* [Python 3.7](https://www.python.org/downloads/release/python-370/)
* [Newspaper3k 0.2.8](https://pypi.org/project/newspaper3k/)
* [BeautifulSoup 0.0.1](https://beautiful-soup-4.readthedocs.io/en/latest/)
* [Dateutil 2.8.2](https://pypi.org/project/python-dateutil/)
* [LangDetect 1.0.9](https://pypi.org/project/langdetect/)
* [Extruct 0.13.0](https://pypi.org/project/extruct/)
* [DeepTranslator 1.5.4](https://pypi.org/project/deep-translator/)

## Installation :inbox_tray:

This is a python package hosted on pypi, so to install simply run the following command:

`pip install newsmeta`

## Usage example :eyes:

In order to use this library simply feed it the downloaded HTML and the URL of the news piece, like so:

```py
import newsmeta

with open("article.html") as article_fh:
    article = newsmeta.parse(article_fh.read(), "http://www.article.com/article")
    print(article.title)
```

## License :memo:

The project is available under the [MIT License](LICENSE).
