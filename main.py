import socket
from _thread import *

SERVER_PORT = 8001
MAX_CONN = 100
MAX_REQ = 50
MAX_URI_LENGTH = 500
MAX_HEADER_LENGTH = 500
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]

req_count = 0

def can_server_handle_req():
    if(req_count < MAX_REQ):
        return True
    return False

def can_server_handle_uri(uri_len):
    if uri_len < MAX_URI_LENGTH:
        return True
    return False

def can_server_handle_method(method):
    if(method in SUPPORTED_METHODS):
        return True
    return False

def can_server_handle_header(header_len):
    if(header_len < MAX_HEADER_LENGTH):
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
    
    if(not can_server_handle_uri(len(req_uri))):
        response = generate_error_response(414, "URI Too Long", "Requested uri is too long to handle to server.")
        return response
    
    if(not can_server_handle_method(req_method)):
        response = generate_error_response(501, "Method Not Implemented", "Requested method is not implemented at server side or server could not support requested method.")
        return response
    
    headers = header_lines[1:]
    header_dict = {}
    for single_header in headers:
        single_header = single_header.split(":", 1)
        if len(single_header) != 2:
            # TODO cross check response code
            response = generate_error_response(400, "Bad Request", "Header format is incorrect.")
            return response
        if(not can_server_handle_header(len(single_header[1]))):
            response = generate_error_response(431, "Request header fields too large", "Requested header field is too large to handle to server.")
            return response
        # TODO check for supported 
        single_header[0] = single_header[0].strip()
        single_header[1] = single_header[1].strip()
        
        header_dict[single_header[0]] = single_header[1]
        print(single_header)

    return header_dict

    

def new_thread(client_conn, client_addr):
    req = b''
    while True:
        partial_request = client_conn.recv(30)
        req += partial_request
        if len(partial_request) < 30:
            break

    parse_request(req.decode())

    


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
        if(can_server_handle_req()):
            start_new_thread(new_thread, (client_conn, client_addr))
        else:
            response = generate_error_response(503, "Service Unavailable")

    listening_socket.close()

if __name__ == '__main__':
    main()