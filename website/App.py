from flask import Flask, render_template, request, jsonify
from elasticsearch import Elasticsearch
import json
import psycopg2
from flask import g
from datetime import datetime

app = Flask(__name__)

es = Elasticsearch([{'host':'localhost','port':9200}])
es_index = "coronavirus_articles"

con = psycopg2.connect(database="kathyhuang", user="kathyhuang", password="", host="127.0.0.1", port="5432")
con.autocommit = True
cur = con.cursor()

f = open('data/topics.json',) 
TOPICS = json.load(f)

COLORS = ["#C7D2DD", "#F4D58F", "#E1C5D2", "#A8AAD7", "#B8E1D9",
                         "#DBBAE4", "#DEE487", "#A9E1C1", "#FAB88A", "#C1C39C",
                         "#F8C2C8", "#ECCB9B", "#C2DF96", "#AAC8DB", "#8BA3B8",
                        "#93A1AE", "#DCC8AB", "#C292AB", "#FAC8A7", "#B5AED8",
                         "#99DBB4", "#C5D9AE", "#F2F295", "#619FC7", "#689E74"]

class DataStore():
    EntityData=None
    EntityToArticleData=None
        
data=DataStore()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index')
def test():
    articles=[]
    return render_template('index.html')

@app.route("/get-entity-data",methods=["GET","POST"])
def returnEntityData():
    cur.execute("select dominant_topic, count(*) from coronavirus.article_topics group by dominant_topic order by count desc limit 5")
    response = cur.fetchall()
    top_categories = []
    response = [(10, 1348),  (9, 1049), (0, 1037), (12, 794), (8, 713)]
    for r in response:
        id = r[0]
        topic_info = TOPICS[id]
        name = topic_info["name"]
        keywords = topic_info["keywords"]
        top_categories.append({ "id": id,
                            "count": r[1],
                              "name": name,
                              "keywords": keywords})
    return jsonify(top_categories)

@app.route("/get-entity-article-ajax")
def returnEntityArticleAjax():
    entity = int(request.args.get('entity'))
    f=data.EntityToArticleData[entity] 
    return render_template("article_cards.html", articles=f)

@app.route('/search', methods=['POST'])
def filter(): 
    keywords = request.form.getlist("keywords[]")
    topics = request.form.getlist('topics[]')
    if len(keywords) == 0:
        results = get_article_info_topics(topics)
    else:
        article_ids,article_scores = get_article_ids(keywords)
        results = get_article_info(topics, article_scores, article_ids)
    #if no article ids, return a null error
    hit_count = len(results)
    if hit_count == 0:
        return render_template('article_cards.html', articles=[], hit_count=0);

    return render_template('article_cards.html', articles=results, hit_count=hit_count)

def get_article_ids(keywords):
    article_ids=[]
    query = ' '.join(keywords)
    res = es.search(index=es_index, _source=["id"], body={"query": {
        "simple_query_string" : { 
          "query": query
        }
      },
        "size": 5000
    })
    article_scores = {}
    for hit in res["hits"]["hits"]:
        article_ids.append(hit["_source"]["id"])
        article_scores[hit["_source"]["id"]] = hit["_score"]
    return article_ids, article_scores

def get_article_info_topics(topics):
    output = []
    topic_clause = [' and topic_' + str(t) + '>.06' for t in topics]
    topic_clause = ' '.join(topic_clause)
    cur.execute("select * from \
                coronavirus.articles as a right join coronavirus.article_topics as t on a.id = t.id \
                where t.id is not null " + topic_clause)

    response = cur.fetchall()
    for r in response:
        topics = r[9:33]
        sort_order = sorted(range(len(topics)), key=lambda k: topics[k], reverse=True)
        i = 0
        top_topics = []
        for s in sort_order:
            if i > 2:
                break
            top_topics.append({"id": s, "strength": topics[s], "name": TOPICS[s]["name"], "color": COLORS[s]})
            i += 1
        output.append({"id": r[0],
                       "title": r[4],
                       "created": r[5],
                       "source": r[6],
                       "link": r[2],
                       "topics": top_topics})

    return output

