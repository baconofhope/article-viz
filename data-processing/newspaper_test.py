from newspaper import Article

url = 'http://fox13now.com/2013/12/30/new-year-new-laws-obamacare-pot-guns-and-drones/'
url = 'https://slate.com/technology/2020/01/china-coronavirus-social-media-rumors-misinformation.html'
article = Article(url)
article.download()
article.parse()
article.text

article.nlp()
article.keywords
article.summary