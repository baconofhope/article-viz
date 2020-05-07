from newspaper import Article
import csv
from datetime import date, datetime, timedelta
import time
from newsapi import NewsApiClient
import sys

news_api_key = "d6bf278b13984a789ace8431364b60b7"

def get_article(url):
    article = Article(url)
    article.download()
    article.parse()
    article.nlp()
    return {"body": article.text, "nlp_keywords": article.keywords, "nlp_summary": article.summary}

def get_from_google_news(newsapi, from_date, to_date):

    all_articles = newsapi.get_everything(q='(wuhan AND virus) OR ncov OR covid OR coronavirus',
                                      from_param=from_date,
                                      to=to_date,
                                      language='en',
                                      sort_by='relevancy',
                                      page_size=100,
                                      page=1)
    for article in all_articles["articles"]:
        url = article["url"]
        snippet = article["description"]
        title = article["title"]
        date = article["publishedAt"]
        source = article["source"]["name"]
        article = {
            "link": url,
            "snippet": snippet,
            "title": title,
            "created": date,
            "source": source
        }
        try:
            article_data = get_article(url)
            article.update(article_data)
        except Exception as e:
            print('Unable to get article at %s' % url, file=sys.stderr)
            print(e)

        yield article

def outputCSV(data, filename):
    with open(filename, "w+") as outputfile:
        fields = ["body", "link", "snippet", "title", "created", "source", "nlp_keywords", "nlp_summary"]
        w = csv.DictWriter(outputfile, fieldnames=fields, restval="na")
        w.writeheader()
        w.writerows(data)

def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)

def scrape_news(date):
    newsapi = NewsApiClient(api_key=news_api_key)
    data = get_from_google_news(newsapi, date, date)
    filename = "news_api_nlp_%s.csv" % date
    outputCSV(data, filename)

def main():
    # start_date = date(2020, 1, 2)
    # end_date = date(2020, 1, 8)
    # for single_date in daterange(start_date, end_date):
    #     day = single_date.strftime("%Y-%m-%d")
    #     filename = "news_api_%s.csv" % day
    #     csv.reader()
    #     for url in urls:
    #         get_article(url)

    start_date = date(2020, 2, 24)
    end_date = date(2020, 3, 23)
    for single_date in daterange(start_date, end_date):
        day = single_date.strftime("%Y-%m-%d")
        scrape_news(day)

if __name__ == "__main__":
    main()
