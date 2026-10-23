"""Small real Uvicorn server fixture for HTTP contract tests."""
import socket

import uvicorn


class HTTPServer:
    def __init__(self, address, app):
        self.socket = socket.socket()
        self.socket.bind(address)
        self.socket.listen(128)
        self.server_port = self.socket.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(app, log_level="error"))

    def serve_forever(self):
        self.server.run(sockets=[self.socket])

    def shutdown(self):
        self.server.should_exit = True

    def server_close(self):
        self.socket.close()
