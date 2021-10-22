"""The main module for the newsmeta library."""
from dataclasses import dataclass
import datetime
import typing
import urllib
import json
import re

import newspaper
from bs4 import BeautifulSoup
from langdetect import detect
from dateutil import parser
from w3lib.html import get_base_url
import extruct
import deep_translator


__version__ = "1.0.1"

TEXT_TAG_BLACKLIST = [
    "[document]",
    "noscript",
    "header",
    "meta",
    "head",
    "input",
    "script",
    "style",
    "svg",
    "iframe",
    "figcation",
]
TRANSLATOR = deep_translator.GoogleTranslator(source="auto", target="en")


@dataclass
class ArticleItem:
    title: str
    description: str
    url: str
    published_date: datetime.datetime
    content: str
    authors: typing.List[str]
    tags: typing.List[str]
    language: str
    translated_language: typing.Optional[str]
    translated_content: typing.Optional[str]


def text_from_element(element: typing.Any) -> str:
    """Find text in an element."""
    current_output = ""
    for tag in element.findAll(text=True):
        if tag.parent.name in TEXT_TAG_BLACKLIST:
            continue
        current_output += f"{tag} "
    return current_output


def check_article_text(article_3k: newspaper.Article, soup: BeautifulSoup):
    """Checks that the articles text is valid."""
    if article_3k.is_valid_body():
        return

    def biggest_tag(tag: str, main_output: str) -> str:
        tags = soup.findAll(tag)
        if tags:
            for article_tag in tags:
                current_output = text_from_element(article_tag)
                if current_output is None:
                    continue
                if main_output is None:
                    main_output = ""
                if len(current_output.split()) > len(main_output.split()):
                    main_output = current_output
        return main_output

    main_output = biggest_tag("article", "")
    main_output = biggest_tag("main", main_output)
    if main_output:
        article_3k.set_text(main_output)


def extract_published_date(article_3k: newspaper.Article, soup: BeautifulSoup) -> datetime.datetime:
    """Extract the published date."""
    published_date = article_3k.publish_date
    # Try and find it in the URL
    if published_date is None:
        url_parse = urllib.parse.urlparse(article_3k.url)
        path_split = url_parse.path.split("/")
        if len(path_split) >= 6:
            year = path_split[1]
            month = path_split[4]
            day = path_split[5]
            try:
                published_date = parser.parse(f"{year}/{month}/{day}")
            except parser.ParserError:
                pass
        if published_date is None:
            if len(path_split) >= 5:
                year = path_split[1]
                month = path_split[3]
                day = path_split[4]
                try:
                    published_date = parser.parse(f"{year}/{month}/{day}")
                except parser.ParserError:
                    pass
        if published_date is None:
            if len(path_split) >= 4:
                year = path_split[1]
                month = path_split[2]
                day = path_split[3]
                try:
                    published_date = parser.parse(f"{year}/{month}/{day}")
                except parser.ParserError:
                    pass
    # Try and find it in the jsonld
    if published_date is None:
        jsonlds = soup.findAll("script", {"type": "application/ld+json"})
        for jsonld_tag in jsonlds:
            if jsonld_tag.string is None:
                continue
            try:
                jsonld = json.loads(jsonld_tag.string)
                if "datePublished" in jsonld:
                    try:
                        published_date = parser.parse(jsonld["datePublished"])
                    except parser.ParserError:
                        pass
            except json.JSONDecodeError:
                matches = re.search(
                    '"datePublished":[^"]*"(.[^"]*)', jsonld_tag.string
                )
                if matches:
                    published_date = parser.parse(matches.groups()[0])
    # Try and find it in the HTML
    if published_date is None:
        html_tags = {
            "span": {"class": "date"},
            "div": {"class": "cnnix-timestamp"},
            "span": {"stream": "time_62656"},
        }
        for html_tag in html_tags:
            date_element = soup.find(html_tag, html_tags[html_tag])
            if date_element is not None:
                published_date = parser.parse(
                    date_element.get_text(strip=True).replace("Updated", "").strip()
                )
    # Try and find it in the extruct metadata
    if published_date is None:
        base_url = get_base_url(article_3k.html, article_3k.url)
        data = extruct.extract(article_3k.html, base_url=base_url)
        for og in data["opengraph"]:
            if published_date is not None:
                break
            for property in og["properties"]:
                if property[0] == "og:pubdate":
                    published_date = parser.parse(property[1])
                    if published_date is not None:
                        break
    # Try and find it in the HTML meta tags
    if published_date is None:
        meta_tags = set(["pubdate", "lastmod", "date"])
        for meta_tag in meta_tags:
            meta_element = soup.find("meta", {"name": meta_tag})
            if meta_element is not None:
                published_date = parser.parse(meta_element["content"])
    # Try and find it in the Javascript
    if published_date is None:
        for script_tag in soup.find_all("script"):
            script_tag = script_tag.text
            if script_tag is None:
                continue
            script_text = script_tag.strip()
            matches = re.search(r'"publish_date":\s+"(.*)"', script_text)
            if matches is not None:
                published_date = parser.parse(matches.group(1))
    if published_date is None:
        raise Exception(
            f"Could not find published date for article: {article_3k.url}"
        )
    return published_date


def translate(text: str) -> str:
    """Translate text."""
    text_paragraphs = [x.strip() for x in text.split("\n")]
    translated_paragraphs = []
    for text_paragraph in text_paragraphs:
        if not text_paragraph:
            continue
        paragraph_parts: typing.List[typing.List[str]] = []
        for word in text_paragraph.split():
            if paragraph_parts:
                if len(" ".join(paragraph_parts[-1] + [word])) > 4000:
                    paragraph_parts.append([word])
                else:
                    paragraph_parts[-1].append(word)
            else:
                paragraph_parts.append([word])
        translated_paragraph_parts = []
        for paragraph_part in paragraph_parts:
            try:
                translated_paragraph = TRANSLATOR.translate(
                    " ".join(paragraph_part)
                )
                if translated_paragraph is None:
                    continue
                translated_paragraph_parts.append(translated_paragraph)
            except (
                deep_translator.exceptions.NotValidPayload,
                deep_translator.exceptions.RequestError,
            ) as e:
                pass
        translated_paragraphs.append(" ".join(translated_paragraph_parts))
    return "\n".join(translated_paragraphs)


def parse(html: str, url: str) -> typing.Optional[ArticleItem]:
    """Parse an HTML string into an Article Item."""
    english_language_code = "en"
    article_3k = newspaper.Article(url)
    article_3k.download(input_html=html)
    article_3k.parse()
    soup = BeautifulSoup(article_3k.html, "html5lib")
    check_article_text(article_3k, soup)
    if article_3k.text:
        language = detect(article_3k.text)
        published_date = extract_published_date(
            article_3k, soup
        )
        title = article_3k.title
        return ArticleItem(
            title,
            article_3k.meta_description,
            url,
            published_date,
            article_3k.text,
            article_3k.authors,
            list(article_3k.tags),
            language,
            None if language == english_language_code else english_language_code,
            None if language == english_language_code else translate(article_3k.text)
        )
    return None
