#!/usr/bin/python
# (C) 2026 ghzserg https://github.com/ghzserg/zmod
# (C) 2026 Claude (Anthropic) — соавтор
#
# ff_orca — эмулятор HTTP API родного экрана FlashForge (AD5X, Creator 5/5 Pro)
# для Flash Studio / OrcaSlicer поверх Moonraker и zmod_color.
# Требует display: False в zmod_color.

import argparse
import base64
import configparser
import http.client
import json
import logging
import os
import re
import signal
import socket
import sys
import tempfile
import threading
import time
import uuid
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlencode, urlsplit

FFCONFIG = '/usr/data/firmwareRes/config/'
AD5X_JSON = '/opt/config/rw/Adventurer5M.json'
OS_RELEASE = '/etc/os-release'
DEFAULT_CONFIG = '/opt/config/mod_data/ff_orca.cfg'
DEFAULT_LOG = '/opt/config/mod_data/log/ff_orca.log'

MODELS = {
    'AD5X':        {'name': 'AD5X',          'pid': 0x0026, 'nozzle_count': 1, 'measure': '220X220X220'},
    'Creator5':    {'name': 'Creator 5',     'pid': 0x0028, 'nozzle_count': 4, 'measure': '256X256X256'},
    'Creator5Pro': {'name': 'Creator 5 Pro', 'pid': 0x0029, 'nozzle_count': 4, 'measure': '256X256X256'},
}
GCODE_EXT = ('.gcode', '.gco', '.g', '.3mf')
MAX_TOOLS = 98                  # как MAX_COLOR в zmod_color
MAX_JSON_BODY = 1024 * 1024
READ_CHUNK = 64 * 1024

log = logging.getLogger('ff_orca')

DEFAULTS = {
    'listen_host': '0.0.0.0',
    'listen_port': '8898',
    'moonraker_url': 'http://127.0.0.1:7125',
    'moonraker_api_key': '',
    'model': '',
    'serial_number': '',
    'check_code': '',
    'check_auth': 'true',
    'printer_name': '',
    'firmware_version': '',
    'pid': '',
    'nozzle_model': '',
    'nozzle_count': '',
    'measure': '',
    'location': '',
    'ip_addr': '',
    'mac_addr': '',
    'camera_url': '',
    'light_object': 'led',
    'fan_object': 'fan_generic FanM106',
    'light_on_gcode': 'LED_ON',
    'light_off_gcode': 'LED_OFF',
    'tmp_dir': '',
    'max_files': '100',
    'poll_interval': '1.0',
    'slow_poll_interval': '30',
    'print_timeout': '14400',
    'auto_clear': '10',             # через сколько секунд после конца печати статус ready (-1 = ждать «Очистить»)
    'log_file': DEFAULT_LOG,
    'log_level': 'INFO',
    'discovery': 'true',
    'discovery_flags': '0000',      # байты 144-145 ответа: 0000 = подключение без входа в аккаунт
}


# ---------------------------------------------------------------- утилиты

def read_json_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.loads(re.sub(r'/\*.*?\*/', '', f.read(), flags=re.DOTALL))


def read_ff_json(name):
    return read_json_file(FFCONFIG + name)


def to_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def norm_hex(color, default='FFFFFF'):
    s = str(color or '').strip().lstrip('#').upper()
    if len(s) == 8:
        s = s[:6]
    return s if re.fullmatch(r'[0-9A-F]{6}', s) else default


def as_list(value):
    if value is None or value == '':
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        txt = str(value).strip()
        try:
            items = json.loads(txt) if txt.startswith('[') else None
        except ValueError:
            items = None
        if not isinstance(items, list):
            items = re.split(r'[;,]', txt.strip('[]'))
    return [str(i).strip().strip('"\'').strip() if isinstance(i, str) else i for i in items]


def safe_filename(name):
    name = os.path.basename(str(name or '').replace('\\', '/'))
    name = re.sub(r'[\x00-\x1f"]', '', name).strip()
    return name


def detect_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))      # пакет не отправляется
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'
    finally:
        s.close()


def detect_mac():
    base = '/sys/class/net'
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return ''
    names = [n for n in ('wlan0', 'eth0') if n in names] + names
    for n in names:
        if n == 'lo':
            continue
        try:
            with open(os.path.join(base, n, 'address')) as f:
                mac = f.read().strip().upper()
        except OSError:
            continue
        if mac and mac != '00:00:00:00:00:00':
            return mac
    return ''


# ---------------------------------------------------------------- конфиг

class Config:
    def __init__(self, path):
        cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=('#',))
        cp.read_dict({'ff_orca': DEFAULTS})
        if path and os.path.exists(path):
            cp.read(path, encoding='utf-8')
        c = cp['ff_orca']
        self.path = path
        self.listen_host = c.get('listen_host')
        self.listen_port = c.getint('listen_port')
        self.moonraker_url = c.get('moonraker_url')
        self.moonraker_api_key = c.get('moonraker_api_key')
        self.check_auth = c.getboolean('check_auth')
        self.camera_url = c.get('camera_url')
        self.light_object = c.get('light_object').strip()
        self.fan_object = c.get('fan_object').strip()
        self.light_on_gcode = c.get('light_on_gcode').replace('\\n', '\n')
        self.light_off_gcode = c.get('light_off_gcode').replace('\\n', '\n')
        self.max_files = c.getint('max_files')
        self.poll_interval = c.getfloat('poll_interval')
        self.slow_poll_interval = c.getfloat('slow_poll_interval')
        self.print_timeout = c.getfloat('print_timeout')
        self.auto_clear = c.getfloat('auto_clear')
        self.log_file = c.get('log_file')
        self.log_level = c.get('log_level').upper()
        self.discovery = c.getboolean('discovery')
        self.discovery_flags = bytes.fromhex(c.get('discovery_flags').strip())[:2].rjust(2, b'\0')

        os_model, os_fw = '', ''
        try:
            with open(OS_RELEASE, 'r', encoding='utf-8') as f:
                m = re.search(r'^VERSION_CODENAME="?([^"\n]*)"?', f.read(), re.M)
            if m:
                parts = m.group(1).split()
                os_model, os_fw = (parts + ['', ''])[:2]
        except OSError:
            pass
        self.model = c.get('model').strip() or os_model or 'AD5X'
        prof = MODELS.get(self.model, MODELS['AD5X'])

        fw = {}
        if self.model == 'AD5X':
            try:
                g = read_json_file(AD5X_JSON).get('general', {})
                fw = {'serial': g.get('printerSerialNumber'), 'code': g.get('lanCode'),
                      'name': g.get('printerName'), 'location': g.get('localName'),
                      'nozzle': g.get('extruderTypeInfo')}
            except Exception as e:
                log.warning('%s: %s', AD5X_JSON, e)
        else:
            try:
                g = read_ff_json('general.json')
                fw = {'serial': g.get('serialNumber'), 'name': g.get('printerName'),
                      'location': g.get('localName'), 'nozzle': g.get('extruderTypeInfo')}
            except Exception as e:
                log.warning('%sgeneral.json: %s', FFCONFIG, e)
            try:
                fw['code'] = read_ff_json('network.json').get('lanModeCode')
            except Exception as e:
                log.warning('%snetwork.json: %s', FFCONFIG, e)

        def pick(key, *alts):
            v = c.get(key).strip()
            if v:
                return v
            return next((str(a) for a in alts if a not in (None, '')), '')

        self.serial_number = pick('serial_number', fw.get('serial'))
        self.check_code = pick('check_code', fw.get('code'))
        self.firmware_version = pick('firmware_version', os_fw, '1.0.0')
        self.printer_name = pick('printer_name', fw.get('name'), prof['name'])
        self.location = pick('location', fw.get('location'), 'Group A')
        self.nozzle_model = pick('nozzle_model', fw.get('nozzle'), '0.4mm')
        self.pid = to_int(pick('pid', prof['pid']), 0)
        self.nozzle_count = to_int(pick('nozzle_count', prof['nozzle_count']), 1)
        self.measure = pick('measure', prof['measure'])

        self.ip_addr = c.get('ip_addr').strip() or detect_ip()
        self.mac_addr = c.get('mac_addr').strip() or detect_mac()
        self.camera_url = self.camera_url.strip() or f'http://{self.ip_addr}:8080/?action=stream'

        tmp = c.get('tmp_dir').strip()
        if not tmp:
            tmp = '/usr/data/tmp' if os.path.isdir('/usr/data') else tempfile.gettempdir()
        os.makedirs(tmp, exist_ok=True)
        self.tmp_dir = tmp


