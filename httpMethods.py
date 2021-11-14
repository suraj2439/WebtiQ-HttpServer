
import gzip
import mimetypes
import sys
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import hashlib
import time
import os
import json
import lzw3
import zlib
import utility
import brotli

from sys import maxsize
from _thread import *
from threading import Lock
from config import *

TIME_DIFF = 19800
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
POST_FILE_PATH = "/home/suraj/Documents/study/TY/CN/Project/post.txt"
MAX_DELETE_SIZE = 100

def get_or_head(reqDict, method):
    responseDict = {}
    body = ""
    headers = reqDict.get("headers")
    uri = reqDict.get("uri")
    path = urlparse(uri).path
    if path == "/":
        path = "/index.html"
    path = DEFAULT_DIR_PATH + path
    userAgent = headers.get("User-Agent", "")
    if "Windows" in userAgent:
        newPath = DEFAULT_DIR_PATH + "/windows" + urlparse(uri).path
        if os.path.isfile(newPath):
            path = newPath

    accept = headers.get("Accept", "*/*")
    fileExtension = utility.handleAcceptContentPriority(path, accept)
    acceptCharset = headers.get("Accept-Charset", "utf-8")
    responseCharset = utility.handleAcceptCharsetPriority(acceptCharset)

    acceptEncoding = headers.get("Accept-Encoding", "")
    contentEncoding = utility.handleEncodingPriority(acceptEncoding)
    if contentEncoding == None:
        return {"isError": True, "Status-Code": 406, "Status-Phrase": "Not Acceptable", "Msg": "Error in content-encoding header field or server could not handle content-encoding header field." }
    
    if fileExtension:
        path = path.rsplit(".", 1)[0] + fileExtension

    if not os.path.isfile(path):
        utility.writeErrorLog("debug", str(os.getpid()), "-", path + " : 404 Not Found")
        return {"isError": True, "Status-Code": 404, "Status-Phrase": "Not Found", "Msg": "Could not found requested resource." }
    else:
        if not os.access(path, os.R_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to read the file." }
        contentType = mimetypes.guess_type(path)[0]
        if contentType == None:
            contentType = "text/plain"
        if "text" in contentType:
            fd = open(path, 'r')
            fileData = fd.read()
            fd.close()
        else:
            fd = open(path, 'rb')
            fileData = fd.read()
            fd.close()

    ifMatch = headers.get('If-Match',"*")
    ifNoneMatch = headers.get('If-None-Match',"")
    
    ifMatchArr = ifMatch.split(",")
    ifNoneMatchArr = ifNoneMatch.split(",")
    for i in range (len(ifMatchArr)):
        ifMatchArr[i] = ifMatchArr[i].strip()
    for i in range (len(ifNoneMatchArr)):
        ifNoneMatchArr[i] = ifNoneMatchArr[i].strip()
    
    # generate ETag
    ETag = '"' + hashlib.md5((str(os.path.getmtime(path)).encode())).hexdigest() + '"'
    if "If-Match" in headers.keys():
        if ETag not in ifMatchArr and ifMatchArr[0] != "*":
            return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not match given ETag." }
    elif "If-Unmodified-Since" in headers.keys():
        date = datetime.strptime(headers["If-Unmodified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader < lastModifiedTime:
            return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet If-Unmodified-Since header requirements." }
    
    statusCode = 200
    statusPhrase = "OK"
    flag = True
    if "If-None-Match" in headers.keys():
        if "*" in ifNoneMatchArr or ETag in ifNoneMatchArr:
            statusCode = 304
            statusPhrase = "Not Modified"
            flag = False
            #return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
    elif "If-Modified-Since" in headers.keys():
        date = datetime.strptime(headers["If-Modified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader >= lastModifiedTime:
            statusCode = 304
            statusPhrase = "Not Modified"
            flag = False
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }

    if flag and "Range" in headers.keys() and (headers["Range"].split("="))[0] == "bytes":
        dataAvailable = True
        # check for conditions on range header
        if "If-Range" in headers.keys():
            # If-Range header is in ETag format
            if headers["If-Range"][0] == '"':
                if headers["If-Range"] != ETag:
                    dataAvailable = False
            # If-Range header is in last-modified format
            else:
                date = datetime.strptime(headers["If-Range"] , "%a, %d %b %Y %H:%M:%S GMT")
                timeFromHeader = time.mktime(date.timetuple())
                lastModifiedTime = os.path.getmtime(path) - TIME_DIFF

                if timeFromHeader < lastModifiedTime:
                    dataAvailable = False
        
        if dataAvailable:
            rangesList = utility.stripList(headers["Range"].split('=')[1].split(','))
            if len(rangesList) > 1:
                for i in range (len(rangesList)):
                    r_range = rangesList[i]
                    if r_range[0] == "-":
                        startPos = 0
                        endPos = r_range[1:]
                    # range format = <value>-
                    elif r_range[-1] == "-":
                        startPos = r_range[:-1]
                        endPos = maxsize
                    # range format = <value>-<value>
                    else:
                        [startPos, endPos] = r_range.split("-")
                    
                    rangesList[i] = (int(startPos), int(endPos))

                boundary = utility.generateBoundary()
                result = b""
                for pair in rangesList:
                    result += ("--" + boundary + "\r\n").encode(responseCharset)
                    result += ("Content-Type: " + contentType + "; charset=" + responseCharset + "\r\n").encode(responseCharset)
                    result += (("Content-Range: bytes" + str(pair[0]) + "-" + str(pair[1]) + "/" + str(len(fileData)) + "\r\n")).encode(responseCharset)
                    result += ("Content-Encoding: " + contentEncoding + "\r\n\r\n").encode(responseCharset)
                    result += (fileData[int(startPos) : int(endPos)+1]).encode(responseCharset) + "\r\n".encode(responseCharset)
                result += ("--" + boundary + "--" + "\r\n").encode(responseCharset)

                body = result

                responseDict["isError"] = False
                responseDict["Status-Code"] = "206"
                responseDict["Status-Phrase"] = "Partial Content"
                responseDict["headers"] = {}
                responseDict["headers"]["Content-Length"] = len(body)
                responseDict["headers"]["Last-Modified"] = utility.toRFC_Date(datetime.fromtimestamp(int(os.path.getmtime(path)) - TIME_DIFF))
                responseDict["headers"]["ETag"] = ETag
                responseDict["headers"]["Accept-Ranges"] = "bytes"
                responseDict["headers"]["Content-Type"] = "multipart/byteranges; boundary="+boundary
                if(method == "GET"):
                    responseDict["body"] = body
                    responseDict["headers"]["Content-MD5"] = hashlib.md5(responseDict["body"]).hexdigest()
                return responseDict

            else:
                r_range = rangesList[0]
                # range format = -<value>
                if r_range[0] == "-":
                    startPos = 0
                    endPos = r_range[1:]
                # range format = <value>-
                elif r_range[-1] == "-":
                    startPos = r_range[:-1]
                    endPos = maxsize
                # range format = <value>-<value>
                else:
                    [startPos, endPos] = r_range.split("-")
                
                if int(startPos) <= int(endPos):
                    responseDict["isError"] = False
                    responseDict["Status-Code"] = "206"
                    responseDict["Status-Phrase"] = "Partial Content"
                    responseDict["headers"] = {}
                    responseDict["headers"]["Content-Range"] = "bytes " + startPos + "-" + endPos + "/" + str(len(fileData))
                    responseDict["headers"]["Content-Encoding"] = contentEncoding
                    if "text" in contentType:
                        responseDict["headers"]["Content-Type"] = contentType + "; charset=" + responseCharset
                    else:
                        responseDict["headers"]["Content-Type"] = contentType
                    body = fileData[int(startPos) : int(endPos)+1]
                    if "text" in contentType:
                        body = body.encode(responseCharset)
                    body = utility.encodeData(body, contentEncoding)
                    responseDict["headers"]["Content-Length"] = len(body)
                    
                    if(method == "GET"):
                        responseDict["body"] = body
                        responseDict["headers"]["Content-MD5"] = hashlib.md5(responseDict["body"]).hexdigest()
                    return responseDict
    responseDict["isError"] = False
    responseDict["Status-Code"] = str(statusCode)
    responseDict["Status-Phrase"] = statusPhrase
    responseDict["headers"] = {}
    responseDict["headers"]["Last-Modified"] = utility.toRFC_Date(datetime.fromtimestamp(int(os.path.getmtime(path)) - TIME_DIFF))
    responseDict["headers"]["ETag"] = ETag
    responseDict["headers"]["Accept-Ranges"] = "bytes"
    if "text" in contentType:
        fileData = fileData.encode(responseCharset)
    body = utility.encodeData(fileData, contentEncoding)
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    responseDict["headers"]["Content-Length"] = 0
    if flag:
        responseDict["headers"]["Content-Length"] = len(body)
        responseDict["headers"]["Content-Encoding"] = contentEncoding
        if "text" in contentType:
            responseDict["headers"]["Content-Type"] = contentType + "; charset=" + responseCharset
        else:
            responseDict["headers"]["Content-Type"] = contentType
        
    if(method == "GET" and flag):
        responseDict["body"] = body
        responseDict["headers"]["Content-MD5"] = hashlib.md5(responseDict["body"]).hexdigest()

    return responseDict

def post(reqDict):
    responseDict = {}
    headers = reqDict.get("headers")
    uri = reqDict.get("uri")
    path = urlparse(uri).path
    if path == "/":
        path = "/index.html"
    path = DEFAULT_DIR_PATH + path

    body = reqDict.get("body")
    contentEncoding = headers.get("Content-Encoding", "")
    contentType = headers.get("Content-Type", "text/plain")

    contentEncoding.split(",").reverse()

    if('Content-MD5' in headers.keys()):
        checksum = hashlib.md5(body.encode("ISO-8859-1")).hexdigest()
        if(checksum != headers["Content-MD5"]):
            return {"isError": True, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Checksum error." }

    # decompress payload data
    for enc in contentEncoding:
        enc = enc.strip()
        if enc == "":
            body = body.decode()
        elif enc == "gzip":
            body = gzip.decompress(body)
        elif enc == "deflate":
            body = zlib.decompress(body)
        elif enc == "br":
            body = brotli.decompress(body)
        else:
            return {"isError": True, "Status-Code": 406, "Status-Phrase": "Not Acceptable", "Msg": "Given Content encoding is not supported in server side." }

    if not os.path.isfile(path):
        doesfileExist = False
        # folder/hi.png
        if not os.access(path.rsplit("/", 1)[0], os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
    else:
        doesfileExist = True
        if not os.access(path, os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
    
    ifMatch = headers.get('If-Match',"*")
    ifNoneMatch = headers.get('If-None-Match',"")
    
    ifMatchArr = ifMatch.split(",")
    ifNoneMatchArr = ifNoneMatch.split(",")
    for i in range (len(ifMatchArr)):
        ifMatchArr[i] = ifMatchArr[i].strip()
    for i in range (len(ifNoneMatchArr)):
        ifNoneMatchArr[i] = ifNoneMatchArr[i].strip()
    

    if doesfileExist:
        # generate ETag
        ETag = '"' + hashlib.md5((str(os.path.getmtime(path)).encode())).hexdigest() + '"'
        if "If-Match" in headers.keys():
            if ETag not in ifMatchArr and ifMatchArr[0] != "*":
                return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not match given ETag." }
        elif "If-Unmodified-Since" in headers.keys():
            date = datetime.strptime(headers["If-Unmodified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
            timeFromHeader = time.mktime(date.timetuple())
            lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
            if timeFromHeader < lastModifiedTime:
                return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet If-Unmodified-Since header requirements." }
        
    if "application/x-www-form-urlencoded" in contentType:
        postDataDict = parse_qs(body)
    elif "application/json" in contentType:
        postDataDict = json.loads(body)
    elif "multipart/form-data" in contentType:
        boundary = contentType.rsplit("=", 1)[1].strip()
        #print(body.split(boundary + "\r\n"))
        multipartArr = body.split("--" + boundary+ "\r\n")[1:]
        multipartArr[len(multipartArr)-1] = multipartArr[len(multipartArr)-1].rsplit("\r\n", 1)[0]
        for part in multipartArr:
            [headers, body] = part.split("\r\n\r\n")
            contentType = "text"
            if "\r\n" in headers:
                [headers, contentType] = headers.rsplit("\r\n", 1)
                contentType = contentType.split(":", 1)[1].strip()
            headers = headers.split(";")
            headers = utility.stripList(headers)

            #print(headers, contentType)
            
        return {"isError": True, "Status-Code": 415, "Status-Phrase": "Unsupported Media Type", "Msg": "Could not support given media type." }
        
    else:
        responseDict = {}
        if contentType.strip() in ["image/png", "image/jpg", "image/jpeg"]:
            fd = open(path, "wb")
            fd.write(body.encode("ISO-8859-1"))
            fd.close()
            responseDict["Status-Code"] = "201"
            responseDict["Status-Phrase"] = "Resourse Created"
        elif contentType.strip() in ["text/html", "text/plain"]:
            statusCode, statusPhrase = "204", "No Content"
            if not os.path.exists(path):
                statusCode = "201"
                statusPhrase = "Resource Created"
            fd = open(path, "a")
            fd.write(body)
            fd.close()
            responseDict["Status-Code"] = statusCode
            responseDict["Status-Phrase"] = statusPhrase
        else:
            return {"isError": True, "Status-Code": 415, "Status-Phrase": "Unsupported Media Type", "Msg": "Could not support given media type." }
        
        responseDict["isError"] = False
        responseDict["headers"] = {}
        responseDict["headers"]["Content-Location"] = path.split(DEFAULT_DIR_PATH)[1]
        responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
        if int(statusCode) == 303:
            responseDict["headers"]["Location"] = "http://localhost:" + str(SERVER_PORT) + "/postSuccess.html"
        responseDict["headers"]["Content-Length"] = 0
        return responseDict

    #postFileDesc = open(POST_FILE_PATH, "a")
    fd = open(path + "/StorePostData.json", "a")
    json.dump({utility.toRFC_Date(datetime.utcnow()): postDataDict}, fd, indent="\t")
    fd.close()

    responseDict = {}
    responseDict["isError"] = False
    responseDict["Status-Code"] = "303"
    responseDict["Status-Phrase"] = "See Other"
    responseDict["headers"] = {}
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    responseDict["headers"]["Location"] = "http://localhost:" + str(SERVER_PORT) + "/postSuccess.html"
    responseDict["headers"]["Content-Length"] = 0

    return responseDict

def put(reqDict):
    responseDict = {}
    headers = reqDict.get("headers")
    uri = reqDict.get("uri")
    path = urlparse(uri).path
    if path == "/":
        path = "/index.html"
    path = DEFAULT_DIR_PATH + path

    body = reqDict.get("body")
    contentEncoding = headers.get("Content-Encoding", "")
    contentType = headers.get("Content-Type", "text/plain")

    contentEncoding.split(",").reverse()
    # decompress payload data
    for enc in contentEncoding:
        enc = enc.strip()
        if enc == "":
            body = body.decode()
        elif enc == "gzip":
            body = gzip.decompress(body)
        elif enc == "compress":
            body= lzw3.decompress(body)
        elif enc == "deflate":
            body = zlib.decompress(body)
        elif enc == "br":
            body = brotli.decompress(body)
        else:
            return {"isError": True, "Status-Code": 406, "Status-Phrase": "Not Acceptable", "Msg": "Given Content encoding is not supported in server side." }

    if not os.path.isfile(path):
        doesFileExist = False
        statusCode = 201
        statusPhrase = "Resource Created"
        if not os.access(path.rsplit("/", 1)[0], os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
    else:
        doesFileExist = True
        statusCode = 204
        statusPhrase = "No Content"
        if not os.access(path, os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
        
    ifMatch = headers.get('If-Match',"*")
    ifNoneMatch = headers.get('If-None-Match',"")
    
    ifMatchArr = ifMatch.split(",")
    ifNoneMatchArr = ifNoneMatch.split(",")
    for i in range (len(ifMatchArr)):
        ifMatchArr[i] = ifMatchArr[i].strip()
    for i in range (len(ifNoneMatchArr)):
        ifNoneMatchArr[i] = ifNoneMatchArr[i].strip()
    
    if doesFileExist:
        # generate ETag
        ETag = '"' + hashlib.md5((str(os.path.getmtime(path)).encode())).hexdigest() + '"'
        if "If-Match" in headers.keys():
            if ETag not in ifMatchArr and ifMatchArr[0] != "*":
                return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not match given ETag." }
        elif "If-Unmodified-Since" in headers.keys():
            date = datetime.strptime(headers["If-Unmodified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
            timeFromHeader = time.mktime(date.timetuple())
            lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
            if timeFromHeader < lastModifiedTime:
                return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet If-Unmodified-Since header requirements." }
        
    if('Content-MD5' in headers.keys()):
        checksum = hashlib.md5(body).hexdigest()
        if(checksum != headers["Content-MD5"]):
            return {"isError": True, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Checksum error." }

    if "application/x-www-form-urlencoded" in contentType:
        postDataDict = parse_qs(body)
    elif "application/json" in contentType:
        postDataDict = json.loads(body)
    elif "multipart/form-data" in contentType:
        boundary = contentType.rsplit("=", 1)[1].strip()
        #print(body.split(boundary + "\r\n"))
        multipartArr = body.split("--" + boundary+ "\r\n")[1:]
        multipartArr[len(multipartArr)-1] = multipartArr[len(multipartArr)-1].rsplit("\r\n", 1)[0]
        for part in multipartArr:
            [headers, body] = part.split("\r\n\r\n")
            contentType = "text"
            if "\r\n" in headers:
                [headers, contentType] = headers.rsplit("\r\n", 1)
                contentType = contentType.split(":", 1)[1].strip()
            headers = headers.split(";")
            headers = utility.stripList(headers)

            #print(headers, contentType)
            
        return {"isError": True, "Status-Code": 415, "Status-Phrase": "Unsupported Media Type", "Msg": "Could not support given media type." }
        
    else:
        responseDict = {}
        if contentType.strip() in ["image/png", "image/jpg", "image/jpeg"]:
            fd = open(path, "wb")
            fd.write(body.encode("ISO-8859-1"))
            fd.close()
            responseDict["Status-Code"] = str(statusCode)
            responseDict["Status-Phrase"] = statusPhrase
        elif contentType.strip() in ["text/html", "text/plain"]:
            fd = open(path, "w")
            fd.write(body)
            fd.close()
            responseDict["Status-Code"] = str(statusCode)
            responseDict["Status-Phrase"] = statusPhrase
        else:
            return {"isError": True, "Status-Code": 415, "Status-Phrase": "Unsupported Media Type", "Msg": "Could not support given media type." }
        
        responseDict["isError"] = False
        responseDict["headers"] = {}
        responseDict["headers"]["Content-Location"] = path.split(DEFAULT_DIR_PATH)[1]
        responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
        responseDict["headers"]["Content-Length"] = 0
        return responseDict

    #postFileDesc = open(POST_FILE_PATH, "a")
    fd = open(path, "w")
    json.dump({utility.toRFC_Date(datetime.utcnow()): postDataDict}, fd, indent="\t")

    responseDict = {}
    responseDict["isError"] = False
    responseDict["Status-Code"] = str(statusCode)
    responseDict["Status-Phrase"] = statusPhrase
    responseDict["headers"] = {}
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    responseDict["headers"]["Content-Length"] = 0

    return responseDict


def delete(reqDict):
    responseDict = {}
    headers = reqDict.get("headers")
    uri = reqDict.get("uri")
    path = urlparse(uri).path
    if path == "/":
        path = "/index.html"
    path = DEFAULT_DIR_PATH + path

    if os.path.exists(path):
        if os.path.isfile(path):       
            ifMatch = headers.get('If-Match',"*")
            ifNoneMatch = headers.get('If-None-Match',"")
            
            ifMatchArr = ifMatch.split(",")
            ifNoneMatchArr = ifNoneMatch.split(",")
            for i in range (len(ifMatchArr)):
                ifMatchArr[i] = ifMatchArr[i].strip()
            for i in range (len(ifNoneMatchArr)):
                ifNoneMatchArr[i] = ifNoneMatchArr[i].strip()
            
            # generate ETag
            ETag = '"' + hashlib.md5((str(os.path.getmtime(path)).encode())).hexdigest() + '"'
            if "If-Match" in headers.keys():
                if ETag not in ifMatchArr and ifMatchArr[0] != "*":
                    return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not match given ETag." }
            elif "If-Unmodified-Since" in headers.keys():
                date = datetime.strptime(headers["If-Unmodified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
                timeFromHeader = time.mktime(date.timetuple())
                lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
                if timeFromHeader < lastModifiedTime:
                    return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet If-Unmodified-Since header requirements." }
            
            # delete file
            if not os.access(path, os.W_OK):
                return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission delete this file." }
            size = os.path.getsize(path) 
            if size > MAX_DELETE_SIZE:
                statusCode = 202
                statusPhrase = "Accepted"
                start_new_thread(utility.deleteData, (path, True))
            else:
                statusCode = 204
                statusPhrase = "No Content"
                os.remove(path)
        else:
            # delete folder
            statusCode = 202
            statusPhrase = "Accepted"
            if not os.access(path.rsplit("/", 1)[0], os.W_OK):
                return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission delete ths folder." }
            else:
                start_new_thread(utility.deleteData, (path, False))
            
    # path does not exist
    else:
        utility.writeErrorLog("debug", str(os.getpid()), "-", path + " : 404 Not Found")
        return {"isError": True, "Status-Code": 404, "Status-Phrase": "Not Found", "Msg": "Could not found requested resource." }

    responseDict = {}
    responseDict["isError"] = False
    responseDict["Status-Code"] = str(statusCode)
    responseDict["Status-Phrase"] = statusPhrase
    responseDict["headers"] = {}
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    responseDict["headers"]["Content-Length"] = 0

    return responseDict
