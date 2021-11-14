import json
import os
import socket
from _thread import *
from time import sleep, time
from typing import DefaultDict
import utility
from datetime import datetime
import httpMethods
from threading import Lock
from config import *
import signal
import sys

def exit_handler(*args):
    fd = open(DEFAULT_DIR_PATH + "/cookies.json", "w")
    json.dump(cookieDict, fd, indent="\t")
    fd.close()
    utility.writeErrorLog("debug", str(os.getpid()), "-", "Server stopped")
    sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGTERM, exit_handler)


"""
Cookie, local time and gmt time, content-type

 stop-start-restart commands;
 error logging
 testing code
 todos
 handle query ?

 cannot find config or essential files, check for all imports(check for pip installs)
 wrong commandline arguments, could not open socket, terminal error messages, server busy,
 explain process(debug level), handle different try except(i/o exception, ) , 
 data not received completely(maybe socket problem, warn level), 

"""

# TODO handle absolute uri
# TODO multipart/byteranges

TOT_COUNT = 20

simultaneousConn = 0
lock = Lock()

# cookie : info
cookieDict = {}



def buildResponse(reqDict):
    global cookieDict
    method = reqDict.get("method")
    if method == "GET":
        response = httpMethods.get_or_head(reqDict, "GET")
    elif method == "HEAD":
        response = httpMethods.get_or_head(reqDict, "HEAD")
    elif method == "POST":
        return httpMethods.post(reqDict)
    elif method == "PUT":
        return httpMethods.put(reqDict)
    elif method == "DELETE":
        return httpMethods.delete(reqDict)

    lock.acquire()
    newCookie, cookieDict = utility.handleCookie(reqDict["headers"].get("Cookie", {}), reqDict["Client-Address"], method, cookieDict)
    if newCookie and not response["isError"]:
        response["headers"]["Set-Cookie"] = MY_COOKIE_NAME + "=" + newCookie + ";" + " Max-Age=" + str(COOKIE_EXPIRE_TIME)
    lock.release()
    return response


def new_thread(client_conn, client_addr, newSocket):
    global simultaneousConn
    timeoutDuration = MAX_KEEP_ALIVE_TIME
    maxReqCount = MAX_REQ_ON_PERSISTENT_CONN

    try: 
        while maxReqCount:
            req = b''
            #TODO handle error, handle pipeliningf
            #req = recv_timeout(new_socket, client_conn)
            req = utility.receiveSocketData(client_conn, timeoutDuration)
            if req == None:
                break

            reqDict = utility.parse_request(req.decode("ISO-8859-1"))
            if reqDict.get("First-Line"):
                utility.writeErrorLog("debug", str(os.getpid()), client_addr, reqDict["First-Line"])

            reqDict["Client-Address"] = client_addr
            if reqDict["isError"]:
                content = utility.generate_error_response(reqDict["Status-Code"], reqDict["Status-Phrase"], reqDict["Msg"])
                responseDict = { "Version": "HTTP/1.1", "Status-Code": str(reqDict["Status-Code"]), "Status-Phrase": reqDict["Status-Phrase"], "isError": True,
                    "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close" , "Content-Length": str(len(content.encode())), "Content-Type": "text/html" }}
                if reqDict.get("method") and reqDict["method"] != "HEAD":
                    responseDict["body"] = content.encode()
                if str(reqDict["Status-Code"]) == "405":
                    responseDict["headers"]["Allow"] = "GET, HEAD, PUT, POST, DELETE"

                if reqDict.get("headers") and reqDict["headers"].get("Connection", None):
                    responseDict["headers"]["Connection"] = reqDict["headers"]["Connection"]

                client_conn.send(utility.generateResponse(responseDict))
                utility.writeErrorLog("debug", str(os.getpid()), "-",reqDict.get("First-Line") + " - response sent.")

            else:
                response = buildResponse(reqDict)
                resp = { "Version": "HTTP/1.1", "Status-Code": str(response["Status-Code"]), "Status-Phrase": response["Status-Phrase"], "isError": False,
                    "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close"  }}

                if response["isError"]:
                    content = utility.generate_error_response(response["Status-Code"], response["Status-Phrase"], response["Msg"])
                    resp["isError"] = True
                    resp["headers"]["Content-Length"] = str(len(content.encode()))
                    resp["headers"]["Content-Type"] = "text/html"
                    if reqDict["method"] != "HEAD":
                        resp["body"] = content.encode()
                else:
                    if response.get("body", None):
                        resp["body"] = response["body"]
                        resp["headers"]["Content-Length"] = response["headers"].get("Content-Length", "0")
                    resp["headers"].update(response["headers"])
                
                if reqDict["headers"].get("Connection", None):
                    resp["headers"]["Connection"] = reqDict["headers"]["Connection"]
                #resp["headers"]["Set-Cookie"] = "yummy_cookie=choco"
                utility.writeAccessLog(reqDict, resp, client_addr, ACCESS_LOG_PATH)
                client_conn.send(utility.generateResponse(resp))
                utility.writeErrorLog("debug", str(os.getpid()), "-",reqDict.get("First-Line") + " - response sent.")
            if reqDict.get("headers"):
                if reqDict["headers"].get("Connection", "close") == "close":
                    client_conn.close()
                    break
                else:
                    keepAlive = reqDict["headers"].get("Keep-Alive")
                    # TODO what if client sends keep alive each time
                    if keepAlive:
                        keepAliveArr = keepAlive.split(",")
                        keepAliveArr = utility.stripList(keepAliveArr)
                        timeoutDuration = int(keepAliveArr[0].split("=")[1].strip())
                        maxReqCount = int(keepAliveArr[1].split("=")[1].strip())
            else:
                client_conn.close()
                break
            maxReqCount -= 1
            # read from existing, make ds, write 
        simultaneousConn -= 1
    except:
        utility.writeErrorLog("warn", str(os.getpid()), "-", "internal server error.")


    """
    httpVersion
    statuscode
    phrase
    response header dict
    
    """

def main():
    global cookieDict, simultaneousConn
    fd = open(DEFAULT_DIR_PATH + "/cookies.json", "r")
    cookieDict = json.load(fd)
    fd.close()

    try:
        s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_addr = ("localhost", SERVER_PORT)
        s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_socket.bind(server_addr)
        s_socket.listen(MAX_CONN)
        utility.writeErrorLog("debug", str(os.getpid()), "-","Server started on port: " + str(SERVER_PORT))
    except:
        utility.writeErrorLog("critical", str(os.getpid()), "-", "Socket error.")

    while True:
        client_conn, client_addr = s_socket.accept()
        utility.writeErrorLog("debug", str(os.getpid()), client_addr, "Accepted new connection")
        simultaneousConn += 1
        if(not utility.isError(simultaneousConn, "max_simult_conn_exceed")):
            start_new_thread(new_thread, (client_conn, client_addr,s_socket))
        else:
            # temporarily server could not serve the request
            response = utility.gen_503_response()
            client_conn.send(response.encode("ISO-8859-1"))
            client_conn.close()
            utility.writeErrorLog("warn", str(os.getpid()), "-","max connection reached.")
            # TODO send response

if __name__ == '__main__':
    main()