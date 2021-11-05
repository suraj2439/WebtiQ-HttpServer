import socket
from _thread import *
from time import sleep, time
import utility
from datetime import datetime
import httpMethods
from requests_toolbelt.multipart import decoder
from threading import Lock

"""
Cookie, local time and gmt time, content-type

Accept
Accept-Charset
Content-Type **
Content-Location
Location       TODO Use in POST request
Set-Cookie
Transfer-Encoding
Connection Keep-Alive
"""

# TODO handle absolute uri
# TODO multipart/byteranges


SERVER_PORT = 7000
MAX_CONN = 100
MAX_REQ = 50
MAX_URI_LENGTH = 500
MAX_HEADER_LENGTH = 500
TIME_DIFF = 19800
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
DEFAULT_DIR_PATH = "/home/suraj/Documents/study/TY/CN/Project/test/"
EXPIRE_TIME = 86400
MAX_KEEP_ALIVE_TIME = 10 # in seconds
TOT_COUNT = 20
ACCESS_LOG_PATH = DEFAULT_DIR_PATH + "log/access.log"

req_count = 0
lock = Lock()

# cookie : info
cookieDict = {}

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
        return {"isError": True, "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "request format is not supported."}
    
    [req_method, req_uri, http_version] = first_line

    if(isError(len(req_uri), "uri_too_long")):
        return {"isError": True, "First-Line": reqLine, "Status-Code": 414, "Status-Phrase": "URI Too Long", "Msg": "Requested uri is too long to handle to server."}
    
    if(isError(req_method, "method_not_implemented")):
        return {"isError": True, "First-Line": reqLine, "Status-Code": 405, "Status-Phrase": "Method Not Implemented", "Msg": "Requested method is not implemented at server side or server could not support requested method."}
    
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
            return {"isError": True, "First-Line": reqLine, "Status-Code": 431, "Status-Phrase": "Request header fields too large", "Msg": "Requested header field is too large to handle to server."}
        # TODO check for supported
        single_header[0] = single_header[0].strip()
        single_header[1] = single_header[1].strip()
        
        header_dict[single_header[0]] = single_header[1]
    if(isError(header_dict, "host_not_available")):
        return {"isError": True, "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Header format is incorrect."}

    return {"isError" : False, "First-Line": reqLine, "headers" : header_dict, "uri" : req_uri, "method" : req_method, "Version" : http_version, "body" : body}

    
def sendResponse():
    pass

def buildResponse(reqDict):
    method = reqDict.get("method")
    if method == "GET":
        return httpMethods.get_or_head(reqDict, "GET", cookieDict)
    elif method == "HEAD":
        return httpMethods.get_or_head(reqDict, "HEAD", cookieDict)
    elif method == "POST":
        return httpMethods.post(reqDict, cookieDict)
    elif method == "PUT":
        return httpMethods.put(reqDict, cookieDict)
    elif method == "DELETE":
        return httpMethods.delete(reqDict, cookieDict)


def receiveRequest(connection, clientAddr, timeout):
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
                sleep(timeout/TOT_COUNT)
                count += 1
        except Exception as e:
            connection.close()
            return None
        if "\r\n\r\n".encode() in partialReq:
            break
    contentLength = int(parse_request(partialReq.decode("ISO-8859-1"))["headers"].get("Content-Length", 0)) 
    contentLength -= len(partialReq.split("\r\n\r\n".encode(), 1)[1])
    body = b""

    while len(body) < contentLength:
        body += connection.recv(8096)
    return (partialReq + body).strip()


def new_thread(client_conn, client_addr, newSocket):
    while True:
        req = b''
        #TODO handle error
        #req = recv_timeout(new_socket, client_conn)
        req = receiveRequest(client_conn, client_addr, MAX_KEEP_ALIVE_TIME)
        if req == None:
            break

        reqDict = parse_request(req.decode("ISO-8859-1"))
        reqDict["Client-Address"] = client_addr
        if reqDict["isError"]:
            content = generate_error_response(reqDict["Status-Code"], reqDict["Status-Phrase"], reqDict["Msg"])
            responseDict = { "Version": "HTTP/1.1", "Status-Code": str(reqDict["Status-Code"]), "Status-Phrase": reqDict["Status-Phrase"], 
                "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close" , "Content-Length": str(len(content.encode())), "Content-Type": "text/html" }}
            if reqDict["method"] != "HEAD":
                responseDict["body"] = content.encode()
            if str(reqDict["Status-Code"]) == "405":
                responseDict["headers"]["Allow"] = "GET, HEAD, PUT, POST, DELETE"

            #responseDict["headers"]["Set-Cookie"] = "yummy_cookie=choco"
            utility.writeAccessLog(reqDict, resp, client_addr, ACCESS_LOG_PATH)
            print("sending")
            client_conn.send(utility.generateResponse(responseDict))

        else:
            response = buildResponse(reqDict)
            resp = { "Version": "HTTP/1.1", "Status-Code": str(response["Status-Code"]), "Status-Phrase": response["Status-Phrase"], 
                "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "keep-alive"  }}

            if response["isError"]:
                content = generate_error_response(response["Status-Code"], response["Status-Phrase"], response["Msg"])
                resp["headers"]["Content-Length"] = str(len(content.encode()))
                resp["headers"]["Content-Type"] = "text/html"
                if reqDict["method"] != "HEAD":
                    resp["body"] = content.encode()
            else:
                if response.get("body", None):
                    resp["body"] = response["body"]
                    resp["headers"]["Content-Length"] = response["headers"]["Content-Length"]
                resp["headers"].update(response["headers"])
            
            #resp["headers"]["Set-Cookie"] = "yummy_cookie=choco"
            utility.writeAccessLog(reqDict, resp, client_addr, ACCESS_LOG_PATH)
            print("sending")
            client_conn.send(utility.generateResponse(resp))
        if reqDict["headers"].get("Connection", "close") == "close":
            break
        # read from existing, make ds, write 

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
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_addr = ("localhost", SERVER_PORT)
    s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s_socket.bind(server_addr)
    s_socket.listen(MAX_CONN)

    while True:
        client_conn, client_addr = s_socket.accept()
        if(not isError(req_count, "req_too_long")):
            start_new_thread(new_thread, (client_conn, client_addr,s_socket))
        else:
            # temporarily server could not serve the request
            response = generate_error_response(503, "Service Unavailable")

    listening_socket.close()

if __name__ == '__main__':
    main()