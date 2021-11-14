from datetime import datetime
from math import trunc
import time
from typing import Tuple
from urllib.parse import urlparse
from PIL.Image import Image
import requests
import socket
from config import *
import json
from utility import toRFC_Date, receiveSocketData
from threading import Thread


SERVER_URL = "http://127.0.0.1:" + str(SERVER_PORT)
etagValue = '"900f23da801f61dab9dab7af2d2d1c30"'
lastModifiedValue = "Mon, 08 Nov 2021 08:10:07 GMT"


def printRequestResponse(response, method):
    print("\nREQUEST")
    print("Method = " + method)
    print("URL = " + response.request.url)
    reqHeaders = response.request.headers
    for header in reqHeaders.keys():
        print(header, ":", reqHeaders[header])
    if response.request.body:
        print(response.request.body)

    print("\nRESPONSE")
    print(f"Status : {response.status_code} {response.reason}")
    for header in response.headers.keys():
        print(header, ":", response.headers[header])
    print("\n\n")

    print(response.content.decode("ISO-8859-1"))

def line():
    print("-"*100)

# HEADERS TESTING SECTION
def test1():
    line()
    print("Test1 - Target: Uri Too Long Error")
    try:
        response = requests.head(SERVER_URL + "/" + "a"*501)
        printRequestResponse(response, "HEAD")
        
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test2():
    line()
    print("Test2 - Target: 405 Method not implemented(options)")
    try:
        response = requests.options(SERVER_URL + "/")
        printRequestResponse(response, "OPTIONS")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 

def test3():
    line()
    print("Test3 - 431 Target: Header too long(connection header)")
    try:
        response = requests.head(SERVER_URL + "/", headers={'Connection': 'error'*101 })
        printRequestResponse(response, "HEAD")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 

