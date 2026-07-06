#!/usr/bin/env python3
import socket
import threading

import webview

from server import app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(port: int) -> None:
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def main() -> None:
    port = find_free_port()
    server_thread = threading.Thread(
        target=start_server,
        args=(port,),
        daemon=True,
    )
    server_thread.start()

    webview.create_window(
        "Korean Study",
        f"http://127.0.0.1:{port}",
        width=920,
        height=720,
        min_size=(640, 480),
        resizable=True,
        text_select=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()