import sqlite3
conn = sqlite3.connect('locations.db')

c = conn.cursor()
c.execute('''CREATE TABLE `locations` (
	`country`	text,
	`province`	text,
	`city`	text,
	`location`	text,
	`population`	real,
	PRIMARY KEY(location)
);''')

c.execute('''CREATE INDEX countryIndex ON locations(country);''')

#Load Cities
f = open('Cities.txt', 'r')
cityList = {}
i = 0
t = []
for line in f:
    city = line.split(',')

    cityCode = city[3]
    try:
        cityCode = unicode(city[3], "UTF-8")
    
        t = (city[1], city[2], cityCode, city[0], city[4])
        c.execute("INSERT or IGNORE INTO locations VALUES (?,?,?,?,?)", t)
    except: i+=1
    
conn.commit()
print str(i) + " elements were skipped due to unicode issues"
f.close()
    
conn.close()