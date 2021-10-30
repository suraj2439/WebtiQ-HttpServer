import socket
from _thread import *
import utility
from urllib.parse import urlparse
import os
from datetime import datetime
import hashlib
import time

"""
Cookie, local time and gmt time, content-type

Accept
Accept-Charset
Content-Type
User-Agent
Content-Location
Location       TODO Use in POST request
Set-Cookie
Transfer-Encoding
Connection Keep-Alive
"""



SERVER_PORT = 7000
MAX_CONN = 100
MAX_REQ = 50
MAX_URI_LENGTH = 500
MAX_HEADER_LENGTH = 500
TIME_DIFF = 19800
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
DEFAULT_DIR_PATH = "/home/suraj/Documents/study/TY/CN/Project/"
EXPIRE_TIME = 86400

req_count = 0

def isError(data, errorType):
    if(errorType == "req_too_long"):
        if(data < MAX_REQ):
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
        if(len(http_version) != 2 or http_version[0] != "HTTP" or (http_version[0].lstrip())[0] != "1"):
            return True
        return False
    elif errorType == "host_not_available":
        if("Host" not in data):
            return True
        return False


# seperate request header, body, method, uri, data etc...
def parse_request(request):
    # seperate header and body
    request = request.split("\r\n\r\n")

    header = request[0]
    body = ""
    if(len(request) > 1):
        body = request[1]

    header_lines = header.split("\r\n")
    first_line = header_lines[0].split()
    if(len(first_line) != 3):
        # TODO crosscheck error code
        return {"isError": True, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "request format is not supported."}
    
    [req_method, req_uri, http_version] = first_line

    if(isError(len(req_uri), "uri_too_long")):
        return {"isError": True, "Status-Code": 414, "Status-Phrase": "URI Too Long", "Msg": "Requested uri is too long to handle to server."}
    
    if(isError(req_method, "method_not_implemented")):
        return {"isError": True, "Status-Code": 405, "Status-Phrase": "Method Not Implemented", "Msg": "Requested method is not implemented at server side or server could not support requested method."}
    
    """if(isError(http_version, "version_not_supported")):
        response = generate_error_response(505, "HTTP Version Not Supported", "HTTP Version Not Supported, either requested wrong version format or requested http version is not supported by server.")
        return response"""
    
    headers = header_lines[1:]
    header_dict = {}
    for single_header in headers:
        single_header = single_header.split(":", 1)
        if len(single_header) != 2:
            # TODO cross check response code
            response = generate_error_response(400, "Bad Request", "Header format is incorrect.")
            return response
        if(isError(len(single_header[1]), "header_too_long")):
            return {"isError": True, "Status-Code": 431, "Status-Phrase": "Request header fields too large", "Msg": "Requested header field is too large to handle to server."}
        # TODO check for supported 
        single_header[0] = single_header[0].strip()
        single_header[1] = single_header[1].strip()
        
        header_dict[single_header[0]] = single_header[1]
    if(isError(header_dict, "host_not_available")):
        return {"isError": True, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Header format is incorrect."}

    return {"isError" : False, "headers" : header_dict, "uri" : req_uri, "method" : req_method, "Version" : http_version, "body" : body}

    
def sendResponse():
    pass

def buildResponse(reqDict):
    responseDict = {}
    headers = reqDict.get("headers")
    uri = reqDict.get("uri")
    method = reqDict.get("method")
    body = reqDict.get("body")
    accept = headers.get("Accept", "*/*")
    acceptEncoding = headers.get("Accept-Encoding", "")
    contentEncoding = utility.handleEncodingPriority(acceptEncoding)
    if contentEncoding == None:
        return {"isError": True, "Status-Code": 406, "Status-Phrase": "Not Acceptable", "Msg": "Error in content-encoding header field or server could not handle content-encoding header field." }
        
    path = urlparse(uri).path
    if path == "/":
        path = "/index.html"
    path = DEFAULT_DIR_PATH + path
    
    if not os.path.isfile(path):
        return {"isError": True, "Status-Code": 404, "Status-Phrase": "Not Found", "Msg": "Could not found requested resource." }
    else:
        fd = open(path, 'rb')
        fileData = fd.read()
        fd.close()
   

    """
    TODO
    Doubt: How to provide file according to accept header?
    1. Does same file with different extenstion is available at server side. or
    2. Do we need to convert file type like jpg to png.
    """
    acceptContent = utility.handleAcceptContentPriority(accept)
    ifModified = headers.get("If-Modified-Since", utility.toRFC_Date(datetime.fromtimestamp(0)))
    ifUnmodified = headers.get("If-Unmodified-Since", utility.toRFC_Date(datetime.utcnow()))
    ifMatch = headers.get('If-Match',"*")
    ifNoneMatch = headers.get('If-None-Match',"")
    
    ifMatchArr = ifMatch.split(",")
    ifNoneMatchArr = ifNoneMatch.split(",")

    # generate Etag
    Etag = '"' + hashlib.md5((str(os.path.getmtime(path)).encode())).hexdigest() + '"'

    if "if-match" in headers.keys():
        if Etag in ifMatchArr or ifMatchArr[0] == "*":
            return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not match given etag." }
    elif "if-unmodified-since" in headers.keys():
        date = datetime.strptime(headers["if-unmodified-since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader < lastModifiedTime:
            return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet if-unmodified-since header requirements." }
    
    if "if-none-match" in headers.keys():
        if "*" in ifNoneMatchArr or Etag in ifNoneMatchArr:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
    elif "if-modified-since" in headers.keys():
        date = datetime.strptime(headers["if-modified-since"] , "%a, %d %b %Y %H:%M:%S GMT")
        timeFromHeader = time.mktime(date.timetuple())
        lastModifiedTime = os.path.getmtime(path) - TIME_DIFF
        if timeFromHeader >= lastModifiedTime:
            return {"isError": True, "Status-Code": 304, "Status-Phrase": "Not Modified", "Msg": "Given resource is not modified." }
            
    if "range" in headers.keys() and (headers["range"].split("="))[0] == "bytes":
        dataAvailable = True
        # check for conditions on range header
        if "if-range" in headers.keys():
            # if-range header is in Etag format
            if headers["if-range"][0] == '"':
                if headers["if-range"] != Etag:
                    dataAvailable = False
            # if-range header is in last-modified format
            else:
                date = datetime.strptime(headers["if-modified-since"] , "%a, %d %b %Y %H:%M:%S GMT")
                timeFromHeader = time.mktime(date.timetuple())
                lastModifiedTime = os.path.getmtime(path) - TIME_DIFF

                if timeFromHeader < lastModifiedTime:
                    dataAvailable = False
        
        if dataAvailable:
            rangesList = headers["range"].split('=')[1].split(',')
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
                    responseDict["body"] = utility.encodeData(fileData[startPos : endPos+1], contentEncoding)
                    responseDict["headers"]["Content-Length"] = len(responseDict["body"])
                    responseDict["headers"]["Content-MD5"] = hashlib.md5(responseDict["body"]).hexdigest()
                    return responseDict

        #if "cookie" not in headers.keys():
        #    response["headers"]["Set-Cookie"] = "sessionId={}".format(random.randint(100000, 1000000))
    responseDict["isError"] = False
    responseDict["Status-Code"] = "200"
    responseDict["Status-Phrase"] = "OK"
    responseDict["headers"] = {}
    responseDict["headers"]["Last-Modified"] = utility.toRFC_Date(datetime.fromtimestamp(int(os.path.getmtime(path)) - TIME_DIFF))
    responseDict["headers"]["Content-Encoding"] = contentEncoding
    #responseDict["Content-Type"] = content_type
    responseDict["headers"]["E-tag"] = Etag
    responseDict["headers"]["Accept-Ranges"] = "bytes"
    responseDict["body"] = utility.encodeData(fileData, contentEncoding)
    responseDict["headers"]["Content-Length"] = len(responseDict["body"])
    responseDict["headers"]["Content-MD5"] = hashlib.md5(responseDict["body"]).hexdigest()
    responseDict["headers"]["Expires"] = utility.toRFC_Date(datetime.fromtimestamp(int(time.time()) + EXPIRE_TIME))

    return responseDict

    # else:
    #     return {"isError": True, "Status-Code": 412, "Status-Phrase": "Precondition Failed", "Msg": "Could not meet range header requirements." }

def new_thread(client_conn, client_addr):
    req = b''
    while True:
        partial_request = client_conn.recv(30)
        req += partial_request
        if len(partial_request) < 30:
            break

    reqDict = parse_request(req.decode())
    if reqDict["isError"]:
        content = generate_error_response(reqDict["Status-Code"], reqDict["Status-Phrase"], reqDict["Msg"])
        responseDict = { "Version": "HTTP/1.1", "Status-Code": str(reqDict["Status-Code"]), "Status-Phrase": reqDict["Status-Phrase"], 
            "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close" , "Content-Length": str(len(content.encode())) }, 
            "body": content.encode()}
        if str(reqDict["Status-Code"]) == "405":
            responseDict["headers"]["Allow"] = "GET, HEAD, PUT, POST, DELETE"

        client_conn.send(utility.generateResponse(responseDict))

    else:
        response = buildResponse(reqDict)
        resp = { "Version": "HTTP/1.1", "Status-Code": str(response["Status-Code"]), "Status-Phrase": response["Status-Phrase"], 
            "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close", "Content-Length": ""  }, 
            "body": ""}

        if response["isError"]:
            content = generate_error_response(response["Status-Code"], response["Status-Phrase"], response["Msg"])
            resp["headers"]["Content-Length"] = str(len(content.encode()))
            resp["body"] = content.encode()
        else:
            resp["body"] = response["body"]
            resp["headers"]["Content-Length"] = response["headers"]["Content-Length"]
            resp["headers"].update(response["headers"])

        client_conn.send(utility.generateResponse(resp))



    """
    httpVersion
    statuscode
    phrase
    response header dict
    
    """


def generate_error_response(errorCode, errorPhrase, errorMsg):
    resp = """<!DOCTYPE html>
            <html>
                <head>
                    <title>{} {}</title>
                </head>
            <body>
                <h1>{}</h1>
                <p1>{}</p>
            </body>
            </html>""".format(errorCode, errorPhrase, errorPhrase, errorMsg)
    return resp

def main():
    path = "/home/suraj/Documents/study/TY/CN/Project/http-server/conditional_get_flowchart.png"
    # print(os.path.getatime("/home/suraj/Documents/study/TY/CN/Project/http-server/rfc_notes.txt"))
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_addr = ("localhost", SERVER_PORT)
    s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s_socket.bind(server_addr)
    s_socket.listen(MAX_CONN)

    while True:
        client_conn, client_addr = s_socket.accept()
        if(not isError(req_count, "req_too_long")):
            start_new_thread(new_thread, (client_conn, client_addr))
        else:
            # temporarily server could not serve the request
            response = generate_error_response(503, "Service Unavailable")

    listening_socket.close()

if __name__ == '__main__':
    main()