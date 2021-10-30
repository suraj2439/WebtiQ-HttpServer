import platform
import gzip
import zlib
import brotli
import lzw3



def handleEncodingPriority(val):
    if val == "":
        return "identity"
    availableEncodings = ["br","compress", "deflate", "gzip", "exi", "pack200-gzip", 
        "x-compress","x-gzip", "zstd"]
    processedEncodings = {}

    accValues = val.split(",")
    for value in accValues:
        tmpArr = value.split(";", 1)
        if(len(tmpArr) == 2):
            priority = float((tmpArr[1].split("="))[1].strip())
        else:
            priority = 1.0
        if(tmpArr[0] == "*"):
            for enc in availableEncodings:
                if enc not in processedEncodings:
                    processedEncodings[enc] = priority
        else:
            processedEncodings[tmpArr[0]] = priority
    
    result = max(processedEncodings, key = processedEncodings.get)
    if processedEncodings[result] > 0:
        return result
    return None


def handleAcceptContentPriority(val):
    pass

def serverInfo():
    name = "MY-HTTP-SERVER"
    version = "1.1"
    operatingSys = platform.platform()
    return name + "/" + version + " " + operatingSys

def toRFC_Date(date):
    weekdayDict = { 0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    monthDict = { 1:"Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"} 
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekdayDict[date.weekday()], date.day, monthDict[date.month], date.year, date.hour, date.minute, date.second)

def generateResponse(respDict):
    firstLine = respDict["Version"] + " " + respDict["Status-Code"] + " " + respDict["Status-Phrase"] + "\r\n"

    body = respDict["body"]
    result = firstLine
    for key in respDict["headers"]:
        result += key + ": " + str(respDict["headers"][key]) + "\r\n"
    result += "\r\n"    
    result = result.encode() + body
    return result

def encodeData(data, encodeFormat):
    if encodeFormat == "gzip" or encodeFormat == "x-gzip":
        return gzip.compress(data)
    elif encodeFormat == "compress":
        return lzw3.compress(data)
    elif encodeFormat == "deflate":
        return zlib.compress(data)
    elif encodeFormat == "br":
        return brotli.compress(data)
    return data
    