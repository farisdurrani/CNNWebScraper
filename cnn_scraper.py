from dataclasses import dataclass
from bs4 import BeautifulSoup as soup
from datetime import datetime
from random import randint
from urllib.error import HTTPError
import pandas as pd
import multiprocessing as mp
import requests

# To change based on what years you want to analyze.
# Set of years, e.g., "2016" to filter
SELECTED_YEARS = {"2022"}
# Set of numeric months, e.g., "01", "02", "12" to filter; can be empty set() to
# include all
SELECTED_MONTHS = {"01"}
# {"01", "02", "03", "04", "05", "06"}
# {"07", "08", "09", "10", "11", "12"}
# Set of numeric dates, e.g., "01", "31", "12" to filter; can be empty set() to
# include all
SELECTED_DATES = set()
# topics to look at from https://us.cnn.com/article/sitemap-2016.html
SELECTED_TOPICS = {"US", "Politics", "Asia", "Middle East", "Business",
                   "Health", "World", "Opinion", "Americas",
                   "Tech", "Africa", "China", "Election Center 2016"}
OUTPUT_FILENAME = f"outputs/cnn_articles-{'&'.join(SELECTED_YEARS)}" \
                  f"-{randint(1_000, 9_999)}.csv"
GET_EVERY_X_ARTICLE_PER_MONTH_TOPIC = 2  # change to 1 to get all articles, 2 to get 50%
USE_MULTIPROCESSING = True  # very fast but can crash in a heavy environment

# CNN standard starting url
CNN_URL = "https://www.cnn.com"
# main site map of all CNN years
SITE_MAP_URL = f"{CNN_URL}/sitemap.html"

# begin time measurement
start_time = datetime.now()

contentsToWrite = []
errorsToWrite = []


@dataclass
class ArticleMetadata:
    article_i: int
    article_url: str
    this_year: int
    this_month: int
    this_day: int
    this_section: str
    num_articles_this_month: int


def scrape_this_month(this_section, politics_month_soup,
                      politics_month_url, article_num) -> int:
    """
    Scrapes all articles of one month of one topic and adds them all to the csv
    :param politics_month_soup: the page soup of the site hosting all the
    articles of the month of that topic
    e.g. page soup of https://us.cnn.com/politics/article/sitemap-2016-1.html
    :param politics_month_url: URL of this month's politics
    e.g. https://us.cnn.com/politics/article/sitemap-2016-1.html
    :param article_num: the current general article number count
    :return: latest general article number to be updated globally
    """

    # finds the collection of all articles with their dates
    articles_dates_this_month = politics_month_soup.findAll(
        "div", {"class": "sitemap-entry"})[1]

    # finds all article links in the single month site of Politics
    articles_this_month = articles_dates_this_month \
        .findAll("span", {"class": "sitemap-link"})

    # finds all dates linked to all articles in this month
    dates_this_month = articles_dates_this_month \
        .findAll("span", {"class", "date"})

    # if there is a mismatch between number of articles and number of dates,
    # stop and fix
    if len(articles_this_month) != len(dates_this_month):
        exit("314: No. articles != No. dates in this month at "
             + politics_month_url)

    # gets the month once from the first date entry
    this_month = dates_this_month[0].text[5:7]
    this_year = dates_this_month[0].text[:4]

    # number of articles this month of this topic
    num_articles_this_month = len(articles_this_month)

    articles_meta = [ArticleMetadata(
        article_i=i,
        article_url=article_html.a["href"],
        this_year=this_year,
        this_month=this_month,
        this_day=dates_this_month[i].text[8:],
        this_section=this_section,
        num_articles_this_month=num_articles_this_month,
    ) for i, article_html in enumerate(articles_this_month)]

    with mp.Pool(mp.cpu_count() if USE_MULTIPROCESSING else 1) as pool:
        this_month_to_write = pool.map(scrape_this_article, articles_meta)

    contentsToWrite.extend(this_month_to_write)

    print(f"Finished {this_section} at {datetime.now() - start_time}\n")

    return article_num