def test4():
    line()
    print("Test4 - Target: 505 HTTP version not supported(HTTP/2)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = ("HEAD / HTTP/2\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 0\r\n\r\n").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = receiveSocketData(clientSocket, MAX_KEEP_ALIVE_TIME)

        print("\nRESPONSE")
        print(response.decode())

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 

def test5():
    line()
    print("Test5 - Target: 400 Bad Request(Necessary header 'Host' not sent.)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = "HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 0\r\n\r\n".encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = receiveSocketData(clientSocket, MAX_KEEP_ALIVE_TIME)
        print("\nRESPONSE")
        print(response.decode("ISO-8859-1"))

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 

def test6():
    line()
    print("Test6 - Target: 400 Bad Request(Wrong Header format)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = "HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 0\r\n\r\n".encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = receiveSocketData(clientSocket, MAX_KEEP_ALIVE_TIME)
        print("\nRESPONSE")
        print(response.decode("ISO-8859-1"))

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 

def test7():
    line()
    print("Test7 - Target: 406 Not Acceptable(Server could not handle given Encoding 'exi'.)")
    try:
        response = requests.get(SERVER_URL + "/", headers={'Accept-Encoding': 'exi,*;q=0' })
        printRequestResponse(response, "GET")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test8():
    line()
    print("Test8 - Target: 404 Not Found(File not found)")
    try:
        response = requests.get(SERVER_URL + "/NotFound.txt")
        printRequestResponse(response, "GET")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test9():
    line()
    print("Test9 - Target: 403 Forbidden(File donot have read permission)")
    try:
        response = requests.get(SERVER_URL + "/ReadLock.txt")
        printRequestResponse(response, "GET")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test10():
    line()
    print("Test10 - Target: 400 Bad Request(Checksum error- Content-MD5 header)")
    try:
        response = requests.post(SERVER_URL + "/ReadLock.txt", headers = {"Content-MD5" : "11111111"}, data=json.dumps({"KEY" : "VALUE"}))
        printRequestResponse(response, "POST")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test11():
    line()
    print("Test11 - Target: Simple GET request.")
    try:
        response = requests.get(SERVER_URL + "/")
        printRequestResponse(response, "GET")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test12():
    line()
    print("Test12 - Target: Simple HEAD request.")
    try:
        response = requests.head(SERVER_URL + "/")
        printRequestResponse(response, "HEAD")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test13():
    line()
    print("Test13 - Target: Simple POST request.")
    try:
        response = requests.post(SERVER_URL + "/post/de.txt", data = "Sample post request data.".encode("ISO-8859-1"))
        printRequestResponse(response, "POST")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test14():
    line()
    print("Test14 - Target: Simple PUT request.")
    try:
        response = requests.put(SERVER_URL + "/put/def.txt", data = "Sample put request data.".encode("ISO-8859-1"))
        printRequestResponse(response, "PUT")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test15():
    line()
    print("Test15 - Target: Simple DELETE request.")
    try:
        response = requests.delete(SERVER_URL + "/delete/abc.txt")
        printRequestResponse(response, "DELETE")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test16():
    line()
    print("Test16 - Target: Headers - Accept, Accept-Charset, Accept-Encoding")
    try:
        print("First Request, expecting 'text' file , 'utf-8' charset and 'br' content encoding.")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"Accept": "text/html;q=0.6, text/plain;q=0.9", "Accept-Charset": "ISO-8859-1;q=0.6, utf-8;q=0.9", "Accept-Encoding": "gzip;q=0.6,br;q=0.9"})
        printRequestResponse(response, "GET")
        
        line()

        print("Second request, expecting 'html' file , 'ISO-8859-1' charset and content encoding '*'")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"Accept": "text/html;q=0.9,text/plain;q=0.6", "Accept-Charset": "ISO-8859-1;q=0.9, utf-8;q=0.6", "Accept-Encoding": "gzip;q=0.9, br;q=0.6, *;q=1"})
        
        # Values used in next test
        global etagValue, lastModifiedValue
        etagValue = response.headers.get("Etag", etagValue)
        lastModifiedValue = response.headers.get("Last-Modified", lastModifiedValue)

        printRequestResponse(response, "GET")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test17():
    line()
    print("Test17 - Target: Headers - If-Modified-Since Header")
    try:
        print("First Request, expecting 304 Not Modified")
        date = datetime.strptime(lastModifiedValue , "%a, %d %b %Y %H:%M:%S GMT")
        lastModifiedTime = time.mktime(date.timetuple())
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Modified-Since": toRFC_Date(datetime.fromtimestamp(lastModifiedTime + 60))})
        printRequestResponse(response, "GET")
        
        line()

        print("First Request, expecting 200 OK")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Modified-Since": toRFC_Date(datetime.fromtimestamp(lastModifiedTime - 60))})
        printRequestResponse(response, "GET")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test18():
    line()
    print("Test18 - Target: Headers - If-Unmodified-Since Header")
    try:
        print("First Request, expecting 200 OK.")
        date = datetime.strptime(lastModifiedValue , "%a, %d %b %Y %H:%M:%S GMT")
        lastModifiedTime = time.mktime(date.timetuple())
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Unmodified-Since": toRFC_Date(datetime.fromtimestamp(lastModifiedTime + 60))})
        printRequestResponse(response, "GET")
        
        line()

        print("First Request, expecting 412 Precondition Failed.")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Unmodified-Since": toRFC_Date(datetime.fromtimestamp(lastModifiedTime - 60))})
        printRequestResponse(response, "GET")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test19():
    line()
    print("Test19 - Target: Headers - If-Match Header")
    try:
        print("First Request, expecting 200 OK.")
        date = datetime.strptime(lastModifiedValue , "%a, %d %b %Y %H:%M:%S GMT")
        lastModifiedTime = time.mktime(date.timetuple())
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Match": etagValue + "," + '"22222222222"'})
        printRequestResponse(response, "GET")
        
        line()

        print("First Request, expecting 412 Precondition Failed.")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Match": "111111111" + "," + '"222222222"'})
        printRequestResponse(response, "GET")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return

