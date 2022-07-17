from urllib.request import urlopen as uReq
from urllib.error import HTTPError
from bs4 import BeautifulSoup as soup
from datetime import datetime

# to change based on what years you want to analyze
SELECTED_YEARS = {"2016"}
SELECTED_MONTHS = {"01"}
SELECTED_DATES = {"01"}
# topics to look at from https://us.cnn.com/article/sitemap-2016.html
SELECTED_TOPICS = {"Politics", "Opinion", "US", "Asia", "Middle East",
                   "Election Center 2016", "China", "Economy", "Business",
                   "Tech", "Health", "World", "Africa"}
OUTPUT_FILENAME = "cnn_articles.csv"
# hardcoded bias and publisher data
BIAS = 0
PUBLISHER = "CNN"
# main site map of all CNN years
SITE_MAP_URL = "https://us.cnn.com/sitemap.html"
# CNN standard starting url
CNN_URL = "https://us.cnn.com"

# begin time measurement
start_time = datetime.now()

f, fe = None, None


def scrape_this_month(this_topic, politics_month_soup,
                      politics_month_url, article_num):
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
    global f, fe

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

    if SELECTED_MONTHS and this_month not in SELECTED_MONTHS:
        return

    # number of articles this month of this topic
    no_articles_this_month = len(articles_this_month)

    # iterating through all links in the Politics month site
    for article_i in range(len(articles_this_month)):
        this_day = dates_this_month[0].text[8:]
        if SELECTED_DATES and this_day not in SELECTED_DATES:
            # assuming CNN orders the articles by date
            break

        # getting to the article webpage
        article_url = articles_this_month[article_i].a["href"]
        try:
            uArticleClient = uReq(article_url)
            article_html = uArticleClient.read()
            uArticleClient.close()
            article_soup = soup(article_html, "html.parser")
        except HTTPError:
            error_msg_title = "".join(["HTTP Error in title in article: ",
                                       article_url, "\n"])
            fe.write(error_msg_title)
            print(error_msg_title)
            continue

            # getting the article's title, double-quoted to include commas
        try:
            article_title = '"' + article_soup.h1.text + '"'
        except AttributeError:
            error_msg_title = "".join(["Attribute Error in title in article: ",
                                       article_url, "\n"])
            fe.write(error_msg_title)
            print(error_msg_title)
            continue

        # getting last updated article time and article date
        # month and year have been retrieved above, in str format
        article_date = dates_this_month[article_i].text[-2:]

        # finding all paragraphs of the article's contents
        article_paragraphs = article_soup. \
            findAll("p", {"class": "paragraph inline-placeholder"})

        # getting the whole article's contents, enclosed in "" to include commas
        # in the article
        article_content = '"'
        try:
            for a_paragraph in article_paragraphs:
                text = a_paragraph.text.strip()
                article_content = ' '.join([article_content, text])
        except AttributeError:
            error_msg_content = "".join([
                "Attribute Error in content in article: ", article_url, "\n"])
            fe.write(error_msg_content)
            print(error_msg_content)
            continue
        article_content += '"'

        # number of characters in article content
        article_length = len(article_content)

        # MS Excel has a cell character limit of 32767
        # if an article passes over 31500 (for added buffer since ’ becomes
        # â€™), it will be truncated to the first 31500 characters,
        # and added TRUNCATED under comments. article_length remains
        # original
        if article_length > 31500:
            article_content = '"'.join([article_content[:31500], ''])
            article_length = str(article_length) + "," + "TRUNCATED"
        elif article_length < 10:
            # some "articles" are actually videos or graphics that don't have
            # text. EMPTY is added under comments. article_length remains
            article_length = str(article_length) + "," + "EMPTY"

        # write article info into csv file
        f.write(",".join([
            str(article_num),
            article_url,
            article_title,
            article_content,
            PUBLISHER,
            str(BIAS),
            this_topic,
            this_year,
            this_month,
            article_date,
            str(article_length),
            "\n"]))

        article_num += 1

        # print status every 10 articles completed with format:
        # topic | month | year | article_i / no. of articles | time elapsed
        if article_i % 10 == 0:
            print("{} {} {} {}/{} {}".format(this_topic, this_month,
                                             this_year, article_i,
                                             no_articles_this_month,
                                             datetime.now() - start_time))

    return article_num


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
    global f, fe

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
        # goes to this single month site of Politics
        politics_month_url = cnn_url_dup + topic.a["href"]
        try:
            uMonthClient = uReq(politics_month_url)
            politics_month_html = uMonthClient.read()
            uMonthClient.close()
            topic_soup = soup(politics_month_html, "html.parser")
        except HTTPError:
            error_msg_title = "".join(["HTTP Error in title in topic: ",
                                       politics_month_url, "\n"])
            fe.write(error_msg_title)
            print(error_msg_title)
            continue

        # scrapes and adds all articles in the month
        try:
            article_num = scrape_this_month(topic.text, topic_soup,
                                            politics_month_url, article_num)
        except AttributeError:
            error_msg_month = "".join(["Attribute Error in month: ",
                                       politics_month_url, "\n"])
            fe.write(error_msg_month)
            print(error_msg_month)
            continue

    return article_num


def run():
    # initialize csv file to write into
    global f, fe
    try:
        f = open(OUTPUT_FILENAME, "w", encoding="utf-8")
        headers = ", link, title, article, publisher, bias, " \
                  "topic, year, month, day, characters, comments\n"
        f.write(headers)

        fe = open("errors.txt", "w", encoding="utf-8")
    except PermissionError:
        exit("File is currently open. Please close it.")


    try:
        # opening up connection, grabbing the top-level page
        uTopClient = uReq(SITE_MAP_URL)
        site_map_html = uTopClient.read()
        uTopClient.close()
        # html parsing
        page_soup = soup(site_map_html, "html.parser")
    except HTTPError:
        error_msg_top = "".join(["HTTP Error in title in top site: ",
                                 SITE_MAP_URL, "\n"])
        fe.write(error_msg_top)
        print(error_msg_top)
        f.close()
        fe.close()
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
                uYearClient = uReq(selected_year_url)
                selected_year_html = uYearClient.read()
                uYearClient.close()
                page_soup = soup(selected_year_html, "html.parser")
            except HTTPError:
                error_msg_year = "".join(["HTTP Error in year: ",
                                          selected_year_url, "\n"])
                fe.write(error_msg_year)
                print(error_msg_year)
                continue

            try:
                gen_article_num = scrape_this_year(CNN_URL, page_soup,
                                                   gen_article_num)
            except AttributeError:
                error_msg_year = "".join(["Attribute Error in year: ",
                                          selected_year_url, "\n"])
                fe.write(error_msg_year)
                print(error_msg_year)
                continue

    # close csv file
    f.close()
    fe.close()

    # calculate time elapsed
    print(f"Total time elapsed: {datetime.now() - start_time}")


def main():
    run()


if __name__ == "__main__":
    main()
