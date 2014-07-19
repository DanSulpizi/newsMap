import requests
import re
import string
import heapq
from lxml import html
from nltk import word_tokenize, pos_tag

class location:   
    def __init__(self, country, provence, city, location):
        self.country = country
        self.provence = provence
        self.city = city
        self.location = location
        self.score = 0


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
    date = tree.xpath('//body//div[@class="content-body story"]//span[@class="delimited"]/text()')
    text = tree.xpath('//body//div[@class="content-body story"]//div[@class="story-body"]/div[@class="story-content"]/p/text()')
    return {"headline" : headline, "subline" : subline, "date" : date, "url" : url, "text" : text}

def getCondensedLocationList(locationList, wordCount, size = 0.0):
    #TODO DETERMINE WEIGHTINGS OF WORDCOUNT
    h = {}
    
    for location in locationList:
        if location[0] in h:
            h[location[0]] += location[1]
        else:
            h[location[0]] = location[1]
        
    returner = []
    length = 0.
    maxFound = 0.
    for item in h:
        maxFound = max(h[item], maxFound)
        length += h[item] 
    
    if length != 0 and wordCount != 0:
        if maxFound/wordCount > 0.01:
            for item in h:
                i = h[item]/length
                if(i >= size and h[item] > maxFound/2):
                    returner.append([item, i])
    
    return returner

def findMatchingCities(cities, countries, cityList, size = 0.0):
    out = []
    
    for city in cities:
        cityLister = cityList[city[0]]
        for city2 in cityLister:
            for country in countries:
                if city2[0] == country[0]:
                    out.append([city[1]+country[1], city2])
    
    # print cityList[''];
                    
    for country in countries:
        if cityList[""]:
            for city in cityList[""]:
                if city[0] == country[0]:
                    out.append([country[1], city])
        else:
            print "Warning: failed to load country list"
                    
    print out
    
def addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList):                
    found = False
    #if already in list
    if w in outCityList:
        outCityList.append([w, score])
        found = True
            
    if(not found):
        if w in cityList:
            outCityList.append([w, score])
            found = True  
        
    found = False
    for country in countryList:
        if w == country:
            # print countryList[country]
            outCountryList.append([country, score/2])
            found == True
    
    if(not found and len(w) > 2):
        regexp = re.compile(r'\b%s\b' % w, re.I)
        for country in countryList: 
            if regexp.search(countryList[country].lower()) is not None:
                outCountryList.append([country, score])
                found == True

def loadCountryList():
    #load Countries and Country Abbreviations
    f = open('CountriesAbr.txt', 'r')
    countryList = {}
    for line in f:
        abbrCount = line.split(',')
        countryList[abbrCount[0].lower()] = abbrCount[1].lower().rstrip()
    f.close()
    
    return countryList
    
def loadCityList():
    #Load Cities
    f = open('Cities.txt', 'r')
    cityList = {}
    i = 0
    for line in f:
        city = line.split(',')
        cityKey = city[3].lower().replace('.','').rstrip()
        if cityKey in cityList:
            cityList[cityKey].append([city[1].lower(),city[2].lower(),city[3].lower(),city[0].lower(),],)
        else:
            cityList[cityKey] = [[city[1].lower(),city[2].lower(),city[3].lower(),city[0].lower(),],]
    f.close()
    
    # print cityList
    
    return cityList
                
def generateGoodLinksCBC(url = 'http://www.cbc.ca/news/world', xPath = '//body//div[@class="wrap8 landing-primary"]//a/@href'):
    linkList = generalScrape(url, xPath, True)
    cleanLinkList = []
    
    countryList = loadCountryList()
    cityList = loadCityList()
    
    for link in linkList:
        if ("http://" not in link and "#" not in link and "?" not in link):
            cleanLinkList.append("http://www.cbc.ca" + link)
            
    for link in cleanLinkList:
    # for link in [cleanLinkList[3]]:
        #scrape the sites getting location (hint look for proper nouns), headlines, date, and link ##STORE IN DATABASE
        
        #Headline
        articleItems = getItemsFromCBCArticle(link)
        
        headline = articleItems["headline"][0]
        subline = articleItems["subline"]
        if(len(subline) > 0): subline = subline[0]
        else: subline = ""
        date = articleItems["date"][0]
        url = articleItems["url"]
        source = "CBC"
        
        if articleItems != None:
            outCityList = []
            outCountryList = []
            
            wordCount = 0
            score = 5
            tokens = word_tokenize(headline.replace('-', ' '))
            partsOfSpeech = pos_tag(tokens)
            for word in partsOfSpeech:
                # print word
                wordCount += 1
                #TODO DETERMINE WEIGHTINGS
                if word[1] == 'IN':
                    score *= 1.1
                if word[0] == 'near':
                    score *= 1.5
                    
                if word[1] == 'NNP':
                    w = word[0].lower().replace('.','')
                    addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList)            
            
            score = 2

            tokens = word_tokenize(subline.replace('-', ' '))
            partsOfSpeech = pos_tag(tokens)
            for word in partsOfSpeech:
                # print word
                wordCount += 1
                if word[1] == 'IN':
                    score *= 1.1
                if word[0] == 'near':
                    score *= 1.5
                    
                if word[1] == 'NNP':
                    w = word[0].lower().replace('.','')
                    addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList)
            
            sentenceNum = len(articleItems["text"])
            sentenceCount = 0
            for sentence in articleItems["text"]:
                sentenceCount += 0
                #TODO DETERMINE WEIGHTINGS
                score = 1.5-((1/sentenceNum)*sentenceCount)
                tokens = word_tokenize(sentence)
                partsOfSpeech = pos_tag(tokens)
                
                for word in partsOfSpeech:
                    wordCount += 1
                    if word[1] == 'IN':
                        score *= 1.1
                    if word[0] == 'near':
                        score *= 1.5
                
                    if word[1] == 'NNP':
                        w = word[0].lower().replace('.','')
                        addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList)

            print ""
            print headline
            print subline
            print date
            print url
            print source
            
            condensedCountries = getCondensedLocationList(outCountryList, wordCount, 0.1)
            condensedCities = getCondensedLocationList(outCityList, wordCount, 0.1)
            
            findMatchingCities(condensedCities, condensedCountries, cityList, 0.25)
            
            #Location (preferably cities not country)
            #Secondary Locations
            #Date
            #Link
            #Tags
            #News Source (CBC)