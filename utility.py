import hashlib
import platform
import gzip
import random
import shutil
from typing import Match
import zlib
import brotli
import mimetypes
import os
import time
import math
from datetime import datetime
from config import *

def stripList(listObj):
    for i in range (len(listObj)):
        listObj[i] = listObj[i].strip()
    return listObj

def handleEncodingPriority(val):
    if val == "":
        return "identity"
    availableEncodings = ["br", "deflate", "gzip", "x-gzip"]
    processedEncodings = {}

    accValues = stripList(val.split(","))
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



def getExtension(mimeType):
    return mimetypes.guess_all_extensions(mimeType)

def handleAcceptContentPriority(filePath, val):
    acceptList = stripList(val.split(","))
    acceptDict = {}
    fileExt = ""
    if len(filePath.rsplit(".", 1)) == 2:
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

def handleAcceptCharsetPriority(acceptCharset):
    availableEncodings = ["utf-8", "ISO-8859-1"]
    processedEncodings = {}

    accValues = stripList(acceptCharset.split(","))
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

# def generateResponse(respDict):
#     firstLine = respDict["Version"] + " " + respDict["Status-Code"] + " " + respDict["Status-Phrase"] + "\r\n"

#     body = respDict.get("body", None)
#     result = firstLine
#     for key in respDict["headers"]:
#         result += key + ": " + str(respDict["headers"][key]) + "\r\n"
#     result += "\r\n"    
#     if body:
#         result = result.encode() + body
#     else:
#         result = result.encode()
#     return result


def generateResponse(respDict):
    if not respDict["isError"] and respDict["headers"].get("Content-Length"):
        del respDict["headers"]["Content-Length"]
    firstLine = respDict["Version"] + " " + respDict["Status-Code"] + " " + respDict["Status-Phrase"] + "\r\n"

    body = respDict.get("body", None)
    if body and not respDict["isError"]:
        body = chunkGenerator(body)
        respDict["headers"]["Transfer-Encoding"] = "chunked"
    elif not respDict["headers"].get("Content-Length"):
        respDict["headers"]["Content-Length"] = "0"
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


# FOR TRANSFER ENCODING
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
    
def removeExpiredCookies(globalCookiesDict):
    expiredCookies = []
    for key in globalCookiesDict.keys():
        currentTime = math.floor(time.time())
        if globalCookiesDict[key]["expireTime"] < currentTime:
            expiredCookies.append(key)
    
    for key in expiredCookies:
        del globalCookiesDict[key]

    return globalCookiesDict

def handleCookie(cookieHeader, clientAddr, method, globalCookieDict):
    cookiesDict = parseCookies(cookieHeader)
    cookie = cookiesDict.get(MY_COOKIE_NAME, None)
    newCookie = None
    if not cookie:
        tmpStr = str(time.time()) + str(random.randint(10000, 99999)) 
        newCookie = hashlib.md5(tmpStr.encode()).hexdigest()
        globalCookieDict[newCookie] = {
            "host": clientAddr,
            "expireTime": math.floor(time.time()) + COOKIE_EXPIRE_TIME,
            "tot_get_requests": 0,
            "tot_head_requests": 0,
            "tot_post_requests": 0,
            "tot_put_requests": 0,
            "tot_delete_requests": 0
        }
        globalCookieDict[newCookie]["tot_" + method.lower() + "_requests"] = 1

    else:
        # check for expire, check if available
        globalCookieDict = removeExpiredCookies(globalCookieDict)
        checkCookie = globalCookieDict.get(cookie, None)
        if not checkCookie:
            # set cookie
            tmpStr = str(time.time()) + str(random.randint(10000, 99999)) 
            newCookie = hashlib.md5(tmpStr.encode()).hexdigest()
            globalCookieDict[newCookie] = {
                "host": clientAddr,
                "expireTime": math.floor(time.time()) + COOKIE_EXPIRE_TIME,
                "tot_get_requests": 0,
                "tot_head_requests": 0,
                "tot_post_requests": 0,
                "tot_put_requests": 0,
                "tot_delete_requests": 0
            }
            globalCookieDict[newCookie]["tot_" + method.lower() + "_requests"] = 1
        else:
            globalCookieDict[cookie]["tot_" + method.lower() + "_requests"] += 1
    
    return newCookie, globalCookieDict

def chunkGenerator(data):
    arr = []
    #arr = (data[0+i : 5+i] for i in range(0, len(data), 5))
    tot_len = len(data)
    prev = 0
    while(tot_len > 0):
        val = random.randint(10,30)
        if prev + val > len(data):
            arr.append(data[prev :])
        else:
            arr.append(data[prev : prev + val])
        prev = prev + val
        tot_len -= val

    result = b""
    for chunk in arr:
        result += b"%x\r\n" % len(chunk)
        result += (chunk + b"\r\n")
    result += b"0\r\n\r\n"
    return result


