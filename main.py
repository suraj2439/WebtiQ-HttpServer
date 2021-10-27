import socket
from _thread import *
import utility
from urllib.parse import urlparse
import os


SERVER_PORT = 8001
MAX_CONN = 100
MAX_REQ = 50
MAX_URI_LENGTH = 500
MAX_HEADER_LENGTH = 500
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
DEFAULT_DIR_PATH = ""

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
        response = generate_error_response(400, "Bad Request", "request format is not supported.")
        return response
    
    [req_method, req_uri, http_version] = first_line

    if(isError(len(req_uri), "uri_too_long")):
        response = generate_error_response(414, "URI Too Long", "Requested uri is too long to handle to server.")
        return response
    
    if(isError(req_method, "method_not_implemented")):
        response = generate_error_response(501, "Method Not Implemented", "Requested method is not implemented at server side or server could not support requested method.")
        return response
    
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
            response = generate_error_response(431, "Request header fields too large", "Requested header field is too large to handle to server.")
            return response
        # TODO check for supported 
        single_header[0] = single_header[0].strip()
        single_header[1] = single_header[1].strip()
        
        header_dict[single_header[0]] = single_header[1]
    if(isError(header_dict, "host_not_available")):
        response = generate_error_response(400, "Bad Request", "Header format is incorrect.")
        return response

    return {"headers" : header_dict, "uri" : req_uri, "method" : req_method, "version" : http_version, "body" : body}

    
def sendResponse():
    pass

def buildResponse(reqDict):
    headers = reqDict.get("headers")
    uri = reqDict.get("uri")
    method = reqDict.get("method")
    body = reqDict.get("body")
    accept = headers.get("accept", "*/*")
    acceptEncoding = headers.get("accept-encoding", "")
    contentEncoding = utility.handleEncodingPriority(acceptEncoding)
    if contentEncoding == None:
        return generate_error_response(406, "Not Acceptable", "Error in content-encoding header field or server could not handle content-encoding header field.")

    
    path = urlparse(uri).path
    if path == "/":
        path = "/index.html"
    path = DEFAULT_DIR_PATH + path
    
    if not os.path.isfile(path):
        return generate_error_response(404, "Not Found", "Could not found requested resource.")
    """
    TODO
    Doubt: How to provide file according to accept header?
    1. Does same file with different extenstion is available at server side. or
    2. Do we need to convert file type like jpg to png.
    """
    
    acceptContent = utility.handleAcceptContentPriority()





def new_thread(client_conn, client_addr):
    req = b''
    while True:
        partial_request = client_conn.recv(30)
        req += partial_request
        if len(partial_request) < 30:
            break

    reqDict = parse_request(req.decode())
    if(not isinstance(reqDict, dict)):
        sendResponse()
    else:
        buildResponse(reqDict)

    print(reqDict)

    


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
            start_new_thread(new_thread, (client_conn, client_addr))
        else:
            response = generate_error_response(503, "Service Unavailable")

    listening_socket.close()

if __name__ == '__main__':
    main()