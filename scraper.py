import requests
import re
import string
import heapq
from lxml import html
from nltk import word_tokenize, pos_tag
from copy import deepcopy
from math import log

class Location:   
    def __init__(self, country, province, city, location, pop):
        self.country = country
        self.province = province
        self.city = city
        self.location = location
        self.score = 0
        self.population = float(pop)
        
    def __str__(self):
        return self.country + ", " + self.province + ", " + self.city + ",.  " + self.location + " " + str(self.score) + " " + str(self.population)
        
class Article:   
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
    text = tree.xpath('//body//div[@class="content-body story"]//div[@class="story-body"]/div[@class="story-content"]/p//text()')
    return {"headline" : headline, "subline" : subline, "date" : date, "url" : url, "text" : text}

#MERGES IDENTICAL LOCATION NAMES
def getCondensedLocationList(locationList, wordCount):
    #TODO DETERMINE WEIGHTINGS OF WORDCOUNT
    if(wordCount == 0): return []
    
    h = {}
    
    #add all the locations to a hashtable
    for location in locationList:
        if location[0] in h:
            h[location[0]] += location[1]
        else:
            h[location[0]] = location[1]
        
    returner = []
    length = 0.
    #get length(total score) and maximum score found
    for item in h:
        length += h[item] 
    
    ##THROW OUT VALUES THAT ARE TOO SMALL (size)
    if length != 0:
        for item in h:
            i = h[item]/length
            returner.append([item, i])
    
    return returner
    
#FINDS CITIES THAT EXIST IN COUNTRIES
def findMatchingCities(cities, countries, cityList, countryList, size = 0.0):
    out = []
    h = {}
    
    maxPopulation = 1
    
    for city in cities:
        # cityLister = cityList[city[0]]
        # for all cities that match city name (Berlin exists in more than one country)
        # for city2 in cityLister:
        
        regexp = re.compile(r'\b%s\b' % city[0], re.I)
        for cityFound in cityList:
            if regexp.search(cityList[cityFound][0].city.lower()) is not None:
                for city2 in cityList[cityFound]:
                    for country in countries:
                        #if we can match a country and city, increase score
                        if city2.country == country[0]:
                            location = deepcopy(city2)
                            #TODO Weightings
                            location.score = (city[1]+country[1])
                            
                            #if city name is also a country name
                            for word in location.city.split(' '):
                                regexp = re.compile(r'\b%s\b' % word, re.I)
                                for countryFound in countryList:
                                    if regexp.search(countryList[countryFound].lower()) is not None:
                                        location.score /= 2
                            
                            if location.city in h:
                                h[city[0]].append(location)
                            else:
                                h[city[0]] = [location,]
                            
                            maxPopulation = max(maxPopulation, location.population)

    #all countries should be scored too
    for country in countries:
        if cityList[""]:
            for city in cityList[""]:
                if city.country == country[0]:
                    location = deepcopy(city)
                    location.score = country[1]
                    if location.city in h:
                        h[""].append(location)
                    else:
                        h[""] = [location,]
        else:
            print "Warning: failed to load country list"
    
    #TODO can I clean the incoming data so this isn't needed?
    ##Combine close cities with the same name
    for each in h:
        a = []
        b = {}
        maxLocationPop = 0
        for location in h[each]:
            locationArea = location.location[:3]
            maxLocationPop = max(maxLocationPop, location.population)
            if not locationArea in b:
                b[locationArea] = True
                a.append(location)
        
        h[each] = a
        ##Modify score based on population  
        for location in h[each]:
            if(location.population > 0 and maxLocationPop > 1):
                location.score = ((0.5)*location.score + (0.5)*location.score*(log(location.population)/log(maxLocationPop)))
            out.append(location)

    out.sort(key=lambda x: x.score, reverse=True)
    
    for each in out:
        print each
 
def addCountryOrCity(w, score, cityList, countryList, outCityList, outCountryList):                
    found = False
    if w in outCityList:
        outCityList.append([w, score])
        found = True
            
    #if not already in list
    # if(not found):
        # if w in cityList:
            # outCityList.append([w, score])
            # found = True  
                          
    if(not found):
        regexp = re.compile(r'\b%s\b' % w, re.I)
        for city in cityList:
            cityName = cityList[city][0].city.lower()
            if regexp.search(cityName) is not None:
                cityMatch = len(w)/len(cityName)
                outCityList.append([w, score*cityMatch])
        
    found = False
    #add country codes
    for country in countryList:
        if w == country:
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
            cityList[cityKey].append(Location(city[1].lower(),city[2].lower(),city[3].lower().rstrip(),city[0].lower(),city[4].lower()))
        else:
            cityList[cityKey] = [Location(city[1].lower(),city[2].lower(),city[3].lower().rstrip(),city[0].lower(),city[4].lower()),]
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
        print headline.replace(u'\u2019', '').replace(u'\u2014', '').replace(u'\u201c', '').replace(u'\u200b', '').replace(u'\u201d','')
        print subline.replace(u'\u2019', '').replace(u'\u2014', '').replace(u'\u201c', '').replace(u'\u200b', '').replace(u'\u201d','')
        print date
        print url
        print source
        
        
        outCityList = []
        outCountryList = []
        
        #HEADLINE CHECK
        
        names = ["Vladimir Putin", "Putin", "President Barack Obama", "Barack Obama", "Obama", "Merek",]
        
        wordCount = 0
        score = 5
        
        headlineWorker = headline.replace('-', ' ')
        sublineWorker = subline.replace('-', ' ')
        for word in names:
            headlineWorker = headlineWorker.replace(word, '')
            sublineWorker = sublineWorker.replace(word, '')
        
        tokens = word_tokenize(headlineWorker)
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
        tokens = word_tokenize(sublineWorker)
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
            sentence = sentence.replace('-', ' ')
            for word in names:
                sentence = sentence.replace(word, '')
            
            sentenceCount += 0
            #TODO DETERMINE WEIGHTINGS (This weighting makes first sentence worth more than the last sentence
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
        
        #TODO determine size (0.05 gets good results)
        condensedCountries = getCondensedLocationList(outCountryList, wordCount)
        condensedCities = getCondensedLocationList(outCityList, wordCount)
        
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
    
    # for link in cleanLinkList:
    for link in [cleanLinkList[0]]:
        articleItems = getItemsFromCBCArticle(link)
        workWithArticleItems(articleItems, cityList, countryList)