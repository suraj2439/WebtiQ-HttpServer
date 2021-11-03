
import gzip
import mimetypes
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import hashlib
import time
import os
import json
import shutil
from _thread import *

import lzw3
import zlib

from requests_toolbelt import multipart
import utility
import brotli

MAX_REQ = 50
MAX_URI_LENGTH = 500
MAX_HEADER_LENGTH = 500
TIME_DIFF = 19800
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
DEFAULT_DIR_PATH = "/home/suraj/Documents/study/TY/CN/Project/test/"
EXPIRE_TIME = 86400
POST_FILE_PATH = "/home/suraj/Documents/study/TY/CN/Project/post.txt"
SERVER_PORT = 7000
MAX_DELETE_SIZE = 100


def get_or_head(reqDict, method):
    responseDict = {}
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
    acceptEncoding = headers.get("Accept-Encoding", "")
    contentEncoding = utility.handleEncodingPriority(acceptEncoding)
    if contentEncoding == None:
        return {"isError": True, "Status-Code": 406, "Status-Phrase": "Not Acceptable", "Msg": "Error in content-encoding header field or server could not handle content-encoding header field." }
    
    if fileExtension:
        path = path.rsplit(".", 1)[0] + fileExtension
    if not os.path.isfile(path):
        return {"isError": True, "Status-Code": 404, "Status-Phrase": "Not Found", "Msg": "Could not found requested resource." }
    else:
        if not os.access(path, os.R_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to read the file." }
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
        print(ifMatchArr)
        if ETag not in ifMatchArr and ifMatchArr[0] != "*":
            return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not match given ETag." }
    elif "If-Unmodified-Since" in headers.keys():
        date = datetime.strptime(headers["If-Unmodified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader < lastModifiedTime:
            return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet If-Unmodified-Since header requirements." }
    
    if "If-None-Match" in headers.keys():
        if "*" in ifNoneMatchArr or ETag in ifNoneMatchArr:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
    elif "If-Modified-Since" in headers.keys():
        date = datetime.strptime(headers["If-Modified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        print(timeFromHeader, lastModifiedTime)
        if timeFromHeader >= lastModifiedTime:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
            
    if "Range" in headers.keys() and (headers["Range"].split("="))[0] == "bytes":
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
            rangesList = headers["Range"].split('=')[1].split(',')
            if len(rangesList) > 1:
                return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "" }
            else:
                r_range = rangesList[0]
                # range format = -<value>
                if r_range[0] == "-":
                    startPos = 0
                    endPos = r_range[1:]
                # range format = <value>-
                elif r_range[-1] == "-":
                    startPos = r_range[:-1]
                    endPos = None
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
                    responseDict["headers"]["Content-Type"] = mimetypes.guess_type(path)[0]
                    body = utility.encodeData(fileData[int(startPos) : int(endPos)+1], contentEncoding)
                    responseDict["headers"]["Content-Length"] = len(body)
                    
                    if(method == "GET"):
                        responseDict["body"] = body
                        responseDict["headers"]["Content-MD5"] = hashlib.md5(responseDict["body"]).hexdigest()
                    return responseDict

    responseDict["isError"] = False
    responseDict["Status-Code"] = "200"
    responseDict["Status-Phrase"] = "OK"
    responseDict["headers"] = {}
    responseDict["headers"]["Last-Modified"] = utility.toRFC_Date(datetime.fromtimestamp(int(os.path.getmtime(path)) - TIME_DIFF))
    responseDict["headers"]["Content-Encoding"] = contentEncoding
    responseDict["headers"]["Content-Type"] = mimetypes.guess_type(path)[0]
    #responseDict["Content-Type"] = content_type
    responseDict["headers"]["ETag"] = ETag
    responseDict["headers"]["Accept-Ranges"] = "bytes"
    body = utility.encodeData(fileData, contentEncoding)
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    responseDict["headers"]["Content-Length"] = len(body)
    
    if(method == "GET"):
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

    #TODO check order of decompress
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
        #TODO handle not supporting encoding

    if not os.path.isfile(path):
        # folder/hi.png
        if not os.access(path.rsplit("/", 1)[0], os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
        else:
            fd = open(path, "w")
    else:
        if not os.access(path, os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
        else:
            fd = open(path, "a")
        
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
    
    if "If-None-Match" in headers.keys():
        if "*" in ifNoneMatchArr or ETag in ifNoneMatchArr:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
    elif "If-Modified-Since" in headers.keys():
        date = datetime.strptime(headers["If-Modified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader >= lastModifiedTime:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }

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
        print(contentType)
        if contentType.strip() in ["image/png", "image/jpg", "image/jpeg"]:
            fd = open(path, "wb")
            fd.write(body.encode("ISO-8859-1"))
            fd.close()
            responseDict["Status-Code"] = "201"
            responseDict["Status-Phrase"] = "Resourse Created"
        elif contentType.strip() in ["text/html", "text/plain"]:
            fd = open(path, "a")
            fd.write(body)
            fd.close()
            responseDict["Status-Code"] = "204"
            responseDict["Status-Phrase"] = "No Content"
        else:
            return {"isError": True, "Status-Code": 415, "Status-Phrase": "Unsupported Media Type", "Msg": "Could not support given media type." }
        
        responseDict["isError"] = False
        responseDict["headers"] = {}
        responseDict["headers"]["Content-Location"] = path.split(DEFAULT_DIR_PATH)[1]
        responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
        #TODO implement this header in testing code.
        responseDict["headers"]["Location"] = "http://localhost:" + str(SERVER_PORT) + "/postSuccess.html"
        responseDict["headers"]["Content-Length"] = 0
        return responseDict

    #postFileDesc = open(POST_FILE_PATH, "a")
    json.dump({utility.toRFC_Date(datetime.utcnow()): postDataDict}, fd, indent="\t")

    responseDict = {}
    responseDict["isError"] = False
    responseDict["Status-Code"] = "303"
    responseDict["Status-Phrase"] = "See Other"
    responseDict["headers"] = {}
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    #TODO implement this header in testing code.
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

    #TODO check order of decompress
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
        #TODO handle not supporting encoding
    if not os.path.isfile(path):
        statusCode = 201
        statusPhrase = "Resource Created"
        if not os.access(path.rsplit("/", 1)[0], os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
        else:
            fd = open(path, "w")
    else:
        statusCode = 204
        statusPhrase = "No Content"
        if not os.access(path, os.W_OK):
            return {"isError": True, "Status-Code": 403, "Status-Phrase": "Forbidden", "Msg": "Client donot have the permission to post at this location" }
        else:
            fd = open(path, "w")
        
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
    
    if "If-None-Match" in headers.keys():
        if "*" in ifNoneMatchArr or ETag in ifNoneMatchArr:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
    elif "If-Modified-Since" in headers.keys():
        date = datetime.strptime(headers["If-Modified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader >= lastModifiedTime:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }

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
    json.dump({utility.toRFC_Date(datetime.utcnow()): postDataDict}, fd, indent="\t")

    responseDict = {}
    responseDict["isError"] = False
    responseDict["Status-Code"] = str(statusCode)
    responseDict["Status-Phrase"] = statusPhrase
    responseDict["headers"] = {}
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    #TODO implement this header in testing code.
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
            
            if "If-None-Match" in headers.keys():
                if "*" in ifNoneMatchArr or ETag in ifNoneMatchArr:
                    return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
            elif "If-Modified-Since" in headers.keys():
                date = datetime.strptime(headers["If-Modified-Since"] , "%a, %d %b %Y %H:%M:%S GMT")
                timeFromHeader = time.mktime(date.timetuple())
                lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
                if timeFromHeader >= lastModifiedTime:
                    return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
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
        return {"isError": True, "Status-Code": 404, "Status-Phrase": "Not Found", "Msg": "Could not found requested resource." }

    responseDict = {}
    responseDict["isError"] = False
    responseDict["Status-Code"] = str(statusCode)
    responseDict["Status-Phrase"] = statusPhrase
    responseDict["headers"] = {}
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))
    responseDict["headers"]["Content-Length"] = 0

    return responseDict
