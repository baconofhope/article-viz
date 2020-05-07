from lxml import etree, objectify
import xml.etree.ElementTree as ET
from urllib.request import urlopen
from urllib.parse import urlparse
from urllib.parse import parse_qs
import requests
from bs4 import BeautifulSoup
import csv
import datetime
import time
import html as ihtml
from newsapi import NewsApiClient

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

news_api_key = "d6bf278b13984a789ace8431364b60b7"
google_news_url = "https://www.google.com/alerts/feeds/11834609579021016554/16869848966735516210"
scmp_china = "https://www.scmp.com/rss/4/feed"
bbc_asia = "http://feeds.bbci.co.uk/news/world/asia/rss.xml"
technode_china = "http://technode.com/tag/china/feed"

#runs once a day to check all news feeds, grab content, and save to elasticsearch index

#get xml feeds
def get_articles(url):
    root = ET.parse(urlopen(url)).getroot()
    #root = ET.parse("google_feed_test.xml").getroot()
    root.findall('.//entry')
    ns={"default": "http://www.w3.org/2005/Atom"}
    for item in root.findall('default:entry', ns):
        title = item.find("default:title", ns).text
        date = item.find("default:published", ns).text
        snippet = item.find("default:content", ns).text
        link_item = item.find("default:link", ns)
        link = link_item.attrib['href']
        parsed = urlparse(link)
        url = parse_qs(parsed.query)['url']
        body = get_article(url)
        yield {
                "_index": "rss_crawl_articles",
                "_type": "article",
                "body": body,
                "link": url,
                "snippet": snippet,
                "title": title,
                "created": date
        }

def get_article(url):
    time.sleep(5)
    response = requests.get(url, allow_redirects=True)
    print(url)
    soup = BeautifulSoup(ihtml.unescape(response.text), features="lxml")
    paragraphs = soup.find_all("p")
    body = ' '.join([p.text for p in paragraphs])
    return body

def get_from_google_news(newsapi):
    from_dates = ['2020-01-24','2020-01-25', '2020-01-26', '2020-01-27']
    to_dates = ['2020-01-24', '2020-01-25', '2020-01-26', '2020-01-27']

    for i in range(0, 4):
        all_articles = newsapi.get_everything(q='wuhan virus',
                                          #sources='abc-news,al-jazeera-english,ars-technica,associated-press,wired,engadget,techcrunch,gizmodo,'
                                          #        'cnn,reuters,business-insider,the-next-web,bbc-news,the-verge',
                                          from_param=from_dates[i],
                                          to=to_dates[i],
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
            try:
                body = get_article(url)
            except:
                print('unable to get article at %s' % url)
                continue

            yield {
                "_index": "google_news_articles",
                "_type": "article",
                "body": body,
                "link": url,
                "snippet": snippet,
                "title": title,
                "created": date,
                "source": source
            }


def main():
    es = Elasticsearch([{'host':'localhost','port':9200}])
    newsapi = NewsApiClient(api_key=news_api_key)
   # bulk(es, get_articles("google"))
    bulk(es, get_from_google_news(newsapi))


def outputCSV(self, data):
    with open("rss_feed_parsed.csv", "w+") as outputfile:
        writer = csv.writer(outputfile)
        writer.writerows(data)


if __name__ == "__main__":
    main()