def isError(data, errorType):
    if(errorType == "max_simult_conn_exceed"):
        if(data < MAX_CONN):
            return False
        return True
    elif errorType == "uri_too_long":
        if data < MAX_URI_LENGTH:
            return False
        return True
    elif errorType == "method_not_implemented":
        if(data in SUPPORTED_METHODS):
            return False
        return True
    elif errorType == "header_too_long":
        if(data < MAX_HEADER_LENGTH):
            return False
        return True
    elif errorType == "version_not_supported":
        http_version = data.split("/", 1)
        if(len(http_version) == 2 and http_version[0] == "HTTP" and (http_version[1].lstrip())[0] == "1"):
            return False
        return True
    elif errorType == "host_not_available":
        if("Host" not in data):
            return True
        return False



# seperate request header, body, method, uri, data etc...
def parse_request(request):
    # seperate header and body
    request = request.split("\r\n\r\n", 1)
    header = request[0]
    body = ""
    if(len(request) > 1):
        body = request[1]

    header_lines = header.split("\r\n")
    reqLine = header_lines[0].strip()
    first_line = header_lines[0].split()
    if(len(first_line) != 3):
        # TODO crosscheck error code
        return {"isError": True, "method": "", "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "request format is not supported."}
    
    [req_method, req_uri, http_version] = first_line

    if(isError(len(req_uri), "uri_too_long")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 414, "Status-Phrase": "URI Too Long", "Msg": "Requested uri is too long to handle to server."}
    
    if(isError(req_method, "method_not_implemented")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 405, "Status-Phrase": "Method Not Implemented", "Msg": "Requested method is not implemented at server side or server could not support requested method."}
    
    if(isError(http_version, "version_not_supported")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 505, "Status-Phrase": "HTTP Version Not Supported", "Msg": "HTTP Version Not Supported, either requested wrong version format or requested http version is not supported by server."}
    
    headers = header_lines[1:]
    header_dict = {}
    for single_header in headers:
        single_header = single_header.split(":", 1)
        if len(single_header) != 2:
            # TODO cross check response code
            return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Header format is incorrect."}
        if(isError(len(single_header[1]), "header_too_long")):
            return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 431, "Status-Phrase": "Request header fields too large", "Msg": "Requested header field is too large to handle to server."}
        # TODO check for supported
        single_header[0] = single_header[0].strip()
        single_header[1] = single_header[1].strip()
        
        header_dict[single_header[0]] = single_header[1]
    if(isError(header_dict, "host_not_available")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Header format is incorrect."}

    return {"isError" : False, "method": req_method, "First-Line": reqLine, "headers" : header_dict, "uri" : req_uri, "method" : req_method, "Version" : http_version, "body" : body}


def receiveSocketData(connection, timeout):
    partialReq = b""
    connection.settimeout(timeout)
    count = 0
    while True:
        try:
            partialReq += connection.recv(8096)
            if count > TOT_COUNT:
                connection.close()
                return None
            if(not partialReq):
                time.sleep(timeout/TOT_COUNT)
                count += 1
        except Exception as e:
            connection.close()
            return None
        if "\r\n\r\n".encode() in partialReq:
            break
    partialReqDict = parse_request(partialReq.decode("ISO-8859-1"))
    if partialReqDict["isError"]:
        return partialReq #headers
    contentLength = int(partialReqDict["headers"].get("Content-Length", 0)) 
    contentLength -= len(partialReq.split("\r\n\r\n".encode(), 1)[1])
    body = b""

    while len(body) < contentLength:
        # TODO handle if not received
        body += connection.recv(8096)
    return (partialReq + body).strip()

def generate_error_response(errorCode, errorPhrase, errorMsg):
    resp = """
<!DOCTYPE html>
<html>
    <head>
        <title>{} {}</title>
    </head>
    <body>
        <h1>{}</h1>
        <p1>{}</p>
    </body>
</html>

    """.format(errorCode, errorPhrase, errorPhrase, errorMsg)
    return resp

def gen_503_response():
    response =  "HTTP/1.1 503 Service Unavailable\r\nDate: Mon, 08 Nov 2021 20:10:35 GMT\r\nServer: MY-HTTP-SERVER/1.1\r\nConnection: close\r\nContent-Length: 195\r\nContent-Type: text/html\r\n\r\n"
    response += generate_error_response(503, "Service Unavailable", "Server temporarily not available, please try again later.")
    return response

#print(chunkGenerator(b"SURAJYERKALLKJLKJLKJFDOIJWEOIJFLKJFLKJDLFKJSDL"))

# TODO 
def generateBoundary():
    return "3d6b6a416f9b5"


