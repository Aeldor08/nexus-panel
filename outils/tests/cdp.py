"""Mini client CDP (websocket, bibliothèque standard). Usage : python cdp.py <port> <fichier.js> [url]
Ouvre l'url (option), évalue le JS (promesse attendue) et affiche le résultat en JSON."""

import base64, json, os, socket, struct, sys, time, urllib.request
from urllib.parse import urlparse


class WS:
    def __init__(self, url):
        u = urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port), timeout=600)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(
            (
                f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]

    def send(self, obj):
        data = json.dumps(obj).encode()
        h = bytearray([0x81])
        n = len(data)
        if n < 126:
            h.append(0x80 | n)
        elif n < 65536:
            h.append(0x80 | 126)
            h += struct.pack(">H", n)
        else:
            h.append(0x80 | 127)
            h += struct.pack(">Q", n)
        mask = os.urandom(4)
        h += mask
        self.s.sendall(bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk:
                raise ConnectionError("fermé")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            if b2 & 0x80:
                mask = self._read(4)
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(n)))
            else:
                data = self._read(n)
            msg += data
            if b1 & 0x80:
                break
        return json.loads(msg.decode("utf-8"))


class Page:
    def __init__(self, port=9333):
        pages = [p for p in json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json")) if p.get("type") == "page"]
        self.ws = WS(pages[0]["webSocketDebuggerUrl"])
        self.mid = 0

    def call(self, m, p=None):
        self.mid += 1
        self.ws.send({"id": self.mid, "method": m, "params": p or {}})
        while True:
            r = self.ws.recv()
            if r.get("id") == self.mid:
                return r.get("result", r)

    def ev(self, js):
        r = self.call("Runtime.evaluate", {"expression": js, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(json.dumps(r["exceptionDetails"])[:600])
        return r.get("result", {}).get("value")

    def go(self, url, wait=2.5):
        self.call("Page.navigate", {"url": url})
        time.sleep(wait)

    def shot(self, path, clip=None):
        p = {"format": "png", "captureBeyondViewport": bool(clip)}
        if clip:
            p["clip"] = {**clip, "scale": 1}
        open(path, "wb").write(base64.b64decode(self.call("Page.captureScreenshot", p)["data"]))


def main():
    port, js = int(sys.argv[1]), open(sys.argv[2], encoding="utf-8-sig").read()
    pg = Page(port)
    if len(sys.argv) > 3:
        pg.go(sys.argv[3])
    print(json.dumps(pg.ev(js), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