# ---------------------------------------------------------------- Moonraker

class MoonrakerError(Exception):
    pass


class Moonraker:
    def __init__(self, url, api_key=''):
        p = urlsplit(url)
        self.host = p.hostname or '127.0.0.1'
        self.port = p.port or 80
        self.base = (p.path or '').rstrip('/')
        self.api_key = api_key

    def _headers(self):
        h = {}
        if self.api_key:
            h['X-Api-Key'] = self.api_key
        return h

    def _path(self, path, params=None):
        p = self.base + path
        if params:
            p += '?' + urlencode(params)
        return p

    def request(self, method, path, params=None, body=None, timeout=10.0, raw=False):
        headers = self._headers()
        data = None
        if body is not None:
            data = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            conn.request(method, self._path(path, params), body=data, headers=headers)
            resp = conn.getresponse()
            payload = resp.read()
        finally:
            conn.close()
        if raw:
            if resp.status != 200:
                raise MoonrakerError(f'HTTP {resp.status} {path}')
            return payload
        try:
            j = json.loads(payload.decode('utf-8'))
        except ValueError:
            raise MoonrakerError(f'HTTP {resp.status} {path}: {payload[:200]!r}')
        if resp.status != 200 or 'error' in j:
            err = j.get('error')
            msg = err.get('message') if isinstance(err, dict) else err
            raise MoonrakerError(f'{path}: {msg or resp.status}')
        return j.get('result')

    def get(self, path, params=None, timeout=10.0):
        return self.request('GET', path, params=params, timeout=timeout)

    def post(self, path, body=None, params=None, timeout=10.0):
        return self.request('POST', path, params=params, body=body, timeout=timeout)

    def get_raw(self, path, timeout=10.0):
        return self.request('GET', path, timeout=timeout, raw=True)

    def gcode(self, script, timeout=30.0):
        log.debug('gcode: %s', script.replace('\n', ' | '))
        return self.post('/printer/gcode/script', {'script': script}, timeout=timeout)

    def upload(self, local_path, filename, timeout=600.0):
        boundary = uuid.uuid4().hex
        fname = filename.replace('"', '')
        pre = (f'--{boundary}\r\n'
               f'Content-Disposition: form-data; name="root"\r\n\r\n'
               f'gcodes\r\n'
               f'--{boundary}\r\n'
               f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
               f'Content-Type: application/octet-stream\r\n\r\n').encode('utf-8')
        post = f'\r\n--{boundary}--\r\n'.encode('utf-8')
        size = os.path.getsize(local_path)

        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            conn.putrequest('POST', self._path('/server/files/upload'))
            for k, v in self._headers().items():
                conn.putheader(k, v)
            conn.putheader('Content-Type', f'multipart/form-data; boundary={boundary}')
            conn.putheader('Content-Length', str(len(pre) + size + len(post)))
            conn.endheaders()
            conn.send(pre)
            with open(local_path, 'rb') as f:
                while True:
                    chunk = f.read(READ_CHUNK)
                    if not chunk:
                        break
                    conn.send(chunk)
            conn.send(post)
            resp = conn.getresponse()
            payload = resp.read()
        finally:
            conn.close()
        try:
            j = json.loads(payload.decode('utf-8'))
        except ValueError:
            raise MoonrakerError(f'upload HTTP {resp.status}: {payload[:200]!r}')
        if resp.status not in (200, 201) or 'error' in j:
            err = j.get('error')
            msg = err.get('message') if isinstance(err, dict) else err
            raise MoonrakerError(f'upload: {msg or resp.status}')
        res = j.get('result', j)
        return (res.get('item') or {}).get('path') or fname


# ---------------------------------------------------------------- состояние

