#!/usr/bin/python
# (C) 2026 ghzserg https://github.com/ghzserg/zmod
#
# zmod_detail - опрос /detail родного экрана AD5X раз в секунду.
# В /tmp/detail.txt пишет {hasMatlStation, slotInfos} только при изменении,
# если экран не отвечает - удаляет файл. Читает zmod_color (наличие прутка).

import os
import sys
import json
import time
import subprocess
import urllib.request

FFCONFIG = '/usr/prog/config/Adventurer5M.json'
DETAIL = '/tmp/detail.txt'
LOG = '/opt/config/mod_data/log/zmod_detail.log'
LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'
MSG = {
    'start': ('Старт', 'Start'),
    'ok':    ('Родной экран отвечает', 'Native screen is responding'),
    'fail':  ('Родной экран не отвечает: {}', 'Native screen is not responding: {}'),
}

def log(key, *args):
    text = MSG[key][0 if LANG == 'ru' else 1].format(*args)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}\n")

def rotate():
    for i in range(4, 0, -1):
        if os.path.exists(f'{LOG}.{i}'):
            os.replace(f'{LOG}.{i}', f'{LOG}.{i + 1}')
    if os.path.exists(LOG):
        os.replace(LOG, f'{LOG}.1')

def printer_ip():
    for iface in ('wlan0', 'eth0'):
        try:
            out = subprocess.run(['ip', '-br', 'addr', 'show', iface], capture_output=True, text=True, timeout=5)
            if out.returncode == 0:
                return out.stdout.split()[2].split('/')[0]
        except Exception:
            pass
    return None

def fetch(ip):
    with open(FFCONFIG, 'r') as f:
        general = json.load(f)['general']
    body = json.dumps({'serialNumber': general['printerSerialNumber'], 'checkCode': general['lanCode']}).encode()
    req = urllib.request.Request(f'http://{ip}:8898/detail', data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3) as resp:
        detail = json.load(resp)['detail']
    return {'hasMatlStation': detail.get('hasMatlStation', 'matlStationInfo' in detail),
            'slotInfos': detail.get('matlStationInfo', {}).get('slotInfos', [])}

def main():
    rotate()
    log('start')
    if os.path.exists(DETAIL):
        os.remove(DETAIL)
    prev, ip, online = None, None, None
    while True:
        try:
            ip = ip or printer_ip()
            cur = fetch(ip)
            if online is not True:
                log('ok')
                online = True
            if cur != prev:
                tmp = DETAIL + '.tmp'
                with open(tmp, 'w') as f:
                    json.dump(cur, f)
                os.replace(tmp, DETAIL)
                prev = cur
        except Exception as e:
            if online is not False:
                log('fail', e)
                online = False
            if prev is not None:
                os.remove(DETAIL)
            prev, ip = None, None
        time.sleep(1)

if __name__ == '__main__':
    main()
