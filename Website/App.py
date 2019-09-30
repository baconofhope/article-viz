from flask import Flask, render_template, request, json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, streaming_bulk
import json


app = Flask(__name__)

es = Elasticsearch([{'host':'localhost','port':9200}])

es_index = "radii_all"


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index')
def test():
    return render_template('index.html')

@app.route('/overview', methods=['GET'])
def overview():
    tag_keys=["key", "doc_count"]

    res = es.search(index=es_index, body={
    "aggs" : {
        "tags" : {
            "terms" : { "field" : "tags" } 
            }
        }
    })
    tag_output=[]
    for tag in res["aggregations"]["tags"]["buckets"]:
        if not tag['key'].startswith('cap') and tag['key']!='culture' and tag['key']!='featured':
            tag_output.append({your_key: tag[your_key] for your_key in tag_keys})
    return json.dumps(tag_output, indent=2)

@app.route('/search', methods=['POST'])
def filter():    
    print(request.form)
    data = query(request.form.getlist("search_terms[]"))
    response = json.dumps(data, indent=2)
    #print(data)
    return response
    
def intersection(lst1, lst2):  
    # Use of hybrid method 
    temp = set(lst2) 
    lst3 = [value for value in lst1 if value in temp] 
    return lst3 

def query(queryterms):
    hit_output = []
    tag_output = []
    hit_keys = ["tags", "title", "created", "link"]
    tag_keys=["key", "doc_count", "score"]
    query_string = ' '.join(queryterms)
    exclude_string = '|'.join(queryterms)
    res = es.search(index=es_index, body={"query": {
        "simple_query_string":
            {
                "query": query_string,
                "default_operator": "and"
            }
    },
        "aggregations": {
            "significant_words": {
                "significant_terms": {
                    "field": "tags",
                    "exclude": ".*(" + exclude_string + ").*"
    }}}})
    print(query_string)
    relevant_tags = []
    for tag in res["aggregations"]["significant_words"]["buckets"]:
        if not tag['key'].startswith('cap'):
            tag_output.append({your_key: tag[your_key] for your_key in tag_keys})
            relevant_tags.append(tag['key'])
            
    for hit in res["hits"]["hits"]:
         print(hit)
         hit_entry = {your_key: hit["_source"][your_key] for your_key in hit_keys}
         hit_tags = hit["_source"]["tags"]
         hit_entry["tags"] = intersection(relevant_tags, hit_tags)
         hit_output.append(hit_entry)
         
   
    

    return {"hits": hit_output, "tags": tag_output}

if __name__ == '__main__':
    app.debug = True
    app.run(host='localhost', port=9874)