def scrape_this_article(article_metadata: ArticleMetadata):
    article_i = article_metadata.article_i
    article_url = article_metadata.article_url
    this_year = article_metadata.this_year
    this_month = article_metadata.this_month
    this_day = article_metadata.this_day
    this_section = article_metadata.this_section
    num_articles_this_month = article_metadata.num_articles_this_month

    # iterating through all links in the Politics month site
    if article_i % GET_EVERY_X_ARTICLE_PER_MONTH_TOPIC != 0:
        return {}

    if SELECTED_DATES and this_day not in SELECTED_DATES:
        return {}

    # getting to the article webpage
    try:
        article_html = requests.get(article_url)
        article_soup = soup(article_html.text, "html.parser")
    except HTTPError:
        error_msg_title = "".join(["HTTP Error in title in article: ",
                                   article_url, "\n"])
        errorsToWrite.append(error_msg_title)
        print(error_msg_title)
        return {}
    except requests.exceptions.ConnectTimeout:
        error_msg_title = f"ConnectionTimeout on {article_url}\n"
        errorsToWrite.append(error_msg_title)
        print(error_msg_title)
        return {}
    except requests.exceptions.TooManyRedirects:
        error_msg_title = f"TooManyRedirects on {article_url}\n"
        errorsToWrite.append(error_msg_title)
        print(error_msg_title)
        return {}

    # get article headline (title)
    try:
        article_title = article_soup.h1.get_text().strip()
    except AttributeError:
        error_msg_title = "".join(["Attribute Error in title in article: ",
                                   article_url, "\n"])
        errorsToWrite.append(error_msg_title)
        print(error_msg_title)
        return {}

    # get author
    author_html = article_soup.find("span", {"class": "byline__name"})
    author_name = None
    if author_html:
        try:
            author_name = author_html.get_text()
        except AttributeError:
            pass

    # getting the whole article's contents
    try:
        article_content = ' '.join([p.get_text().strip() for p in
                                    article_soup.findAll("p", {
                                        "class": "paragraph inline-placeholder"})])
    except AttributeError:
        error_msg_content = "".join([
            "Attribute Error in content in article: ", article_url, "\n"])
        errorsToWrite.append(error_msg_content)
        print(error_msg_content)
        return {}

    # number of characters in article content
    article_length = len(article_content)

    if article_length < 10:
        # some "articles" are actually videos or graphics that don't have
        # text
        return {}

    # print status every 10 articles completed with format:
    # topic | month | year | article_i / no. of articles | time elapsed
    if article_i % 10 == 0:
        print("{} {} {} {}/{} {}".format(this_section, this_month,
                                         this_year, article_i,
                                         num_articles_this_month,
                                         datetime.now() - start_time))

    # MS Excel has a cell character limit of 32767
    # if an article passes over 31500 (for added buffer since ’ becomes
    # â€™), it will be truncated to the first 31500 characters
    # article_length remains as original
    # write article info an array of dicts to later be written into CSV
    return {
        "timestamp": f"{this_year}-{this_month}-{this_day}",
        "webUrl": article_url,
        "headline": article_title,
        "sectionName": this_section,
        "site": "CNN",
        "bodyContent": article_content[:31500],
        "article_length": article_length,
        "author_name": author_name
    }


def scrape_this_year(cnn_url_dup, year_soup, article_num):
    """
    scrapes all articles in this year and adds them all to the csv
    :param year_soup the page soup of the site hosting all the articles of this
    year
    e.g. page soup of https://us.cnn.com/article/sitemap-2016.html
    :param cnn_url_dup duplicate of cnn_url
    :param article_num the current general article number count
    :return: latest general article number to be updated globally
    """

    # grabs each section e.g. Politics, Entertainment for each month
    sections_this_year = year_soup.findAll("li", {"class": "section"})

    # grabs Politics of each month
    topics_this_year = []
    for section in sections_this_year:
        if section.text in SELECTED_TOPICS:
            topics_this_year.append(section)

    # goes through every topic of every month in this year and scrapes all its
    # articles
    for topic in topics_this_year:
        # skip unneeded months
        this_url_month = topic.a["href"].split("-")[-1][:-5]
        if len(this_url_month) == 1:
            this_url_month = '0' + this_url_month
        if SELECTED_MONTHS and this_url_month not in SELECTED_MONTHS:
            continue

        # goes to this single month site of Politics
        politics_month_url = cnn_url_dup + topic.a["href"]

        try:
            politics_month_html = requests.get(politics_month_url)
            topic_soup = soup(politics_month_html.text, "html.parser")
        except HTTPError:
            error_msg_title = "".join(["HTTP Error in title in topic: ",
                                       politics_month_url, "\n"])
            errorsToWrite.append(error_msg_title)
            print(error_msg_title)
            continue

        # scrapes and adds all articles in the month
        try:
            article_num = scrape_this_month(topic.text, topic_soup,
                                            politics_month_url, article_num)
        except AttributeError:
            error_msg_month = "".join(["Attribute Error in month: ",
                                       politics_month_url, "\n"])
            errorsToWrite.append(error_msg_month)
            print(error_msg_month)
            continue

    return article_num


def run():
    try:
        # opening up connection, grabbing the top-level page
        site_map_html = requests.get(SITE_MAP_URL)
        # html parsing
        page_soup = soup(site_map_html.text, "html.parser")
    except HTTPError:
        error_msg_top = "".join(["HTTP Error in title in top site: ",
                                 SITE_MAP_URL, "\n"])
        errorsToWrite.append(error_msg_top)
        print(error_msg_top)
        save_and_close_files()
        exit(-1)
        return

    # grabs each year
    years = page_soup.find("ul", {"class": "sitemap-year"}) \
        .findAll("li", {"class": "date"})

    # global variable--general article count
    gen_article_num = 1

    # iterate over all years to find the selected_year and go to that year page
    for year in years:
        if year.text.strip() in SELECTED_YEARS:
            selected_year_url = CNN_URL + year.a["href"]
            try:
                selected_year_html = requests.get(selected_year_url)
                page_soup = soup(selected_year_html.text, "html.parser")
            except HTTPError:
                error_msg_year = "".join(["HTTP Error in year: ",
                                          selected_year_url, "\n"])
                errorsToWrite.append(error_msg_year)
                print(error_msg_year)
                continue

            try:
                gen_article_num = scrape_this_year(CNN_URL, page_soup,
                                                   gen_article_num)
            except AttributeError:
                error_msg_year = "".join(["Attribute Error in year: ",
                                          selected_year_url, "\n"])
                errorsToWrite.append(error_msg_year)
                print(error_msg_year)
                continue

    save_and_close_files()

    # calculate time elapsed
    print(f"Total time elapsed: {datetime.now() - start_time}")


def save_and_close_files():
    df = pd.DataFrame(contentsToWrite)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.to_csv(OUTPUT_FILENAME)
    with open(f"{OUTPUT_FILENAME[:-4]}-ERRORS.txt", "w",
              encoding="utf-8") as fe:
        fe.write('\n'.join(errorsToWrite))


def main():
    run()


if __name__ == "__main__":
    main()