class State:
    OBJECTS = ['webhooks', 'print_stats', 'virtual_sdcard', 'heater_bed',
               'extruder', 'extruder1', 'extruder2', 'extruder3',
               'toolhead', 'gcode_move', 'fan', 'idle_timeout',
               'motion_report', 'zmod_color', 'pause_resume']

    def __init__(self, cfg, mr):
        self.cfg = cfg
        self.mr = mr
        self.lock = threading.Lock()
        self.status = {}
        self.online = False
        self.objects = None
        self.disk_free_gb = 0.0
        self.total_filament_m = 0.0
        self.total_print_min = 0
        self.camera_url = cfg.camera_url
        self.cur_meta_file = None
        self.cur_meta = {}
        self.light_state = False
        self.display_warned = False
        self._stop = threading.Event()
        self._last_slow = 0.0

    def start(self):
        threading.Thread(target=self._loop, name='poller', daemon=True).start()

    def stop(self):
        self._stop.set()

    def snapshot(self):
        with self.lock:
            return dict(self.status), self.online

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._poll()
            except Exception as e:
                with self.lock:
                    if self.online:
                        log.warning('Moonraker недоступен: %s', e)
                    self.online = False
                self.objects = None
                self._stop.wait(3.0)
                continue
            now = time.monotonic()
            if now - self._last_slow >= self.cfg.slow_poll_interval:
                self._last_slow = now
                self._slow_poll()
            self._stop.wait(self.cfg.poll_interval)

    def _poll(self):
        if self.objects is None:
            avail = set(self.mr.get('/printer/objects/list')['objects'])
            objs = [o for o in self.OBJECTS if o in avail]
            if self.cfg.light_object and self.cfg.light_object in avail:
                objs.append(self.cfg.light_object)
            if self.cfg.fan_object and self.cfg.fan_object in avail:
                objs.append(self.cfg.fan_object)
            if 'zmod_color' not in avail:
                log.warning('Объект zmod_color не найден в Klipper')
            self.objects = objs
            log.info('Опрашиваемые объекты: %s', ', '.join(objs))
        res = self.mr.post('/printer/objects/query',
                           {'objects': {o: None for o in self.objects}})
        status = res.get('status', {})
        with self.lock:
            if not self.online:
                log.info('Moonraker на связи')
            self.status = status
            self.online = True

        zc = status.get('zmod_color', {})
        if zc.get('display') and not self.display_warned:
            self.display_warned = True
            log.error('zmod_color: display=True. Установите display: False, '
                      'иначе возможна взаимная блокировка')

        fname = status.get('print_stats', {}).get('filename') or ''
        if fname != self.cur_meta_file:
            self.cur_meta_file = fname
            self.cur_meta = {}
            if fname:
                try:
                    self.cur_meta = self.mr.get('/server/files/metadata', {'filename': fname}) or {}
                except Exception as e:
                    log.debug('metadata %s: %s', fname, e)

    def _slow_poll(self):
        try:
            d = self.mr.get('/server/files/directory', {'path': 'gcodes', 'extended': 'false'})
            free = (d.get('disk_usage') or {}).get('free', 0)
            self.disk_free_gb = round(free / 1024 ** 3, 2)
        except Exception as e:
            log.debug('disk_usage: %s', e)
        try:
            t = self.mr.get('/server/history/totals').get('job_totals', {})
            self.total_filament_m = round(float(t.get('total_filament_used', 0)) / 1000.0, 2)
            self.total_print_min = int(float(t.get('total_print_time', 0)) / 60)
        except Exception as e:
            log.debug('history totals: %s', e)


# ---------------------------------------------------------------- multipart

class BodyReader:

    def __init__(self, rfile, length=None, chunked=False):
        self.rfile = rfile
        self.left = length or 0
        self.chunked = chunked
        self.chunk_left = 0
        self.done = False

    def read(self, n):
        if self.chunked:
            return self._read_chunked(n)
        if self.left <= 0:
            return b''
        data = self.rfile.read(min(n, self.left))
        if not data:
            self.left = 0
            return b''
        self.left -= len(data)
        return data

    def _read_chunked(self, n):
        if self.done:
            return b''
        if self.chunk_left == 0:
            line = self.rfile.readline(1024)
            try:
                size = int(line.split(b';')[0].strip() or b'0', 16)
            except ValueError:
                self.done = True
                return b''
            if size == 0:
                while True:
                    tr = self.rfile.readline(1024)
                    if tr in (b'\r\n', b'\n', b''):
                        break
                self.done = True
                return b''
            self.chunk_left = size
        data = self.rfile.read(min(n, self.chunk_left))
        if not data:
            self.done = True
            return b''
        self.chunk_left -= len(data)
        if self.chunk_left == 0:
            self.rfile.readline(1024)
        return data

    def drain(self):
        while self.read(READ_CHUNK):
            pass


