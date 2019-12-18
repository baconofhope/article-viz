from flask import Flask, render_template, request, json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, streaming_bulk
import json
import psycopg2
from flask import g

app = Flask(__name__)

es = Elasticsearch([{'host':'localhost','port':9200}])
con = psycopg2.connect(database="thesis", user="kathy", password="", host="127.0.0.1", port="5432")
con.autocommit = True
cur = con.cursor()

es_index = "all_the_news"

class DataStore():
     EntityData=None
        
data=DataStore()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index')
def test():
    articles=[]
    return render_template('index.html')

@app.route('/data')
def dummydata():
    with open('data/elsa_result_processed_tech.json') as read_file:
        data = json.load(read_file)
        return json.dumps({"data": data}, indent=2);
    
@app.route("/get-data",methods=["GET","POST"])
def returnEntityData():
    f=data.EntityData 
    return json.dumps(f, indent=2)

@app.route('/search', methods=['POST'])
def filter(): 
    query_str = request.form.get("query_term")
    get_article_ids(query_str)
    #if no article ids, return a null error
    if len(g.article_ids) == 0:
        return render_template('index.html', articles=[], hit_count=0);
    hit_count, articles = query(query_str)    
    #response = json.dumps(data, indent=2)
    #print(data)
    print(hit_count)
    print(articles)
    return render_template('index.html', articles=articles, hit_count=hit_count)

def query(query):
    res = es.search(index=es_index, body={"query": {
        "simple_query_string" : { 
          "query": query
        }
      },
        "size": 20,
        "aggregations": {
            "tags": {
                "significant_terms": {
                    "field": "entity_tags",
                    "size": 30
    }}}})
    output = process_result(res)
    #output["hit_count"] = res["hits"]["total"]
    return res["hits"]["total"], output

def get_article_ids(query):
    article_ids=[]
    res = es.search(index=es_index, _source=["article_id"], body={"query": {
        "simple_query_string" : { 
          "query": query
        }
      },
        "size": 1000                                     
    })

    for hit in res["hits"]["hits"]:
        article_ids.append(hit["_source"]["article_id"])
    g.article_ids = article_ids
    return article_ids

def get_entity_ids(entities):
    cur.execute("select id from entity where name in %s", entities)
    response = cur.fetchall()
    return [item[0] for item in response]

def get_entity_info(entity_names):
    output = []
    article_ids = g.article_ids
    cur.execute("select entity_id, e.name, e.type, count(m.*), avg(sentiment) from mention as m left join entity as e on m.entity_id=e.id where article_id in %(articles)s and name in %(entities)s group by entity_id, e.name, e.type", {"articles": tuple(article_ids), "entities": tuple(entity_names)})
    response = cur.fetchall()
    for r in response:
        output.append({ "id": r[0],
        "name": r[1],
        "entity_type": r[2],
        "frequency": r[3],
        "avg_sentiment": r[4] })
    return output
    
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