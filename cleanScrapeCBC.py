import requests
import re
import string
import heapq
from lxml import html
from nltk import word_tokenize, pos_tag
from copy import deepcopy
from math import log   

import provinceList

import sqlite3
conn = sqlite3.connect('locations.db')
    
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
    
def getItemsFromCBCArticle(url):
    page = requests.get(url)
    tree = html.fromstring(page.text)
    headline = tree.xpath('//body//div[@class="content-body story"]/div[@id="content"]/div[@class="colfull"]/div[@class="story-headline"]/h1[@class="story-title"]/text()')
    subline = tree.xpath('//body//div[@class="content-body story"]/div[@id="content"]/div[@class="colfull"]/h3[@class="story-deck"]/text()')
    if(headline == []): return
    # date = tree.xpath('//body//div[@class="content-body story"]//span[@class="delimited"]/text()')
    date = tree.xpath('//body//div[@class="content-body story"]//p[@class="small lighttext"]//text()')
    text = tree.xpath('//body//div[@class="content-body story"]//div[@class="story-body"]/div[@class="story-content"]/p//text()')
    return {"headline" : headline, "subline" : subline, "date" : date, "url" : url, "text" : text, "source": "cbc"}
    
#SCORE SYSTEMS
class NewsPageClassifier:
    class ListLoader:
        countryList = []

        def loadCountryList(self):
            #load Countries and Country Abbreviations
            f = open('CountriesAbr.txt', 'r')
            countryList = {}
            for line in f:
                abbrCount = line.split(',')
                self.countryList.append([abbrCount[0].lower(), abbrCount[1].lower().rstrip()])
            f.close()
   
    class Score:
        #TODO   
        isHeadline = 0
        isSubline = 0
        
        numCombinedScores = 1
        
        #do these words appear before the NNP?
        numInBefore = 0
        numNearBefore = 0
        numFromBefore = 0
        
        #sentence position (SentenceNum/numSentence)
        sentencePosition = 0.
        
        matchPercent = 1.
        
        perCombinedScores = 1
        
        provinceMatch = False
        
        def add(self, score):
            self.isHeadline = (self.isHeadline or score.isHeadline)
            self.isSubline = (self.isSubline or score.isSubline)
            self.provinceMatch = (self.provinceMatch or score.provinceMatch)
            
            #not averages
            self.numInBefore   = (self.numInBefore*self.numCombinedScores + score.numInBefore)/(self.numCombinedScores + 1.)
            self.numNearBefore = (self.numNearBefore*self.numCombinedScores + score.numNearBefore)/(self.numCombinedScores + 1.)
            self.numFromBefore = (self.numFromBefore*self.numCombinedScores + score.numFromBefore)/(self.numCombinedScores + 1.)
            
            #averages
            self.sentencePosition = (score.sentencePosition + self.sentencePosition*self.numCombinedScores)/(self.numCombinedScores + 1.)
            self.matchPercent = (score.matchPercent + self.matchPercent*self.numCombinedScores)/(self.numCombinedScores + 1.)

            self.numCombinedScores += score.numCombinedScores   
        
        def combine(self, score, matchBonus = True):
            matchBonus = 1.5
            
            self.isHeadline = (self.isHeadline or score.isHeadline) + (self.isHeadline and score.isHeadline)
            self.isSubline = (self.isSubline or score.isSubline) + (self.isHeadline and score.isHeadline)
            self.provinceMatch = (self.provinceMatch or score.provinceMatch)
            
            self.numInBefore = (self.numInBefore*self.numCombinedScores + score.numInBefore*score.numCombinedScores) / (self.numCombinedScores + score.numCombinedScores)
            self.numNearBefore = (self.numNearBefore*self.numCombinedScores + score.numNearBefore*score.numCombinedScores) / (self.numCombinedScores + score.numCombinedScores)
            self.numFromBefore = (self.numFromBefore*self.numCombinedScores + score.numFromBefore*score.numCombinedScores) / (self.numCombinedScores + score.numCombinedScores)
            
            self.sentencePosition = (self.sentencePosition*self.numCombinedScores + score.sentencePosition*score.numCombinedScores) / (self.numCombinedScores + score.numCombinedScores)
            
            self.matchPercent = (self.matchPercent*score.matchPercent)
            if(matchBonus): self.matchPercent*= matchBonus
                
            self.numCombinedScores = (score.numCombinedScores + self.numCombinedScores)/2

        def toValue(self):
            #TODO machine learn these scores / think up more criteria
            
            out = self.perCombinedScores
            # out = 1
        
            out *= 1+(self.isHeadline)
            out *= 1+(0.33*self.isSubline)
            
            out *= 1+self.numInBefore/float(self.numCombinedScores)
            out *= 1+self.numNearBefore/float(self.numCombinedScores)
            out *= 1+self.numFromBefore/float(self.numCombinedScores)
            
            out *= self.matchPercent
            out *= 1.25-(0.5)*self.sentencePosition
            
            out *= 1+(0.5)*self.provinceMatch
            return out
        
        def __str__(self):
            return str(self.toValue())
            # return self.printInfo()
            
        def printInfo(self):
            #Value, headline, subline, in before, near before, from before, sentence pos, match %, numScores
            return str(self.toValue()) + "   :   " + str(int(self.isHeadline)) + " " + str(int(self.isSubline)) + " " + str(int(self.provinceMatch)) + " "  + " " + str(self.numInBefore) + " " + str(self.numNearBefore) + " " + str(self.numFromBefore) + " " + str(self.sentencePosition) + " " + str(self.matchPercent) + " " + str(self.numCombinedScores)
   
    class Location:  
        def __init__(self, key, country, province, city, location, score, pop):
            self.country = country
            self.province = province
            self.city = city
            self.key = key
            self.location = location
            self.score = score
            self.population = float(pop)
            
        def __str__(self):
            return self.country + "," + self.province + "," + self.city + "," + self.location + "," + str(self.population)
        
        def printInfo(self):
            return str(self.score) + "     " + str(self.key) + " " + self.country + ", " + self.province + ", " + self.city + ",.  " + self.location + " " + str(self.population)
            
    class Article:   
        def __init__(self, headline, subline, date, url, source, primaryLocation, secondaryLocations):
            self.headline = headline
            self.subline = subline
            self.date = date
            self.url = url
            self.source = source
            self.primaryLocation = primaryLocation
            self.secondaryLocations = secondaryLocations
            
        def __str__(self):
            return "\n######################################################\n" + str(self.headline).replace(u'\u2019', '').replace(u'\u2014', '').replace(u'\u201c', '').replace(u'\u200b', '').replace(u'\u201d','') + "\n" + str(self.subline).replace(u'\u2019', '').replace(u'\u2014', '').replace(u'\u201c', '').replace(u'\u200b', '').replace(u'\u201d','') + "\n" + str(self.date) + "\n" + str(self.url) + "\n" + str(self.source) + "\n" + str(self.primaryLocation) + "\n" + str(self.secondaryLocations) + "\n"

    #Todo, get data list of officials
    forbiddenNames = ["Vladimir Putin", "Putin", "President Barack Obama", "Barack Obama", "Obama", "Merek", "Costa Concordia", "Nobel Prize", "Van Dam", "Mark Rutte", "Iron Dome", "Iron Curtain",]

    def __init__(self, articleItems):
        self.articleItems = articleItems
        self.locationLists = self.ListLoader()
        self.locationLists.loadCountryList()
    
    def findCountriesInPOS(self, pos, isHeadline=False, isSubline=False, sentence = 0, sentenceNum = 1):   
        INCount = 0
        nearCount = 0
        fromCount = 0
        
        for word in pos: 
            self.length += 1 
            if word[1] == 'IN':
                INCount += 1
            if word[0].lower() == 'near':
                nearCount += 1
            if word[0].lower() == 'from':
                fromCount += 1
                
            #if the word is a proper noun or if it starts uppercase and is an adjective (Language)
            if len(word[0]) > 1 and (word[1] == 'NNP' or (word[0].istitle() and (word[1] == 'NNS' or word[1] == 'JJ'))) :
                w = word[0].lower().replace('.','')
                # print word
                
                currScore = self.Score()
                
                currScore.isHeadline = isHeadline
                currScore.isSubline = isSubline

                currScore.numInBefore = INCount
                currScore.numNearBefore = nearCount
                currScore.numFromBefore = fromCount
                
                currScore.sentencePosition = (sentence/float(sentenceNum))
                
                inList = False
                for item in self.listOfNNP:
                    if(item[0] == w): 
                        inList = True
                        item[1].add(currScore)
                
                if(not inList): self.listOfNNP.append([w, deepcopy(currScore)])

                found = False
                #add country codes
                for country in self.locationLists.countryList:
                    if w == country[0]:
                        
                        currScore.matchPercent = 1
                    
                        if w in self.countriesInArticle: self.countriesInArticle[w].add(currScore)
                        else: self.countriesInArticle[w] = deepcopy(currScore)
                        found = True
                        break #only find highest on list
                        
                if(not found and len(w) > 2):
                    regexp = re.compile(r'\b%s\b' % w, re.I)
                    for country in self.locationLists.countryList:
                        if regexp.search(country[1].lower()) is not None:
                        
                            currScore.matchPercent = len(w)/float(len(country[1].replace(' ','')))
                                
                            if country[0] in self.countriesInArticle: self.countriesInArticle[country[0]].add(currScore)
                            else: self.countriesInArticle[country[0]] = deepcopy(currScore)
                            found = True
                            
    def findCitiesInCountries(self):
        c = conn.cursor()
        currResults = []
        self.locationList = []
        
        foundProvinces = []
        
        for country in self.countriesInArticle:
            t = (country.upper(),)
            c.execute('SELECT location, city FROM locations WHERE country=?', t)
            for result in c.fetchall():
                currResults.append(result)
        
        for NNP in self.listOfNNP:
            if NNP[0] in provinceList.provinces:
                foundProvinces.append(NNP[0])
            else:
                found = False
                for province in provinceList.provinces:
                    for each in provinceList.provinces[province]:
                        if NNP[0] == each:
                            found = True
                            foundProvinces.append(province)
                            break
                    if(found): break
        
        # print foundProvinces
        
        for NNP in self.listOfNNP:
            regexp = re.compile(r'\b%s\b' % NNP[0], re.I)
            for result in currResults: #each city
                if regexp.search(result[-1]) is not None:
                    c.execute('SELECT country,province,city,location,population FROM locations WHERE location=?', (result[0],))
                    loc = c.fetchone()

                    sc = deepcopy(self.countriesInArticle[loc[0].lower()])
                    
                    #Score based on match percent

                    inList = False
                    #combine cities with same name, country, and general area: only return most populous area
                    for location in self.locationList:
                        
                        #if one of the locations is in a foundProvince, don't combine them unless it's the same province!
                        provinceFound = (location.province.lower() in foundProvinces) or (loc[1].lower() in foundProvinces) 
                        
                        if location.city == loc[2] and location.country == loc[0] and (not provinceFound or location.province == loc[1]):# and location.location[:3] == loc[3][:4]:
                            inList = True
                            # print ""
                            # print location.score.numCombinedScores
                            # print sc.numCombinedScores
                            # location.score.add(sc)
                            
                            if provinceFound:
                                location.score.provinceMatch = True
                            
                            if(float(loc[4]) > location.population):
                                location.country = loc[0]  
                                location.province = loc[1] 
                                location.city = loc[2]     
                                location.location = loc[3]
                                location.population = float(loc[4])
                                                        
                            inList2 = False
                            for key in location.key:
                                if(key == NNP[0]):
                                    inList2 = True
                                    break
                                    
                            if(not inList2): location.key.append(NNP[0])
                            break
                    
                    #TODO should cities gain the headline bonus of their country?
                    NNP[-1].matchPercent = len(NNP[0])/float(len(result[-1].replace(' ','')))
                    sc.combine(NNP[-1])
                    
                    if(not inList):
                        self.locationList.append(self.Location([NNP[0]], loc[0],loc[1],loc[2],loc[3], sc, loc[4]))
    
        #add countries to results (no city in particular, just country)
        for country in self.countriesInArticle:
            t = (country.upper(),)
            c.execute('SELECT country,province,city,location,population FROM locations WHERE country=? and city=""', t)
            loc = c.fetchone()
            
            if loc: self.locationList.append(self.Location('', loc[0],loc[1],loc[2],loc[3], self.countriesInArticle[country], loc[4]))
        
        #TODO add provinces and states to results
        
        length = float(self.length)
        if(length > 0):
            for location in self.locationList:
                location.score.perCombinedScores = location.score.numCombinedScores/length
    
        self.locationList.sort(key=lambda x: x.score.toValue(), reverse=True)
           
        # for location in self.locationList[0:5]:
            # print location.printInfo()
            
    def workWithArticleItems(self):
        self.countriesInArticle = {}
        self.listOfNNP = []
        self.length = 0
        if(self.articleItems != None):
            print "#"
            
            headline = self.articleItems["headline"][0]
            subline = self.articleItems["subline"]
            if(len(subline) > 0): subline = subline[0]
            else: subline = ""
            date = ""
            url = self.articleItems["url"]
            source = self.articleItems["source"]

            for each in self.articleItems["date"]:
                if "Posted" in each:
                    date = each
                elif "Updated" in each:
                    date = each
            
            c = conn.cursor()
            currResults = []
            
            t = (url,)
            c.execute('SELECT url,date FROM articles WHERE url=?', t)
            currResults = c.fetchone()

            if not currResults or date != currResults[-1]:
        
                #separate words
                headlineWorker = headline.replace('-', ' ')
                sublineWorker = subline.replace('-', ' ')
                
                #replace all forbiddenNames with blanks
                for word in self.forbiddenNames:
                    headlineWorker = headlineWorker.replace(word, '')
                    sublineWorker = sublineWorker.replace(word, '')
                
                #headline
                tokens = word_tokenize(headlineWorker)
                partsOfSpeech = pos_tag(tokens)
                
                self.findCountriesInPOS(partsOfSpeech, isHeadline = True)

                #subline
                tokens = word_tokenize(sublineWorker)
                partsOfSpeech = pos_tag(tokens)
                
                self.findCountriesInPOS(partsOfSpeech, isSubline = True)
                   
                sentenceNum = len(self.articleItems["text"])
                sentenceCount = 0   
                for sentence in self.articleItems["text"]:
                    sentence = sentence.replace('-', ' ')
                    for word in self.forbiddenNames:
                        sentence = sentence.replace(word, '')
                        
                    tokens = word_tokenize(sentence)
                    partsOfSpeech = pos_tag(tokens)
                    
                    self.findCountriesInPOS(partsOfSpeech, sentence = sentenceCount, sentenceNum = sentenceNum)
                    sentenceCount += 1
                    
                # for each in self.countriesInArticle: print each + " " + self.countriesInArticle[each].printInfo()
                
                self.findCitiesInCountries()
                
                returnList = []
                
                firstFlag = False
                for item in self.locationList:
                    if(not firstFlag): firstFlag = True
                    else:
                        if(item.score.toValue() > (self.locationList[0].score.toValue()/2.)):
                            returnList.append(item.location)
                
                
                article = self.Article(headline, subline, date, url, source, self.locationList[0], returnList)

                # print type(self.locationList[0])
                
                # print headline+ " " +subline+ " " +date+ " " +url+ " " +source+ " " +self.locationList[0]+ " " +returnList
                
                t = (headline,subline,date,url,source,str(self.locationList[0].location),(str(self.locationList[0].city) + " " + str(self.locationList[0].country)),str(returnList),)
                c.execute('INSERT or REPLACE into articles(headline, subline, date, url, source, primaryLocation, locationName, secondaryLocations) values(?,?,?,?,?,?,?,?)', t)
                

            else: return 
        else: return 

def generateGoodLinksCBC(url = 'http://www.cbc.ca/news/world', xPath = '//body//div[@class="wrap8 landing-primary"]//a/@href'):
    linkList = generalScrape(url, xPath, True)
    cleanLinkList = []
    
    for link in linkList:
        if ("http://" not in link and "#" not in link and "?" not in link):
            cleanLinkList.append("http://www.cbc.ca" + link)
            print link
    
    
    # for link in [cleanLinkList[13]]:             
    for link in cleanLinkList:             
        articleItems = getItemsFromCBCArticle(link)
        npc = NewsPageClassifier(articleItems)
        npc.workWithArticleItems()
        
    conn.commit()