def parse_multipart(reader, boundary, tmp_dir, max_field=MAX_JSON_BODY):
    """-> (fields {name: str}, files {name: (filename, path, size)})"""
    delim = b'\r\n--' + boundary
    keep = len(delim) - 1
    st = {'buf': b'\r\n', 'eof': False}
    fields, files = {}, {}

    def fill():
        if st['eof']:
            return False
        chunk = reader.read(READ_CHUNK)
        if not chunk:
            st['eof'] = True
            return False
        st['buf'] += chunk
        return True

    try:
        while True:
            i = st['buf'].find(delim)
            if i >= 0:
                st['buf'] = st['buf'][i + len(delim):]
                break
            st['buf'] = st['buf'][-keep:]
            if not fill():
                raise ValueError('multipart: boundary not found')

        while True:
            while len(st['buf']) < 2:
                if not fill():
                    raise ValueError('multipart: truncated')
            if st['buf'][:2] == b'--':
                break
            while True:
                j = st['buf'].find(b'\r\n')
                if j >= 0:
                    st['buf'] = st['buf'][j + 2:]
                    break
                if not fill():
                    raise ValueError('multipart: truncated')
            while True:
                if st['buf'].startswith(b'\r\n'):
                    raw_headers = b''
                    st['buf'] = st['buf'][2:]
                    break
                j = st['buf'].find(b'\r\n\r\n')
                if j >= 0:
                    raw_headers = st['buf'][:j]
                    st['buf'] = st['buf'][j + 4:]
                    break
                if len(st['buf']) > 16384:
                    raise ValueError('multipart: part headers too long')
                if not fill():
                    raise ValueError('multipart: truncated')

            hdrs = {}
            for line in raw_headers.decode('utf-8', 'replace').split('\r\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    hdrs[k.strip().lower()] = v.strip()
            disp = hdrs.get('content-disposition', '')
            m = re.search(r'\bname="([^"]*)"', disp) or re.search(r'\bname=([^;\s]+)', disp)
            name = m.group(1) if m else ''
            m = re.search(r'filename="([^"]*)"', disp) or re.search(r'filename=([^;\s]+)', disp)
            filename = m.group(1) if m else None

            out = None
            data = bytearray()
            size = 0
            path = None
            if filename is not None:
                fd, path = tempfile.mkstemp(dir=tmp_dir, prefix='ff_orca_', suffix='.part')
                out = os.fdopen(fd, 'wb')
                files[name] = (filename, path, 0)

            def write(b):
                if out is not None:
                    out.write(b)
                else:
                    data.extend(b)
                    if len(data) > max_field:
                        raise ValueError('multipart: field too large')
                return len(b)

            try:
                while True:
                    i = st['buf'].find(delim)
                    if i >= 0:
                        size += write(st['buf'][:i])
                        st['buf'] = st['buf'][i + len(delim):]
                        break
                    if len(st['buf']) > keep:
                        size += write(st['buf'][:-keep])
                        st['buf'] = st['buf'][-keep:]
                    if not fill():
                        raise ValueError('multipart: truncated')
            finally:
                if out is not None:
                    out.close()

            if filename is not None:
                files[name] = (filename, path, size)
            else:
                fields[name] = data.decode('utf-8', 'replace')
        reader.drain()
    except Exception:
        for _, p, _ in files.values():
            try:
                os.remove(p)
            except OSError:
                pass
        raise
    return fields, files


# ---------------------------------------------------------------- логика

def blank_png(size=1):
    def chunk(t, d):
        return len(d).to_bytes(4, 'big') + t + d + zlib.crc32(t + d).to_bytes(4, 'big')
    raw = (b'\0' + b'\0' * 4 * size) * size
    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', size.to_bytes(4, 'big') * 2 + bytes((8, 6, 0, 0, 0))) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def png_to_bmp(data):
    """PNG -> BMP 24 бит без альфы, байт-в-байт как /getThum родного экрана."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not png')
    pos, idat, w = 8, bytearray(), 0
    while pos < len(data):
        ln = int.from_bytes(data[pos:pos + 4], 'big')
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b'IHDR':
            w, h = int.from_bytes(chunk[0:4], 'big'), int.from_bytes(chunk[4:8], 'big')
            depth, ctype, interlace = chunk[8], chunk[9], chunk[12]
            if depth != 8 or interlace or ctype not in (0, 2, 4, 6):
                raise ValueError('unsupported png')
            bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'IEND':
            break
    if not w:
        raise ValueError('no IHDR')
    raw = zlib.decompress(bytes(idat))
    stride = w * bpp
    rows, prev, i = [], bytearray(stride), 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            if f == 1:
                line[x] = (line[x] + a) & 0xFF
            elif f == 2:
                line[x] = (line[x] + b) & 0xFF
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 0xFF
            elif f == 4:
                c = prev[x - bpp] if x >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
        rows.append(line)
        prev = line
    pad = (4 - (w * 3) % 4) % 4
    out = bytearray()
    for line in reversed(rows):                  # BMP хранит строки снизу вверх
        for x in range(w):
            px = line[x * bpp:(x + 1) * bpp]
            if bpp >= 3:
                r, g, b = px[0], px[1], px[2]
            else:
                r = g = b = px[0]
            out += bytes((b, g, r))
        out += b'\0' * pad
    hdr = b'BM' + (54 + len(out)).to_bytes(4, 'little') + b'\0\0\0\0' + (54).to_bytes(4, 'little')
    dib = (40).to_bytes(4, 'little') + w.to_bytes(4, 'little') + h.to_bytes(4, 'little') + \
        (1).to_bytes(2, 'little') + (24).to_bytes(2, 'little') + b'\0' * 4 + \
        len(out).to_bytes(4, 'little') + (6969).to_bytes(4, 'little') + (2835).to_bytes(4, 'little') + b'\0' * 8
    return hdr + dib + bytes(out)


class ApiError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.mr = Moonraker(cfg.moonraker_url, cfg.moonraker_api_key)
        self.state = State(cfg, self.mr)
        self.job_lock = threading.Lock()
        self.job_active = False
        self.last_error = ''
        self.meta_lock = threading.Lock()
        self.meta_cache = {}
        self.job_file = ''
        self.job_bound = None
        self.pending = None             # (pause|resume|cancel, время)
        self.done_since = None

    def check_auth(self, serial, code):
        if not self.cfg.check_auth:
            return True
        return str(serial or '') == self.cfg.serial_number and str(code or '') == self.cfg.check_code

    def run_async(self, script, timeout=60.0):
        def worker():
            try:
                self.mr.gcode(script, timeout=timeout)
            except Exception as e:
                self.last_error = str(e)
                log.error('G-code "%s": %s', script.replace('\n', ' | '), e)
        threading.Thread(target=worker, daemon=True).start()

    def _zmod(self):
        st, online = self.state.snapshot()
        if not online:
            raise ApiError('Moonraker offline')
        zc = st.get('zmod_color')
        if zc is None:
            raise ApiError('zmod_color not loaded')
        if zc.get('display'):
            raise ApiError('zmod_color display=True, set display: False')
        return st, zc

    def printer_status(self, st, online):
        if not online:
            return 'error'
        wh = st.get('webhooks', {}).get('state')
        if wh and wh != 'ready':
            return 'error'
        ps = st.get('print_stats', {}).get('state', 'standby')
        if ps not in ('complete', 'cancelled'):
            self.done_since = None
        paused = ps == 'paused' or (ps == 'printing' and st.get('pause_resume', {}).get('is_paused'))
        pend = self.pending
        if pend and time.monotonic() - pend[1] > 300:
            pend = self.pending = None
        if pend:
            if pend[0] == 'pause' and not paused and ps == 'printing':
                return 'pausing'
            if pend[0] == 'resume' and paused:
                return 'heating'
            if pend[0] == 'cancel' and ps in ('printing', 'paused'):
                return 'canceling'
            self.pending = None
        if paused:
            return 'pause'
        if ps == 'printing':
            return 'printing'
        if ps == 'error':
            return 'error'
        if self.job_active:
            return 'printing'               # родной экран сразу после старта отдаёт printing
        if st.get('idle_timeout', {}).get('state') == 'Printing':
            return 'busy'
        if ps not in ('complete', 'cancelled'):
            return 'ready'
        if self.done_since is None:
            self.done_since = time.monotonic()
        if 0 <= self.cfg.auto_clear <= time.monotonic() - self.done_since:
            return 'ready'                  # нет экрана, где нажать «Очистить»: сбрасываем сами
        return 'completed' if ps == 'complete' else 'cancel'

    def fan_speed(self, st):
        obj = st.get(self.cfg.fan_object) or st.get('fan') or {}
        return float(obj.get('speed', obj.get('value')) or 0)

    def light_on(self, st):
        obj = st.get(self.cfg.light_object) if self.cfg.light_object else None
        if isinstance(obj, dict):
            if 'value' in obj:
                return float(obj.get('value') or 0) > 0
            if 'color_data' in obj:
                return any(any(float(c) > 0 for c in px) for px in obj.get('color_data') or [])
        return self.state.light_state

    def build_detail(self):
        st, online = self.state.snapshot()
        cfg = self.cfg
        ps = st.get('print_stats', {})
        sd = st.get('virtual_sdcard', {})
        th = st.get('toolhead', {})
        gm = st.get('gcode_move', {})
        bed = st.get('heater_bed', {})
        zc = st.get('zmod_color', {})
        ext = st.get(th.get('extruder') or 'extruder', {}) or st.get('extruder', {})

        progress = float(sd.get('progress') or 0.0)
        duration = float(ps.get('print_duration') or 0.0)
        est_total = float(self.state.cur_meta.get('estimated_time') or 0.0)
        if est_total > 0:
            left = max(0.0, est_total - duration)
        elif progress > 0.001:
            left = max(0.0, duration / progress - duration)
        else:
            left = 0.0
        info = ps.get('info') or {}
        fname = self.display_file(ps)
        thumb = f'http://{cfg.ip_addr}:{cfg.listen_port}/getThum' if fname else ''
        status = self.printer_status(st, online)
        if status == 'ready':
            fname = thumb = ''
        working = status not in ('ready', 'error')
        finfo = self.file_info(fname) if fname and working else {}
        homing = gm.get('homing_origin') or [0, 0, 0, 0]
        velocity = st.get('motion_report', {}).get('live_velocity') or 0.0

        slots = []
        for s in zc.get('slots', []):
            slots.append({
                'slotId': to_int(s.get('ID'), 0),
                'hasFilament': bool(s.get('hasFilament', True)),
                'materialName': s.get('Material', '?'),
                'materialColor': '#' + norm_hex(s.get('HEX')),
            })
        active = to_int(zc.get('active_tool_id'), -1)
        cur_slot = active + 1 if active >= 0 else 0
        indep = slots[active] if 0 <= active < len(slots) else (slots[0] if slots else None)
        pos = th.get('position') or [0, 0, 0]
        if 'xyz' not in str(th.get('homed_axes') or ''):
            pos = [10000.0, 10000.0, 10000.0]

        return {
            'autoShutdown': 'close',
            'autoShutdownTime': 30,
            'camera': 1 if self.state.camera_url else 0,
            'cameraStreamUrl': self.state.camera_url or '',
            'chamberFanSpeed': 0,
            'chamberTargetTemp': 0,
            'chamberTemp': 0,
            'clearFanStatus': 'close',
            'coolingFanLeftSpeed': 0,
            'coolingFanSpeed': int(round(self.fan_speed(st) * 100)),
            'cumulativeFilament': self.state.total_filament_m,
            'cumulativePrintTime': self.state.total_print_min,
            'coordinate': [round(float(v), 3) for v in pos[:3]],
            'currentPrintSpeed': int(round(float(velocity))),
            'doorStatus': 'close',
            'errorCode': '',
            'estimatedLeftLen': 0,
            'estimatedLeftWeight': 0.0,
            'estimatedRightLen': 0,
            'estimatedRightWeight': float(finfo.get('weight') or 0.0),
            'estimatedTime': float(int(left)),
            'externalFanStatus': 'close',
            'extrudeCtrl': 1,
            'fillAmount': finfo.get('fill', 0),
            'firmwareVersion': cfg.firmware_version,
            'flashRegisterCode': '',
            'hasLeftFilament': False,
            'hasMatlStation': bool(slots),
            'hasRightFilament': any(x['hasFilament'] for x in slots),
            'indepMatlInfo': {'materialColor': indep['materialColor'] if indep else '#FFFFFF',
                              'materialName': indep['materialName'] if indep else '?',
                              'stateAction': 4 if working else 0, 'stateStep': 0},
            'internalFanStatus': 'close',
            'ipAddr': cfg.ip_addr,
            'leftFilamentType': '',
            'leftTargetTemp': 0,
            'leftTemp': 0,
            'lightStatus': 'open' if self.light_on(st) else 'close',
            'location': cfg.location,
            'macAddr': cfg.mac_addr,
            'matlStationInfo': {
                'currentLoadSlot': cur_slot,
                'currentSlot': cur_slot,
                'slotCnt': to_int(zc.get('color_limit'), len(slots)),
                'slotInfos': slots,
                'stateAction': 4 if working else 0,
                'stateStep': 0,
            },
            'measure': cfg.measure,
            'moveCtrl': 1,
            'name': cfg.printer_name,
            'nozzleCnt': cfg.nozzle_count,
            'nozzleModel': cfg.nozzle_model,
            'nozzleStyle': 0,
            'pid': cfg.pid,
            'platTargetTemp': round(float(bed.get('target') or 0), 1),
            'platTemp': round(float(bed.get('temperature') or 0), 1),
            'polarRegisterCode': '',
            'printDuration': int(duration),
            'printFileName': fname,
            'printFileThumbUrl': thumb,
            'printLayer': to_int(info.get('current_layer'), 0),
            'printProgress': round(progress, 4),
            'printSpeedAdjust': float(int(round(float(gm.get('speed_factor') or 1.0) * 100))) if working else 0.0,
            'remainingDiskSpace': self.state.disk_free_gb,
            'rightFilamentType': '',
            'rightTargetTemp': round(float(ext.get('target') or 0), 1),
            'rightTemp': round(float(ext.get('temperature') or 0), 1),
            'status': status,
            'targetPrintLayer': to_int(info.get('total_layer'), 0),
            'tvoc': 0,
            'zAxisCompensation': round(float(homing[2] if len(homing) > 2 else 0), 3),
        }

    def api_product(self, body):
        return {'product': {
            'chamberTempCtrlState': 0,
            'externalFanCtrlState': 0,
            'internalFanCtrlState': 0,
            'lightCtrlState': 1 if (self.cfg.light_on_gcode or self.cfg.light_object) else 0,
            'nozzleTempCtrlState': 1,
            'platformTempCtrlState': 1,
        }}

    def api_detail(self, body):
        return {'detail': self.build_detail()}

    def api_control(self, body):
        payload = body.get('payload') or {}
        cmd = payload.get('cmd', '')
        args = payload.get('args') or {}
        log.info('control: %s %s', cmd, json.dumps(args, ensure_ascii=False))

        if cmd in ('ms_cmd', 'ipdMs_cmd'):
            # Загрузка (action=0) / выгрузка (action=1); ipdMs_cmd — внешняя катушка (слот 0, AD5X)
            st, zc = self._zmod()
            slot = to_int(args.get('slot'), 0) if cmd == 'ms_cmd' else 0
            napr = to_int(args.get('action'), -1)
            ad5x = self.cfg.model == 'AD5X'
            if napr not in (0, 1) or not (0 if ad5x else 1) <= slot <= to_int(zc.get('color_limit'), 4):
                raise ApiError(f'Invalid slot {slot} or action {napr}')
            self.run_async(f'IN_ZCOLOR SLOT={slot} NAPR={napr}' if ad5x
                           else f'_T_IN_ZCOLOR SLOT={slot} NAPR={napr} HIDE=1', timeout=600)
            return {}

        if cmd in ('msConfig_cmd', 'ipdMsConfig_cmd'):
            st, zc = self._zmod()
            slot = to_int(args.get('slot'), 0) if cmd == 'msConfig_cmd' else 0
            limit = to_int(zc.get('color_limit'), 4)
            if not (0 if self.cfg.model == 'AD5X' else 1) <= slot <= limit:
                raise ApiError(f'Invalid slot {slot}')
            mt = str(args.get('mt') or '').strip().upper()
            valid = [t.upper() for t in zc.get('valid_types', [])]
            if mt and valid and mt not in valid:
                raise ApiError(f'Invalid material {mt}')
            parts = [f'CHANGE_ZCOLOR SLOT={slot}', 'HIDE=1']
            if args.get('rgb'):
                parts.append(f'HEX={norm_hex(args.get("rgb"))}')
            if mt:
                parts.append(f'TYPE={mt}')
            if len(parts) == 2:
                raise ApiError('Specify rgb or mt')
            self.run_async(' '.join(parts))
            return {}

        if cmd == 'jobCtl_cmd':
            action = str(args.get('action') or '').lower()
            path = {'pause': '/printer/print/pause',
                    'continue': '/printer/print/resume',
                    'resume': '/printer/print/resume',
                    'cancel': '/printer/print/cancel'}.get(action)
            if not path:
                raise ApiError(f'Unknown action {action}')

            self.pending = ('resume' if action == 'continue' else action, time.monotonic())

            def worker():
                try:
                    self.mr.post(path, timeout=60)
                except Exception as e:
                    self.pending = None
                    self.last_error = str(e)
                    log.error('%s: %s', path, e)
            threading.Thread(target=worker, daemon=True).start()
            return {}

        if cmd == 'lightControl_cmd':
            on = str(args.get('status') or '').lower() == 'open'
            script = self.cfg.light_on_gcode if on else self.cfg.light_off_gcode
            if not script:
                raise ApiError('Light control not configured')
            self.state.light_state = on
            self.run_async(script)
            return {}

        if cmd == 'printerCtl_cmd':
            st, _ = self.state.snapshot()
            gm = st.get('gcode_move', {})
            script = []
            if 'speed' in args:
                v = to_int(args.get('speed'), 100)
                if v != int(round(float(gm.get('speed_factor') or 1.0) * 100)) and 10 <= v <= 500:
                    script.append(f'M220 S{v}')
            if 'coolingFan' in args:
                v = max(0, min(100, to_int(args.get('coolingFan'), 0)))
                cur = int(round(self.fan_speed(st) * 100))
                if v != cur:
                    script.append(f'M106 S{int(round(v * 2.55))}')
            if 'zAxisCompensation' in args:
                try:
                    v = float(args.get('zAxisCompensation'))
                    homing = gm.get('homing_origin') or [0, 0, 0]
                    if abs(v - float(homing[2])) > 0.0005:
                        script.append(f'SET_GCODE_OFFSET Z={v:.3f}')
                except (TypeError, ValueError):
                    pass
            if script:
                self.run_async('\n'.join(script))
            return {}

        if cmd == 'temperatureCtl_cmd':
            script = []
            if 'platform' in args:
                script.append(f'M140 S{float(args["platform"]):.1f}')
            if 'leftJet' in args:
                script.append(f'M104 S{float(args["leftJet"]):.1f}')
            if script:
                self.run_async('\n'.join(script))
            return {}

        if cmd == 'stateCtrl_cmd':
            if str(args.get('action') or '') == 'setClearPlatform':
                self.job_file, self.job_bound = '', None
                self.run_async('SDCARD_RESET_FILE')
            return {}

        if cmd in ('circulateCtl_cmd', 'streamCtrl_cmd'):
            return {}

        raise ApiError(f'Unsupported command {cmd}')

    def display_file(self, ps):
        """.3mf, запущенный через сервис, вместо извлечённого zmod G-code."""
        ps_fn = ps.get('filename') or ''
        if self.job_file:
            if self.job_bound is None and ps_fn and ps.get('state') in ('printing', 'paused'):
                self.job_bound = ps_fn
            if self.job_bound is not None and ps_fn and ps_fn != self.job_bound:
                self.job_file, self.job_bound = '', None
        return self.job_file or ps_fn

    def file_info(self, path, modified=None):
        with self.meta_lock:
            c = self.meta_cache.get(path)
            if c and (modified is None or c[0] == modified):
                return c[1]
        info = {'tools': [], 'printingTime': 0, 'weight': 0.0, 'fill': 0}
        try:
            meta = self.mr.get('/server/files/metadata', {'filename': path}) or {}
            colors = as_list(meta.get('filament_colors') or meta.get('extruder_colors'))
            types = as_list(meta.get('filament_type'))
            weights = as_list(meta.get('filament_weights'))
            for i, color in enumerate(colors):
                info['tools'].append({
                    'filamentWeight': round(float(weights[i]), 2) if i < len(weights) else 0,
                    'materialColor': '#' + norm_hex(color),
                    'materialName': (types[i] if i < len(types) else (types[0] if types else 'PLA')) or 'PLA',
                    'slotId': 0,
                    'toolId': i,
                })
            info['printingTime'] = int(float(meta.get('estimated_time') or 0))
            info['weight'] = round(float(meta.get('filament_weight_total') or 0), 2)
        except Exception as e:
            log.debug('file_info %s: %s', path, e)
        with self.meta_lock:
            self.meta_cache[path] = (modified, info)
        return info

    def api_gcode_list(self, body):
        files = self.mr.get('/server/files/list', {'root': 'gcodes'}) or []
        files = [f for f in files if str(f.get('path', '')).lower().endswith(GCODE_EXT)]
        files.sort(key=lambda f: f.get('modified', 0), reverse=True)
        files = files[:self.cfg.max_files]
        names, details = [], []
        for f in files:
            path = f['path']
            info = self.file_info(path, f.get('modified'))
            names.append(path)
            details.append({
                'gcodeFileName': path,
                'gcodeToolCnt': len(info['tools']),
                'gcodeToolDatas': info['tools'],
                'printingTime': info['printingTime'],
                'totalFilamentWeight': info['weight'],
                'useMatlStation': True,
            })
        return {'gcodeList': names, 'gcodeListDetail': details}

    def thumbnail(self, fname):
        thumbs = self.mr.get('/server/files/thumbnails', {'filename': fname}) or []
        if not thumbs:
            return None
        best = max(thumbs, key=lambda t: (t.get('width') or 0) * (t.get('height') or 0))
        tp = best.get('thumbnail_path')
        if not tp:
            return None
        return self.mr.get_raw('/server/files/gcodes/' + quote(tp))

    def current_thumb_bmp(self):
        st, _ = self.state.snapshot()
        fname = self.display_file(st.get('print_stats', {}))
        if not fname:
            return None, ''
        png = self.thumbnail(fname)
        if not png:
            return None, fname
        try:
            return png_to_bmp(png), fname
        except Exception as e:
            log.debug('png_to_bmp %s: %s', fname, e)
            return png, fname

    def api_gcode_thumb(self, body):
        fname = body.get('fileName') or ''
        if not fname:
            raise ApiError('fileName required')
        data = self.thumbnail(fname)
        if not data:
            # code != 0 Flash Studio считает обрывом связи: отдаём пустое превью
            log.info('Нет превью для %s, отдаю пустое', fname)
            data = blank_png()
        return {'imageData': base64.b64encode(data).decode('ascii')}

    @staticmethod
    def parse_mappings(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        s = str(value).strip()
        for cand in (s, None):
            try:
                if cand is None:
                    cand = base64.b64decode(s + '=' * (-len(s) % 4)).decode('utf-8')
                v = json.loads(cand)
                if isinstance(v, list):
                    return v
            except Exception:
                continue
        log.warning('Не удалось разобрать materialMappings: %r', s[:200])
        return []

    def start_print(self, fname, leveling, autopa, use_ms, mappings, tool_cnt):
        st, zc = self._zmod()
        ps = st.get('print_stats', {}).get('state')
        with self.job_lock:
            if self.job_active or ps in ('printing', 'paused'):
                raise ApiError('Printer busy')
            self.job_active = True
        try:
            limit = to_int(zc.get('color_limit'), 4)
            parts = ['PRINT_ZCOLOR', f'FILENAME="{fname.replace(chr(34), "")}"',
                     f'LEVELING={1 if leveling else 0}', f'AUTOPA={1 if autopa else 0}']
            tmap = {}
            if use_ms or mappings:          # «Включить IFS» игнорируем: сопоставление есть всегда
                for m in mappings:
                    tid = to_int(m.get('toolId'), -1)
                    sid = to_int(m.get('slotId'), 0)
                    if 0 <= tid < MAX_TOOLS and 1 <= sid <= limit:
                        tmap[tid] = sid
            if tmap:
                need = max(max(tmap) + 1, to_int(tool_cnt, 0))
                if need > limit:
                    parts.append(f'ALLOWED_TOOL_COUNT={need}')
                parts += [f'T{t}={s}' for t, s in sorted(tmap.items())]
            script = ' '.join(parts)
        except Exception:
            self.job_active = False
            raise
        self.job_file, self.job_bound = fname, None
        log.info('Старт печати: %s', script)
        threading.Thread(target=self._run_print, args=(script,), daemon=True).start()

    def _run_print(self, script):
        try:
            self.mr.gcode(script, timeout=self.cfg.print_timeout)
            self.last_error = ''
        except Exception as e:
            self.last_error = str(e)
            log.error('PRINT_ZCOLOR: %s', e)
        finally:
            with self.job_lock:
                self.job_active = False

    def api_print_gcode(self, body):
        fname = str(body.get('fileName') or '').strip()
        if not fname:
            raise ApiError('fileName required')
        try:
            self.mr.get('/server/files/metadata', {'filename': fname})
        except MoonrakerError:
            raise ApiError(f'File not found: {fname}')
        self.start_print(fname,
                         to_bool(body.get('levelingBeforePrint')),
                         to_bool(body.get('flowCalibration')),
                         to_bool(body.get('useMatlStation'), True),
                         self.parse_mappings(body.get('materialMappings')),
                         body.get('gcodeToolCnt'))
        return {}

    def upload(self, tmp_path, fname, opts):
        log.info('Загрузка %s (%d байт) в Moonraker', fname, os.path.getsize(tmp_path))
        try:
            path = self.mr.upload(tmp_path, fname)
        except Exception as e:
            raise ApiError(f'Upload to Moonraker failed: {e}')
        with self.meta_lock:
            self.meta_cache.pop(path, None)
        log.info('Файл сохранён: %s', path)
        if to_bool(opts.get('printNow')):
            self.start_print(path,
                             to_bool(opts.get('levelingBeforePrint')),
                             to_bool(opts.get('flowCalibration')),
                             to_bool(opts.get('useMatlStation'), True),
                             self.parse_mappings(opts.get('materialMappings')),
                             opts.get('gcodeToolCnt'))
        return {}


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'ff_orca'
    sys_version = ''

    ROUTES = {
        '/product': 'api_product',
        '/detail': 'api_detail',
        '/control': 'api_control',
        '/gcodeList': 'api_gcode_list',
        '/gcodeThumb': 'api_gcode_thumb',
        '/printGcode': 'api_print_gcode',
    }

    @property
    def app(self):
        return self.server.app

    def log_message(self, fmt, *args):
        log.debug('%s %s', self.client_address[0], fmt % args)

    def _send(self, status, data, ctype):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        self.wfile.write(data)

    def _send_json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                   'application/json')

    def _reply(self, extra=None, code=0, message='Success'):
        res = {'code': code, 'message': message}
        if extra:
            res.update(extra)
        self._send_json(res)

    def _reader(self):
        te = (self.headers.get('Transfer-Encoding') or '').lower()
        length = to_int(self.headers.get('Content-Length'), 0)
        return BodyReader(self.rfile, length, 'chunked' in te)

    def _read_json(self):
        reader = self._reader()
        data = bytearray()
        while True:
            chunk = reader.read(READ_CHUNK)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > MAX_JSON_BODY:
                self.close_connection = True
                raise ApiError('Request too large')
        if not data.strip():
            return {}
        try:
            body = json.loads(data.decode('utf-8'))
        except ValueError:
            raise ApiError('Invalid JSON')
        return body if isinstance(body, dict) else {}

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path.rstrip('/') == '/getThum':
            try:
                data, fname = self.app.current_thumb_bmp()
            except Exception as e:
                log.debug('getThum: %s', e)
                data, fname = None, ''
            if data:
                ctype = 'image/bmp' if data[:2] == b'BM' else 'image/png'
                self.send_response(200)
                self.send_header('Content-Disposition', 'inline; filename=' +
                                 quote(os.path.splitext(os.path.basename(fname))[0]) + '.bmp')
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.close_connection = True
                self.wfile.write(data)
            else:
                self._send(404, b'not found', 'text/plain')
            return
        if url.path.rstrip('/') == '/thumb':
            fname = (parse_qs(url.query).get('fileName') or [''])[0]
            try:
                data = self.app.thumbnail(fname) if fname else None
            except Exception as e:
                log.debug('thumb %s: %s', fname, e)
                data = None
            if data:
                self._send(200, data, 'image/png')
            else:
                self._send(404, b'not found', 'text/plain')
            return
        self._send(404, b'not found', 'text/plain')

    def do_POST(self):
        path = urlsplit(self.path).path.rstrip('/')
        try:
            if path == '/uploadGcode':
                self._upload()
                return
            name = self.ROUTES.get(path)
            body = self._read_json()
            if not name:
                self._send(404, b'not found', 'text/plain')
                return
            if not self.app.check_auth(body.get('serialNumber'), body.get('checkCode')):
                log.warning('%s %s: неверные serialNumber/checkCode', self.client_address[0], path)
                self._reply(code=1, message='Authentication failed')
                return
            self._reply(getattr(self.app, name)(body))
        except ApiError as e:
            log.warning('%s: %s', path, e)
            self._reply(code=e.code, message=str(e))
        except Exception as e:
            log.exception('%s: %s', path, e)
            self.close_connection = True
            self._reply(code=1, message=f'Internal error: {e}')

    def _upload(self):
        h = self.headers
        ctype = h.get('Content-Type') or ''
        m = re.search(r'boundary=(?:"([^"]+)"|([^;\s]+))', ctype)
        if not m:
            self.close_connection = True
            raise ApiError('multipart boundary required')
        boundary = (m.group(1) or m.group(2)).encode('latin-1')

        if h.get('serialNumber') is not None and not self.app.check_auth(h.get('serialNumber'), h.get('checkCode')):
            self.close_connection = True
            raise ApiError('Authentication failed')

        reader = self._reader()
        try:
            fields, files = parse_multipart(reader, boundary, self.app.cfg.tmp_dir)
        except ValueError as e:
            self.close_connection = True
            raise ApiError(str(e))

        tmp_paths = [p for _, p, _ in files.values()]
        try:
            def opt(key):
                v = h.get(key)
                return v if v is not None else fields.get(key)

            if h.get('serialNumber') is None and not self.app.check_auth(opt('serialNumber'), opt('checkCode')):
                raise ApiError('Authentication failed')

            part = files.get('gcodeFile') or (next(iter(files.values())) if files else None)
            if not part:
                raise ApiError('gcodeFile required')
            filename, tmp_path, size = part
            fname = safe_filename(opt('fileName') or filename)
            if not fname:
                raise ApiError('Empty file name')
            expected = to_int(opt('fileSize'), -1)
            if expected >= 0 and expected != size:
                raise ApiError(f'File size mismatch: {size} != {expected}')

            opts = {k: opt(k) for k in ('printNow', 'levelingBeforePrint', 'flowCalibration',
                                        'useMatlStation', 'gcodeToolCnt', 'materialMappings')}
            log.info('uploadGcode: %s %s', fname, json.dumps(opts, ensure_ascii=False))
            self._reply(self.app.upload(tmp_path, fname, opts))
        finally:
            for p in tmp_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass


class Discovery:
    """Ответ на UDP-поиск FlashForge.
    Запрос 8 байт: IPv4 клиента, порт ответа (BE), 2 байта флагов.
    Ответ 280 байт (BE):
      0   name[132]
      132 u16 TCP-порт команд (8899)
      134 u16 vendor 0x2B71
      136 u16 pid (AD5X=0x26, 5M=0x23)
      138 u16 0
      140 u16 0x5A02
      142 u16 HTTP-порт (8898)
      144 u16 0x0100 у AD5X, 0x0000 у 5M
      146 serial[128]
      274 u16 0x5A02, u16 0x0100, u16 0
    """
    MCAST_GROUP = '225.0.0.9'
    PORTS = (19000, 48899)

    def __init__(self, cfg):
        self.cfg = cfg
        self.socks = []
        self._stop = threading.Event()

    def packet(self):
        cfg = self.cfg
        b = bytearray(280)
        name = cfg.printer_name.encode('utf-8')[:131]
        b[0:len(name)] = name
        b[132:146] = bytes.fromhex('22c3' '2b71') + cfg.pid.to_bytes(2, 'big') + \
            bytes.fromhex('0000' '5a02') + cfg.listen_port.to_bytes(2, 'big') + cfg.discovery_flags
        sn = cfg.serial_number.encode('ascii', 'ignore')[:127]
        b[146:146 + len(sn)] = sn
        b[274:280] = bytes.fromhex('5a0201000000')
        return bytes(b)

    def start(self):
        for port in self.PORTS:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('', port))
                if port == 19000:
                    mreq = socket.inet_aton(self.MCAST_GROUP) + socket.inet_aton('0.0.0.0')
                    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            except OSError as e:
                log.error('Discovery: порт UDP %d недоступен: %s', port, e)
                s.close()
                continue
            s.settimeout(1.0)
            self.socks.append(s)
            threading.Thread(target=self._loop, args=(s, port), name=f'disc{port}', daemon=True).start()
            log.info('Discovery: слушаю UDP %d', port)

    def stop(self):
        self._stop.set()

    def _loop(self, s, port):
        while not self._stop.is_set():
            try:
                data, addr = s.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(data) < 6:
                continue
            ip = socket.inet_ntoa(data[0:4])
            rport = int.from_bytes(data[4:6], 'big')
            if ip == '0.0.0.0' or not rport:
                ip, rport = addr
            try:
                s.sendto(self.packet(), (ip, rport))
                log.debug('Discovery: %s:%d -> ответ на %s:%d', addr[0], port, ip, rport)
            except OSError as e:
                log.debug('Discovery: ответ %s:%d: %s', ip, rport, e)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, app):
        super().__init__(addr, Handler)
        self.app = app


# ---------------------------------------------------------------- запуск

def setup_logging(cfg, debug):
    level = logging.DEBUG if debug else getattr(logging, cfg.log_level, logging.INFO)
    fmt = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s',
                            '%Y-%m-%d %H:%M:%S')
    if cfg.log_file:
        os.makedirs(os.path.dirname(cfg.log_file) or '.', exist_ok=True)
    handler = logging.FileHandler(cfg.log_file, encoding='utf-8') if cfg.log_file \
        else logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def dump_native(cfg, url):
    p = urlsplit(url if '://' in url else f'http://{url}')
    port = p.port or 8898
    for api in ('/product', '/detail', '/gcodeList'):
        conn = http.client.HTTPConnection(p.hostname, port, timeout=15)
        body = json.dumps({'serialNumber': cfg.serial_number, 'checkCode': cfg.check_code})
        try:
            conn.request('POST', api, body=body, headers={'Content-Type': 'application/json'})
            resp = conn.getresponse()
            data = resp.read().decode('utf-8', 'replace')
        except Exception as e:
            data = f'ERROR: {e}'
        finally:
            conn.close()
        print(f'===== {api}')
        try:
            print(json.dumps(json.loads(data), indent=2, ensure_ascii=False))
        except ValueError:
            print(data)


def main():
    ap = argparse.ArgumentParser(description='FlashForge native screen API emulator for Moonraker')
    ap.add_argument('-c', '--config', default=DEFAULT_CONFIG)
    ap.add_argument('--debug', action='store_true')
    ap.add_argument('--dump', metavar='HOST[:PORT]',
                    help='вывести ответы настоящего экрана и выйти')
    args = ap.parse_args()

    cfg = Config(args.config)
    if args.dump:
        dump_native(cfg, args.dump)
        return 0

    setup_logging(cfg, args.debug)
    if not cfg.serial_number or not cfg.check_code:
        log.warning('serialNumber/checkCode не заданы')
    log.info('ff_orca: %s:%d -> %s, ip=%s, model=%s, fw=%s, name=%s, sn=%s, pid=%d',
             cfg.listen_host, cfg.listen_port, cfg.moonraker_url, cfg.ip_addr,
             cfg.model, cfg.firmware_version, cfg.printer_name, cfg.serial_number, cfg.pid)

    app = App(cfg)
    try:
        server = Server((cfg.listen_host, cfg.listen_port), app)
    except OSError as e:
        log.error('Не удалось открыть порт %d: %s (занят родным экраном?)', cfg.listen_port, e)
        return 1

    app.state.start()
    disc = Discovery(cfg)
    if cfg.discovery:
        disc.start()

    def stop(signum, frame):
        log.info('Остановка (сигнал %d)', signum)
        app.state.stop()
        disc.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