def get_article_info(topics, article_scores=[], article_ids=[]):
    output = []
    topic_clause = [' and topic_' + str(t) + '>.06' for t in topics]
    topic_clause = ' '.join(topic_clause)
    if len(article_ids)==0:
        cur.execute("select * from \
                coronavirus.articles as a right join coronavirus.article_topics as t on a.id = t.id \
                where t.id is not null " + topic_clause)
    else:
        cur.execute("select * from \
        coronavirus.articles as a right join coronavirus.article_topics as t on a.id = t.id \
        where a.id in %(articles)s " + topic_clause , {"articles": tuple(article_ids)})

    response = cur.fetchall()
    for r in response:
        topics = r[9:33]
        sort_order = sorted(range(len(topics)), key=lambda k: topics[k], reverse=True)
        i = 0
        top_topics = []
        for s in sort_order:
            if i > 2:
                break
            top_topics.append({"id": s, "strength": topics[s], "name": TOPICS[s]["name"], "color": COLORS[s]})
            i += 1
        output.append({"id": r[0],
                       "title": r[4],
                       "created": r[5],
                       "source": r[6],
                       "link": r[2],
                        "relevance_score": article_scores[r[0]],
                       "topics": top_topics})

    output=sorted(output, key = lambda i: i['relevance_score'], reverse=True)

    return output

def query_articles(keywords, topics):
    output = []
    topics = ['topic_' + str(t) for t in topics]
    topic_terms = ', ' + ','.join(topics)
    keyword_terms = '&'.join(keywords)
    topic_values = '+'.join(topics)
    query = "SELECT t.id, title, created, source, link %s from \
                (SELECT id, title, created, source, link, (setweight(to_tsvector(title),'A') || \
                setweight(to_tsvector(body),'B') || \
                setweight(to_tsvector(source),'C')) as document \
                FROM coronavirus.articles) \
                p_search right join coronavirus.article_topics as t on p_search.id = t.id \
                WHERE p_search.document @@ to_tsquery('%s') \
                ORDER BY \
                ts_rank(p_search.document, to_tsquery('%s'))+%s \
                DESC" % (topic_terms, keyword_terms, keyword_terms, topic_values)
    cur.execute(query)

    response = cur.fetchall()
    for r in response:
        doc_topics = dict(zip(topics, r[5:]))

        output.append({"id": r[0],
        "title": r[1],
        "created": r[2],
        "source": r[3],
        "link": r[4],
        "topics": doc_topics})


    return output

def get_entity_ids(entities):
    cur.execute("select id from entity where name in %s", entities)
    response = cur.fetchall()
    g.entity_ids=[item[0] for item in response]
    return g.entity_ids

def get_entity_info(entity_names):
    output = []
    entity_ids=[]
    article_ids = g.article_ids
    cur.execute("select id, e.name, e.type, count(m.*), avg(sentiment) from mention as m left join entity as e on m.entity_id=e.id where article_id in %(articles)s and name in %(entities)s group by entity_id, e.name, e.type", {"articles": tuple(article_ids), "entities": tuple(entity_names)})
    response = cur.fetchall()
    for r in response:
        output.append({ "id": r[0],
        "name": r[1],
        "entity_type": r[2],
        "frequency": r[3],
        "avg_sentiment": r[4] })
        entity_ids.append(r[0])
    g.entity_ids=entity_ids
    return output
    
def get_entity_article():
    output={}
    cur.execute("select distinct on(entity_id, article_id, title, url, date, author, publication) entity_id, article_id, a.url, a.title, a.date, a.author, a.publication, m.sentence from mention as m left join article as a on m.article_id=a.id where entity_id in %s and article_id in %s order by date desc", 
            (tuple(g.entity_ids), tuple(g.article_ids)))
    responses = cur.fetchall()
    for r in responses:
        entity_id=r[0]
        article_id=r[1]
        url=r[2]
        title=r[3]
        date=r[4].strftime("%Y-%m-%d")
        author=r[5]
        publication=r[6]
        mention=r[7]
        if entity_id in output.keys():
            articles=output[entity_id]
        else:
            articles=[]
            output[entity_id]=articles
        article={"link": url, "title": title, "created": date, "author": author, "publication": publication, "entity_mention": mention}
        articles.append(article)
    data.EntityToArticleData=output
    
def process_result(res):
    hit_keys = ["entity_tags", "title", "created", "publication", "link"]
    tag_keys=["key", "doc_count", "score"]
    hit_output=[]
    tag_output=[]
    relevant_tags=[]
    entities=[]
    for tag in res["aggregations"]["tags"]["buckets"]:
        if tag["score"] > 0.05:
            entities.append(tag["key"])
            
    for hit in res["hits"]["hits"]:
         hit_entry = {your_key: hit["_source"][your_key] for your_key in hit_keys}
         hit_output.append(hit_entry)
    
    data.EntityData = get_entity_info(entities)
    #return {"hits": hit_output, "entities": data.EntityData}
    return hit_output


if __name__ == '__main__':
    app.debug = True
    app.run(host='localhost', port=9875)