def test20():
    line()
    print("Test20 - Target: Headers - If-None-Match Header")
    try:
        print("First Request, expecting 304 Not Modified.")
        date = datetime.strptime(lastModifiedValue , "%a, %d %b %Y %H:%M:%S GMT")
        lastModifiedTime = time.mktime(date.timetuple())
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-None-Match": etagValue + "," + '"22222222222"'})
        printRequestResponse(response, "GET")
        
        line()

        print("Second Request, expecting 200 OK")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-None-Match": '"1111111111"' + "," + '"22222222222"'})
        printRequestResponse(response, "GET")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test21():
    line()
    print("Test21 - Target: Headers - If-Range and Range")
    try:
        print("First Request, expecting 206 Partial Content(in multipart/byteranges format).")
        date = datetime.strptime(lastModifiedValue , "%a, %d %b %Y %H:%M:%S GMT")
        lastModifiedTime = time.mktime(date.timetuple())
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Range": etagValue, "Range": "bytes= -10, 20-30, 40-"})
        printRequestResponse(response, "GET")
        
        line()

        print("First Request, expecting 200 OK")
        response = requests.get(SERVER_URL + "/accept.html", headers = {"If-Range": '"1111111111"', "Range": "bytes= -10, 20-30, 40-"})
        printRequestResponse(response, "GET")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test22():
    line()
    print("Test22 - Target: Headers - Content-Loction")
    try:
        response = requests.post(SERVER_URL + "/post/def.txt", data = "Sample post request data.".encode("ISO-8859-1"))
        printRequestResponse(response, "POST")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test23():
    line()
    print("Test23 - Target: Headers - Location")
    print("\nPART 1: Testing using socket to see 'Location' header\n")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        # TEST 1 (Simple GET request)
        get_request = ("POST /post/form2 HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nContent-Type: application/x-www-form-urlencoded\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 23\r\n\r\nkey1=value1&key2=value2").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = receiveSocketData(clientSocket, MAX_KEEP_ALIVE_TIME)

        print("\nRESPONSE")
        print(response.decode())

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()


    print("\nPART 2: testing using python requests module to verify redirection.")

    try:
        response = requests.post(SERVER_URL + "/post/form1", headers={"Content-Type": "application/x-www-form-urlencoded"}, data = {"key1":"value1", "key2":"value2"})
        printRequestResponse(response, "POST")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test24():
    line()
    print("Test24 - Target Header: Transfer-Encoding(chunked)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = ("GET / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\n\r\n").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = receiveSocketData(clientSocket, MAX_KEEP_ALIVE_TIME)

        print("\nRESPONSE")
        response = response.split("\r\n\r\n".encode(), 1)
        print(response[0].decode())
        print("\nPRINTING RAW BODY TO VIEW CHUNKS.")
        print(repr(response[1]))

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 

def test25():
    line()
    print("Test25 - Target: 'Allow' header")
    try:
        response = requests.options(SERVER_URL + "/")
        printRequestResponse(response, "OPTIONS")
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 


def test26():
    line()
    print("Test26 - Headers: Cookie, Set-Cookie")
    try:
        response = requests.head(SERVER_URL + "/")
        printRequestResponse(response, "HEAD")
        receivedCookie = response.headers.get("Set-Cookie")
        if receivedCookie:
            print("Sending 2 HEAD and 2 GET request with cookie to verify if count of requests is increamented in cookie file.")
            receivedCookie = receivedCookie.split(";")[0].strip()
            requests.head(SERVER_URL + "/", headers={"Cookie": receivedCookie})
            requests.head(SERVER_URL + "/", headers={"Cookie": receivedCookie})
            requests.get(SERVER_URL + "/", headers={"Cookie": receivedCookie})
            requests.get(SERVER_URL + "/", headers={"Cookie": receivedCookie})

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 


def fun(req, no):
    print("REQUEST: " + no)
    serverName = "127.0.0.1"
    serverPort = int(SERVER_PORT)
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((serverName, serverPort))

    print(req.decode("ISO-8859-1"))
    clientSocket.send(req)

    response = receiveSocketData(clientSocket, MAX_KEEP_ALIVE_TIME)

    print("\nRESPONSE " + no) 
    response = response.split("\r\n\r\n".encode(), 1)
    print(response[0].decode())


def test27():
    line()
    print("Test27: PART 1 - Target: Connection 'close'(non persistent connection)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = ("HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)

        response = receiveSocketData(clientSocket, 2)

        print("\nRESPONSE")
        print(response.decode())

        clientSocket.send(get_request)
        response = b''

        response = receiveSocketData(clientSocket, 2)

        print("\nRESPONSE")
        if response:
            print(response.decode())
            print("Data is received, Connection is alive")
        else:
            print("Data not received, Connection is 'closed'")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()


    print("Test27: PART 2 - Target: Connection 'keep-alive'(persistent connection)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = ("HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: keep-alive\r\n\r\n").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)

        response = receiveSocketData(clientSocket, 2)

        print("\nRESPONSE")
        print(response.decode())

        clientSocket.send(get_request)
        response = b''

        response = receiveSocketData(clientSocket, 2)

        print("\nRESPONSE")
        if response:
            print(response.decode())
            print("Data is received, Connection is alive")
        else:
            print("Data not received, Connection is 'closed'")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test28():
    line()
    print("Test28: PART 1 - Target: timeout field of Keep-Alive header.")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = ("HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: keep-alive\r\nKeep-Alive: timeout=1, max=3\r\n\r\n").encode("ISO-8859-1")

        print("\nESTABLISHING PERSISTENT CONNECTION WITH 'Keep-Alive' HEADER.\n")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)

        response = receiveSocketData(clientSocket, 2)
        print("\nRESPONSE")
        print(response.decode())

        print("WAITING FOR TIMEOUT AT SERVER(SLEEP 1.5 sec)")
        time.sleep(1.5)

        clientSocket.send(get_request)
        response = b''

        print("WAITING FOR RESPONSE")
        response = receiveSocketData(clientSocket, 2)

        if response:
            print(response.decode())
            print("Data is received, Connection is alive")
        else:
            print("Data not received, Connection is 'closed'")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()


    print("Test28: PART 2 - Target: 'max' field of Keep-Alive header.")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        get_request = ("HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: keep-alive\r\nKeep-Alive: timeout=1, max=3\r\n\r\n").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)

        response = receiveSocketData(clientSocket, 2)

        print("\nRESPONSE")
        print(response.decode())

        count = 3
        get_request = ("HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: keep-alive\r\n\r\n").encode("ISO-8859-1")
        print("SENDING MULTIPLE REQUESTS TO VERIFY MAX FIELD")
        print("WAITING FOR RESPONSES")
        while count:
            clientSocket.send(get_request)
            response = b''
            response = receiveSocketData(clientSocket, 2)
            if response:
                print("response received.")
            else:
                print("maximum requests reached, server has closed connection.")
            count -= 1

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


