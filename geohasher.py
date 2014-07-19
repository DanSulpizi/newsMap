def base2to32(strNum):
    n = 5
    list = [strNum[i:i+n] for i in range(0, len(strNum), n)]
    
    out = ""
    num_rep={
        "00000": '0',
        "00001": '1',
        "00010": '2',
        "00011": '3',
        "00100": '4',
        "00101": '5',
        "00110": '6',
        "00111": '7',
        "01000": '8',
        "01001": '9',
        "01010": 'b',
        "01011": 'c',
        "01100": 'd',
        "01101": 'e',
        "01110": 'f',
        "01111": 'g',
        "10000": 'h',
        "10001": 'j',
        "10010": 'k',
        "10011": 'm',
        "10100": 'n',
        "10101": 'p',
        "10110": 'q',
        "10111": 'r',
        "11000": 's',
        "11001": 't',
        "11010": 'u',
        "11011": 'v',
        "11100": 'w',
        "11101": 'x',
        "11110": 'y',
        "11111": 'z',
    }
    
    for each in list:
        while(len(each) < 5): each+="0"
        out += num_rep[each]
        
    return out
    
def base32to2(strNum):
    out = ""
    num_rep={
        '0': "00000",
        '1': "00001",
        '2': "00010",
        '3': "00011",
        '4': "00100",
        '5': "00101",
        '6': "00110",
        '7': "00111",
        '8': "01000",
        '9': "01001",
        'b': "01010",
        'c': "01011",
        'd': "01100",
        'e': "01101",
        'f': "01110",
        'g': "01111",
        'h': "10000",
        'j': "10001",
        'k': "10010",
        'm': "10011",
        'n': "10100",
        'p': "10101",
        'q': "10110",
        'r': "10111",
        's': "11000",
        't': "11001",
        'u': "11010",
        'v': "11011",
        'w': "11100",
        'x': "11101",
        'y': "11110",
        'z': "11111",
    }
    for letter in strNum:
        out += num_rep[letter]
            
    return out

def hash(lat, long, precision = 100):
    out = ""
    latMax = 90.
    latMin = -90.
    longMax = 180.
    longMin = -180.
    
    i = 0
    
    while(i < precision/2):
        if(i%2 == 0):
            longMid = (longMax+longMin)/(2.)
            # print "LONG:  " + str(longMin) + " " + str(longMid) + " " + str(longMax)
            if long >= longMid:
                longMin = longMid
                out += "1"
            else:
                longMax = longMid
                out += "0"
        else:
            latMid = (latMax+latMin)/2
            # print "LAT :  " + str(latMin) + " " + str(latMid) + " " + str(latMax)
            if lat >= latMid:
                latMin = latMid
                out += "1"
            else:
                latMax = latMid
                out += "0"
        
        
        i += 1
    return base2to32(out)

def decode(geohash, longMin = -180., longMax = 180., latMin = -90., latMax = 90.):
    bitstring = base32to2(geohash)
    
    i = 0
    for char in bitstring:
        if(i%2 == 0):
            longMid = (longMax + longMin)/2.
            if char == '1':
                longMin = longMid
            else:
                longMax = longMid
        else:
            latMid = (latMax + latMin)/2.
            if char == '1':
                latMin = latMid
            else:
                latMax = latMid
        i+=1
        
    return ((latMax + latMin)/2.,(longMax + longMin)/2.)

if __name__ == "__main__":
    print decode(hash(42.605, -5.6))
    print (hash(12.6059, -50.6241, 75))
    print decode(hash(12.6059, -50.6241, 75))
    print decode(hash(39.92890, 116.3883))
    print hash(33.7000,130.4167)
    
    print hash(55.873945, -4.276478)
    print decode(hash(52.037478, -3.952382))
    
    print decode('1110001011000011100110001')
    print decode('0100111110011110000000000')

    print hash(37.180651, -119.674172)
    print hash(40.697074, -74.007964)