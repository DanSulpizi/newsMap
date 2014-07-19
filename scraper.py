import requests
import re
import string
import heapq
from lxml import html
from nltk import word_tokenize, pos_tag
from copy import deepcopy

class location:   
    def __init__(self, country, province, city, location, pop):
        self.country = country
        self.province = province
        self.city = city
        self.location = location
        self.score = 0
        self.population = pop
        
    def __str__(self):
        return self.country + ", " + self.province + ", " + self.city + ",.  " + self.location + " " + str(self.score) + " " + str(self.population)
        
class article:   
    def __init__(self, headline, subline, date, url, source, locations):
        self.headline = headline
        self.subline = subline
        self.date = date
        self.url = url
        self.source = source
        self.locations = locations

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
    
    #add all the locations to a hashtable
    for location in locationList:
        if location[0] in h:
            h[location[0]] += location[1]
        else:
            h[location[0]] = location[1]
        
    returner = []
    length = 0.
    maxFound = 0.
    #get length(total score) and maximum score found
    for item in h:
        maxFound = max(h[item], maxFound)
        length += h[item] 
    
    ##THROW OUT VALUES THAT ARE TOO SMALL (size)
    if length != 0 and wordCount != 0:
        #if the most likely location is not very likely, we ignore all locations
        if maxFound/wordCount > 0.01:
            for item in h:
                i = h[item]/length
                if(i >= size): #and h[item] > maxFound/2):
                    returner.append([item, i])
    
    return returner

def findMatchingCities(cities, countries, cityList, countryList, size = 0.0):
    out = []
    
    maxPopulation = 1
    
    for city in cities:
        cityLister = cityList[city[0]]
        #for all cities that match city name (Berlin exists in more than one country)
        for city2 in cityLister:
            for country in countries:
                #if we can match a country and city, increase score
                if city2.country == country[0]:
                    location = deepcopy(city2)
                    #TODO Weightings
                    location.score = 0.75*(city[1]+country[1])
                    
                    #if city name is also a country name
                    
                    regexp = re.compile(r'\b%s\b' % location.city, re.I)
                    for countryFound in countryList:
                        if regexp.search(countryList[countryFound].lower()) is not None:
                            print "HAHA"
                            location.score /= 2
                    out.append(location)
                    
                    maxPopulation = max(maxPopulation, location.population)
                    
                    
    
    #all countries should be scored too
    for country in countries:
        if cityList[""]:
            for city in cityList[""]:
                if city.country == country[0]:
                    location = deepcopy(city)
                    location.score = country[1]
                    out.append(location)
        else:
            print "Warning: failed to load country list"
    
    ##Combine close cities with the same name
    #TODO
    ##Modify score based on population  
    
    for each in out:
        print each
    
def addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList):                
    found = False
    if w in outCityList:
        outCityList.append([w, score])
        found = True
            
    #if not already in list
    if(not found):
        if w in cityList:
            outCityList.append([w, score])
            found = True  
        
    found = False
    #add country codes
    for country in countryList:
        if w == country:
            # print countryList[country]
            #todo determine weightings
            outCountryList.append([country, score/2])
            found == True
    
    #if not already in list
    #add full country name
    if(not found and len(w) > 2):
        regexp = re.compile(r'\b%s\b' % w, re.I)
        for country in countryList: 
            if regexp.search(countryList[country].lower()) is not None:
                outCountryList.append([country, score/(countryList[country].count(' ')+1)])
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
            cityList[cityKey].append(location(city[1].lower(),city[2].lower(),city[3].lower().rstrip(),city[0].lower(),city[4].lower()))
        else:
            cityList[cityKey] = [location(city[1].lower(),city[2].lower(),city[3].lower().rstrip(),city[0].lower(),city[4].lower()),]
    f.close()
    
    return cityList

def workWithArticleItems(articleItems, cityList, countryList): 
    if articleItems != None:        
        headline = articleItems["headline"][0]
        subline = articleItems["subline"]
        if(len(subline) > 0): subline = subline[0]
        else: subline = ""
        date = articleItems["date"][0]
        url = articleItems["url"]
        source = "CBC"
    
        print ""
        print headline.replace(u'\u2019', '').replace(u'\u2014', '')
        print subline.replace(u'\u2019', '').replace(u'\u2014', '')
        print date
        print url
        print source
    
        outCityList = []
        outCountryList = []
        
        #HEADLINE CHECK
        
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
        
        #SUBLINE CHECK
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
        
        #CONTENT CHECK
        sentenceNum = len(articleItems["text"])
        sentenceCount = 0
        for sentence in articleItems["text"]:
            sentenceCount += 0
            #TODO DETERMINE WEIGHTINGS
            score = 1.5-((1/sentenceNum)*sentenceCount)
            tokens = word_tokenize(sentence)
            partsOfSpeech = pos_tag(tokens)
            
            NNPList = []
            for word in partsOfSpeech:
                wordCount += 1
                if word[1] == 'IN':
                    score *= 1.1
                if word[0] == 'near':
                    score *= 1.5
            
                if word[1] == 'NNP':
                    w = word[0].lower().replace('.','')
                    addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList)
        
        condensedCountries = getCondensedLocationList(outCountryList, wordCount, 0.05)
        condensedCities = getCondensedLocationList(outCityList, wordCount, 0.05)
        
        findMatchingCities(condensedCities, condensedCountries, cityList, countryList, 0.25)
    
def generateGoodLinksCBC(url = 'http://www.cbc.ca/news/world', xPath = '//body//div[@class="wrap8 landing-primary"]//a/@href'):
    linkList = generalScrape(url, xPath, True)
    cleanLinkList = []
    
    for link in linkList:
        if ("http://" not in link and "#" not in link and "?" not in link):
            cleanLinkList.append("http://www.cbc.ca" + link)
            print link
    
    countryList = loadCountryList()
    cityList = loadCityList()
    
    for link in cleanLinkList:
    # for link in [cleanLinkList[3]]:
        #scrape the sites getting location (hint look for proper nouns), headlines, date, and link ##STORE IN DATABASE
        
        #Headline

        articleItems = getItemsFromCBCArticle(link)
        # print articleItems
        workWithArticleItems(articleItems, cityList, countryList)