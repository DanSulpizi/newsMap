import sqlite3
import geohasher
conn = sqlite3.connect('locations.db')

articleLoc = {}

t = ()
c = conn.cursor()
c.execute('SELECT primaryLocation,headline,subline,date,url,source,locationName,secondaryLocations,timestamp FROM articles WHERE (timestamp >= date("now", "-7 days")) ORDER BY datetime(timestamp) DESC limit 100', t)

for each in c.fetchall():
    latlong = geohasher.decode(each[0])
    # print each
    if each[0] in articleLoc:
        articleLoc[each[0]].append({
            'headline': each[1],
            'subline': each[2],
            'date': each[3],
            'url': each[4],
            'source': each[5],
            'lat': latlong[0],
            'long': latlong[1],
            'locationName': each[6],
            'secondaryLocations': each[7],
        })
    else:
        articleLoc[each[0]] = [{
            'headline': each[1],
            'subline': each[2],
            'date': each[3],
            'url': each[4],
            'source': each[5],
            'lat': latlong[0],
            'long': latlong[1],
            'locationName': each[6],
            'secondaryLocations': each[7],
        }]
        
conn.close()

import json
with open('webpage/data/data.txt', 'w') as outfile:
    json.dump(articleLoc, outfile)