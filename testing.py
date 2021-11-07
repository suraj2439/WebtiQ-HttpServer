"""
headers
error codes
logs testing
cookies
persistent connections
http methods
bad request
multi threading
multipart data
max connections exceed 
conditional request
server start/stop
"""

from os import getresgid
import requests
import socket
from config import *
import json


"""
try:
            print("\nMaking a POST Request")
            data = dict(
                key1='TEST',
                value1='TEST DATA'
            )
            r = requests.post(SERVER_URL + "/test",
                data=json.dumps(data),
                headers={'content-type': 'application/json'}
            )
            print(f"Status : {r.status_code} {r.reason}")
            print("Headers:", r.headers)
        except Exception as ex:
            print('Something went horribly wrong!', ex)
        finally:
            return

"""
SERVER_URL = "http://127.0.0.1:" + str(SERVER_PORT)

"""
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
        """
def printRequestResponse(response):
    print("\nREQUEST")
    print(response.request.url)
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

# HEADERS TESTING SECTION
def test1():
    print("Test1 - Target: Uri Too Long Error")
    try:
        response = requests.head(SERVER_URL + "/" + "a"*501)
        printRequestResponse(response)
        
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test2():
    print("Test2 - Target: Method not implemented(options)")
    try:
        response = requests.options(SERVER_URL + "/")
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return 

def test3():
    print("Test3 - Target: Header too long(connection header)")
    try:
        response = requests.head(SERVER_URL + "/", headers={'Connection': 'error'*101 })
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return 

def test4():
    print("Test4 - Target: HTTP version not supported(HTTP/2)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        # TEST 1 (Simple GET request)
        get_request = ("HEAD / HTTP/2\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nHost: localhost:" + str(SERVER_PORT) +"\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 0\r\n\r\n").encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = b''
        while True:
            partial_response = clientSocket.recv(8024)

            response += partial_response
            if len(partial_response) < 8024:
                break

        print("\nRESPONSE")
        print(response.decode())

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return 

def test5():
    print("Test5 - Target: Bad Request(Necessary header 'Host' not sent.)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        # TEST 1 (Simple GET request)
        get_request = "HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent: PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 0\r\n\r\n".encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = b''
        while True:
            partial_response = clientSocket.recv(8024)

            response += partial_response
            if len(partial_response) < 8024:
                break
        print("\nRESPONSE")
        print(response.decode("ISO-8859-1"))

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return 

def test6():
    print("Test6 - Target: Bad Request(Wrong Header format)")
    try:
        serverName = "127.0.0.1"
        serverPort = int(SERVER_PORT)
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))

        # TEST 1 (Simple GET request)
        get_request = "HEAD / HTTP/1.1\r\nConnection: close\r\nUser-Agent PostmanRuntime/7.28.4\r\nAccept: */*\r\nPostman-Token: 5501edf7-82e9-4b2f-9c08-a8e7d72387f4\r\nAccept-Encoding: gzip, deflate, br\r\nContent-Length: 0\r\n\r\n".encode("ISO-8859-1")

        print("REQUEST")
        print(get_request.decode("ISO-8859-1"))
        clientSocket.send(get_request)
        response = b''
        while True:
            partial_response = clientSocket.recv(8024)

            response += partial_response
            if len(partial_response) < 8024:
                break
        print("\nRESPONSE")
        print(response.decode("ISO-8859-1"))

    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return 

# for i in range (1, 7):
#     eval("test" + str(i) + "()")

def test7():
    print("Test7 - Target: Not Acceptable(Server could not handle given Encoding 'exi'.)")
    try:
        response = requests.get(SERVER_URL + "/", headers={'Accept-Encoding': 'exi,*;q=0' })
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test8():
    print("Test8 - Target: 404 Not Found(File not found)")
    try:
        response = requests.get(SERVER_URL + "/NotFound.txt")
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test9():
    print("Test9 - Target: 403 Forbidden(File donot have read permission)")
    try:
        response = requests.get(SERVER_URL + "/ReadLock.txt")
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test10():
    print("Test10 - Target: 400 Bad Request(Checksum error- Content-MD5 header)")
    try:
        response = requests.post(SERVER_URL + "/ReadLock.txt", headers = {"Content-MD5" : "11111111"}, data=json.dumps({"KEY" : "VALUE"}))
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test11():
    print("Test11 - Target: Simple GET request.")
    try:
        response = requests.get(SERVER_URL + "/")
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test12():
    print("Test12 - Target: Simple HEAD request.")
    try:
        response = requests.head(SERVER_URL + "/")
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test13():
    print("Test13 - Target: Simple POST request.")
    try:
        response = requests.post(SERVER_URL + "/post/def.txt", data = "Sample post request data.".encode("ISO-8859-1"))
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test14():
    print("Test14 - Target: Simple PUT request.")
    try:
        response = requests.put(SERVER_URL + "/put/def.txt", data = "Sample put request data.".encode("ISO-8859-1"))
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

def test15():
    print("Test15 - Target: Simple DELETE request.")
    try:
        response = requests.delete(SERVER_URL + "/delete/abc.txt")
        printRequestResponse(response)
    except Exception as e:
        print('Something unexpected occured!', e)
    finally:
        return

 