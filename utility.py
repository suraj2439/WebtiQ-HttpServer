import platform
import gzip
import shutil
from typing import Match
import zlib
import brotli
import lzw3
import mimetypes
import os
import time
import math
from datetime import datetime


def handleEncodingPriority(val):
    if val == "":
        return "identity"
    availableEncodings = ["br","compress", "deflate", "gzip", "x-gzip"]
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
        elif tmpArr[0] in availableEncodings:
            processedEncodings[tmpArr[0]] = priority
    
    result = max(processedEncodings, key = processedEncodings.get)
    if processedEncodings[result] > 0:
        return result
    return None

def stripList(listObj):
    for i in range (len(listObj)):
        listObj[i] = listObj[i].strip()
    return listObj

def getExtension(mimeType):
    return mimetypes.guess_all_extensions(mimeType)

def handleAcceptContentPriority(filePath, val):
    acceptList = stripList(val.split(","))
    acceptDict = {}
    fileExt = "." + filePath.rsplit(".", 1)[1]
    filePath = filePath.rsplit(".", 1)[0]
    for accept in acceptList:
        tmpArr = accept.split(";", 1)
        if accept == "*/*":
            if(len(tmpArr) == 1):
                acceptDict[fileExt] = 1
            else:
                acceptDict[fileExt] = tmpArr[1]

        extensionArr = getExtension(tmpArr[0])
        for extension in extensionArr:
            tmpPath = filePath + extension
            if os.path.isfile(tmpPath):
                if(len(tmpArr) == 1):
                    acceptDict[extension] = 1
                else:
                    acceptDict[extension] = tmpArr[1]
                break

    if len(acceptDict) == 0:
        return None 
    return max(acceptDict, key = acceptDict.get)

def parseCookies(cookies):
    if not cookies:
        return {}
    cookies = cookies.split(";")
    result = {}
    for cookie in cookies:
        [name, value] = stripList(cookie.split("="))
        result[name] = value
    return result

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

    body = respDict.get("body", None)
    result = firstLine
    for key in respDict["headers"]:
        result += key + ": " + str(respDict["headers"][key]) + "\r\n"
    result += "\r\n"    
    if body:
        result = result.encode() + body
    else:
        result = result.encode()
    return result


def deleteData(path, isFile):
    if isFile:
        os.remove(path)
    else:
        shutil.rmtree(path, ignore_errors=True)


# def generateResponse(respDict):
#     entityHeaders = ["Allow", "Content-Encoding", "Content-Language", "Content-Length", "Content-Location", 
#                     "Content-MD5", "Content-Range", "Content-Type", "Expires", "Last-Modified"]
#     respDict["headers"]["Transfer-Encoding"] = "gzip"

#     firstLine = respDict["Version"] + " " + respDict["Status-Code"] + " " + respDict["Status-Phrase"] + "\r\n"

#     body = respDict.get("body", None)
#     result = firstLine
#     entityData = ""
#     for key in respDict["headers"]:
#         if key not in entityHeaders:
#             result += key + ": " + str(respDict["headers"][key]) + "\r\n"
#         else:
#             entityData += key + ": " + str(respDict["headers"][key]) + "\r\n"
#     entityData += "\r\n"
#     #result += "\r\n"   
    
#     if body:
#         entityData = entityData.encode() + body
#     else:
#         entityData = entityData.encode()
#     entityData = gzip.compress(entityData)

#     return result.encode() + entityData


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

def logTime():
    timezone = -time.timezone/3600
    # extract hours
    timezoneHour = math.floor(timezone)
    # extract minutes
    timezoneMin = int((timezone-timezoneHour)*60)
    date = datetime.now()
    monthDict = { 1:"Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"} 
    date = "%02d/%s/%04d:%02d:%02d:%02d +" % (date.day, monthDict[date.month], date.year, date.hour, date.minute, date.second)
    date+=str(timezoneHour)
    date+=str(timezoneMin)
    return date

def writeAccessLog(reqDict, respDict, clientAddr, logFilePath):
    logDict = {
        'laddr': clientAddr[0],
        'identity':'-',
        'userid':'-',
        'time': logTime(),
        'requestLine':'"-"',
        'statusCode':'-',
        'dataSize':0,
        'referer':'"-"',
        'userAgent':'"-"',
        'cookie':'"-"',
        'set-cookie':'"-"'
    }
    logDict["requestLine"] = "'" + reqDict["First-Line"] + "'"
    logDict["statusCode"] = respDict["Status-Code"]
    logDict["dataSize"] = respDict["headers"]["Content-Length"]
    logDict["referer"] = "'" + reqDict["headers"].get("Referer", "-") + "'"
    logDict["userAgent"] = "'" + reqDict["headers"].get("User-Agent", "-") + "'"
    logDict["cookie"] = "'" + reqDict["headers"].get("Cookie", "-") + "'"
    logDict["set-cookie"] = "'" + respDict["headers"].get("Set-Cookie", "-") + "'"

    log = ""
    for logKey in logDict:
        log+=str(logDict[logKey]) + " "
    log += "\n"
    with open(logFilePath, "a") as fd:
        fd.write(log)
        fd.close()
    
def removeExpiredCookies(globalCookies):
    return globalCookies