import requests
from lxml import html

##SCRAPING TOOLS
def generalScrape(url, xPath, forbidDupes = False):
    page = requests.get(url)
    tree = html.fromstring(page.text)
    table = tree.xpath(xPath)
    
    returnList = []
    
    if(not forbidDupes):
        return table

    else:
        seen = set()
        for item in table:
            if item not in seen: #remove duplicates in a given page, for all pages would take much longer
                seen.add(item)
                returnList.append(item)
                
    return returnList
    
def getItemsFromCBCArticle(url):
    page = requests.get(url)
    tree = html.fromstring(page.text)
    headline = tree.xpath('//body//div[@class="content-body story"]/div[@id="content"]/div[@class="colfull"]/div[@class="story-headline"]/h1[@class="story-title"]/text()')
    subline = tree.xpath('//body//div[@class="content-body story"]/div[@id="content"]/div[@class="colfull"]/h3[@class="story-deck"]/text()')
    if(headline == []): return
    date = tree.xpath('//body//div[@class="content-body story"]//p[@class="small lighttext"]//text()')
    text = tree.xpath('//body//div[@class="content-body story"]//div[@class="story-body"]/div[@class="story-content"]/p//text()')
    return {"headline" : headline, "subline" : subline, "date" : date, "url" : url, "text" : text, "source": "cbc"}