def test29():
    line()
    print("Test29 - Target: Testing Multi-threading.")
    print("Sending get request followed by head, but response is first received for head, \nwhich indicates server is multithreaded.\n")
    try:
        get_request1 = ("GET /bigSample.txt HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").encode("ISO-8859-1")
        get_request2 = ("HEAD / HTTP/2\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").encode("ISO-8859-1")

        thrd1 = Thread(target=fun, args=(get_request1, "1 : GET"))
        thrd2 = Thread(target=fun, args=(get_request2, "2 : HEAD"))

        thrd1.start()
        time.sleep(0.001)
        thrd2.start()

        thrd1.join()
        thrd2.join()
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return 



def test30():
    line()
    print("Test30 - Target: Media types. (image, audio, video, pdf)")
    try:
        response = requests.get(SERVER_URL + "/sample.png")
        fd = open("media-types/test.png", "wb")
        fd.write(response.content)
        fd.close()
        print("Received image response")

        response = requests.get(SERVER_URL + "/sample.mp3")
        fd = open("media-types/audio.mp3", "wb")
        fd.write(response.content)
        fd.close()
        print("Received audio response")

        response = requests.get(SERVER_URL + "/sample.mp4")
        fd = open("media-types/video.mp4", "wb")
        fd.write(response.content)
        fd.close()
        print("Received video response")

        response = requests.get(SERVER_URL + "/sample.pdf")
        fd = open("media-types/test.pdf", "wb")
        fd.write(response.content)
        fd.close()
        print("Received pdf response")

        print("\nYou can view this files in 'media-types' folder in project directory.")

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        line()
        return


# def test31():
#     line()
#     print("Test31 - Target: max simutaneous connections reached")
#     try:
#         count = 20
#         while count:
#             response = requests.get(SERVER_URL + "/bigSample.txt", headers={"Connection" : "close"})
#             print(response.status_code)
#             count -= 1
#         time.sleep(10)
#         response = requests.get(SERVER_URL + "/bigSample.txt", headers={"Connection" : "close"})
#         print(response.status_code)

#     except Exception as e:
#         print('Something unexpected occured!', e)
#     finally:
#         line()
#         return

for i in range (1, 31):
    eval("test"+str(i)+"()")
