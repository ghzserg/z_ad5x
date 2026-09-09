#!/usr/bin/python
# (C) 2026 ghzserg https://github.com/ghzserg/zmod

import http.server
import socketserver
import time
import struct
import urllib.parse
import io
import os
import sys
from PIL import Image

PORT = 8010

USE_AD5X = '-ad5x1' in sys.argv

EVENT_FORMAT = 'IIHHi' if USE_AD5X else 'LLHHl'
TOUCH_DEV = '/dev/input/event3' if USE_AD5X else '/dev/input/event2'
FB_SIZE = (800, 480) if USE_AD5X else (480, 800)

def send_event_raw(f, type_, code, value):
    t = time.time()
    sec = int(t)
    usec = int((t - sec) * 1000000)
    f.write(struct.pack(EVENT_FORMAT, sec, usec, type_, code, value))

def send_touch_event(x, y):
    try:
        t = time.time()
        sec = int(t)
        usec = int((t - sec) * 1000000)

        with open(TOUCH_DEV, 'wb') as f:
            if USE_AD5X:
                send_event_raw(f, 1, 330, 1)   # EV_KEY, BTN_TOUCH, 1
                send_event_raw(f, 3, 0, x)     # EV_ABS, ABS_X, x
                send_event_raw(f, 3, 1, y)     # EV_ABS, ABS_Y, y
                send_event_raw(f, 3, 24, 57)   # EV_ABS, ABS_PRESSURE, 57
                send_event_raw(f, 0, 0, 0)     # EV_SYN, SYN_REPORT, 0
                f.flush()

                time.sleep(0.12)

                send_event_raw(f, 1, 330, 0)   # EV_KEY, BTN_TOUCH, 0
                send_event_raw(f, 3, 24, 0)    # EV_ABS, ABS_PRESSURE, 0
                send_event_raw(f, 0, 0, 0)     # EV_SYN, SYN_REPORT, 0
                f.flush()
            else:
                t = time.time()
                sec = int(t)
                usec = int((t - sec) * 1000000)
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 1, 330, 1))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 3, 53, x))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 3, 54, y))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 3, 48, 18))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 3, 50, 18))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 3, 57, 0))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 0, 2, 0))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 0, 0, 0))
                f.flush()

                time.sleep(0.07)

                t = time.time()
                sec = int(t)
                usec = int((t - sec) * 1000000)
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 1, 330, 0))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 0, 2, 0))
                f.write(struct.pack(EVENT_FORMAT, sec, usec, 0, 0, 0))
                f.flush()
    except Exception:
        pass

class StreamHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        # 1. Корневая HTML страница (Страница HTTP для Fluidd)
        if self.path == '/' or self.path == '/index.html' or self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    html, body {
                        margin: 0;
                        padding: 0;
                        width: 100%;
                        height: 100%;
                        background: transparent;
                        overflow: hidden;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }
                    .container {
                        position: relative;
                        width: 100%;
                        height: 100%;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }
                    img {
                        width: 100%;
                        height: 100%;
                        object-fit: contain;
                        cursor: pointer;
                        user-select: none;
                        -webkit-user-drag: none;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <img id="screen" src="/screen/streams" onclick="sendClick(event)">
                </div>
                <script>
                    function sendClick(event) {
                        const img = document.getElementById('screen');
                        const rect = img.getBoundingClientRect();

                        const imgRatio = 800 / 480;
                        const containerRatio = rect.width / rect.height;

                        let actualWidth = rect.width;
                        let actualHeight = rect.height;
                        let offsetX = 0;
                        let offsetY = 0;

                        if (containerRatio > imgRatio) {
                            actualWidth = rect.height * imgRatio;
                            offsetX = (rect.width - actualWidth) / 2;
                        } else {
                            actualHeight = rect.width / imgRatio;
                            offsetY = (rect.height - actualHeight) / 2;
                        }

                        const clickX = event.clientX - rect.left - offsetX;
                        const clickY = event.clientY - rect.top - offsetY;

                        const x = Math.round(clickX * (800 / actualWidth));
                        const y = Math.round(clickY * (480 / actualHeight));

                        if (x >= 0 && x <= 800 && y >= 0 && y <= 480) {
                            fetch(`/screen/click?x=${x}&y=${y}`);
                        }
                    }
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            return

        # 2. Обработка кликов
        elif self.path.startswith('/click'):
            parsed_url = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed_url.query)

            if 'x' in params and 'y' in params:
                x_web = int(params['x'][0])
                y_web = int(params['y'][0])

                if USE_AD5X:
                    x_touch = int((x_web * 65536 + 4184520) / 76390)
                    y_touch = int((y_web * 65536 + 6959128) / 95216)
                else:
                    x_touch = y_web
                    y_touch = 800 - x_web
                    x_touch = max(0, min(480, x_touch))
                    y_touch = max(0, min(800, y_touch))

                send_touch_event(x_touch, y_touch)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            return

        # 3. Видеопоток экрана (Стабильный MJPEG)
        elif self.path == '/streams':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                last_fb = b''
                last_frame = b''

                memory_buffer = io.BytesIO()

                with open('/dev/fb0', 'rb') as fb_file:
                    while True:
                        fb_file.seek(0)
                        fb = fb_file.read()

                        if fb == last_fb and last_frame:
                            frame = last_frame
                        else:
                            img = Image.frombytes('RGBA', FB_SIZE, fb, 'raw', 'BGRA')
                            if not USE_AD5X:
                                img = img.transpose(Image.ROTATE_270)
                            img = img.convert('RGB')

                            memory_buffer.seek(0)
                            memory_buffer.truncate(0)

                            img.save(memory_buffer, format='JPEG', quality=60)
                            frame = memory_buffer.getvalue()

                            last_fb = fb
                            last_frame = frame

                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-type', 'image/jpeg')
                        self.send_header('Content-length', str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')

                        time.sleep(0.2) # ~5 FPS
            except Exception:
                pass
            return

        # 4. Одиночный Snapshot
        elif self.path == '/snapshot':
            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            try:
                fb = open('/dev/fb0', 'rb').read()
                img = Image.frombytes('RGBA', FB_SIZE, fb, 'raw', 'BGRA')
                if not USE_AD5X:
                    img = img.transpose(Image.ROTATE_270)
                img = img.convert('RGB')
                img.save(self.wfile, format='JPEG', quality=60)
            except Exception:
                pass
            return

        else:
            self.send_response(404)
            self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == '__main__':
    if not os.access(TOUCH_DEV, os.W_OK):
        os.system(f"chmod 666 {TOUCH_DEV}")

    server = ThreadedHTTPServer(('0.0.0.0', PORT), StreamHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
