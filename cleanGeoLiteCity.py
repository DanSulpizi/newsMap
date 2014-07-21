import geohasher

def iround(x):
    """iround(number) -> integer
    Round a number to the nearest integer."""
    y = round(x) - .5
    return int(y) + (y > 0)

f = open('glds00g15', 'r')

popDen = []

#lower left corner of data set is at -58, -180

latMin = -58
latMax = 85
resolution = 4

passedFirst = False
for line in f:
    if passedFirst == True:
        popDenRow = line.split()
        for x in popDenRow:
            x = float(x)
        popDen.append(popDenRow)
    else: passedFirst = True
    
f.close()

f = open('GeoLiteCity-Location.csv', 'r')
o = open('Cities.txt', 'w')
o2 = open('Regions.txt', 'w')
o.close()
o2.close()
o = open('Cities.txt', 'a')
o2 = open('Regions.txt', 'a')

citySet = set()

i = 0

for line in f:
    if i >= 2:
        city = line.split(',')
        countryCode = city[1].replace('"', '')
        regionCode  = city[2].replace('"', '')
        cityCode    = city[3].replace('"', '')
        lat = float(city[5])
        long = float(city[6])
        location = geohasher.hash(lat,long)
        density = 0
        
        # if cityCode == "Beijing": print str(lat) + " " + str(long)
        
        if cityCode != "":
            if(lat > latMin and lat < latMax):
                latPos = (latMax-iround(lat))*resolution
                longPos = (min((iround(long)+180)*resolution,len(popDen[0])-1))
                
                # if(location == 'spyketv4n0'):
                    # print latPos
                    # print longPos
                density = float(popDen[latPos][longPos])
                if density < 0: density = -1
        
        s = cityCode+location
        if not s in citySet:
            citySet.add(s)
            if(cityCode != "" or regionCode == ""):
                o.write(location + ',' + countryCode + ',' + regionCode + ',' + cityCode + ',' + str(density) + "\n")
            else: o2.write(location + ',' + countryCode + ',' + regionCode + ',' + cityCode + ',' + str(density) + "\n")
    i+=1
        
o.close()
o2.close()
f.close()