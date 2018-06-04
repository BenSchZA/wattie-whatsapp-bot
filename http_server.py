import http.server


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        # Send the html message
        self.wfile.write(b"Hello World! Service is up.")
        return


def run(server_class=http.server.HTTPServer):
    server_address = ('', 8001)
    try:
        httpd = server_class(server_address, Handler)
        httpd.serve_forever()
        return httpd
    except OSError:
        pass
