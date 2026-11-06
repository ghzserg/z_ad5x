# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
# Эмуляция AFC (ArmoredTurtle/AFC-Klipper-Add-On) поверх zmod_color:
# панель AFC и диалог выбора lane перед печатью во Fluidd/Mainsail.
# Статус - только zmod_color.get_status() (slots, active_tool_id), карта T->слот - FILE_CONFIG.
# Общий для AD5X и C5Pro; команды загрузки/выгрузки задаются в [zmod_afc].

import os
import json
import queue
import logging
import threading
import requests
from .zmod_color import atomic_write, FILE_CONFIG

UNIT = 'IFS'            # юнит; при нескольких IFS (IFS Jacker) - IFS_1, IFS_2... по 4 lane
SPOOLMAN = 'http://127.0.0.1:7125/server/spoolman/proxy'
DEFAULT_WEIGHT = 1000
MSG = {
    'material': ('Материал', 'Material'),
    'cancel':   ('Отмена', 'Cancel'),
    'no_lane':  ('Нет загруженной lane', 'No lane loaded'),
    'no_card':  ('Метка {} не привязана к катушке в Spoolman', 'Tag {} is not linked to a spool in Spoolman'),
}

class _Obj:
    def __init__(self, fn):
        self.get_status = fn

class zmod_afc:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.load = config.get('load', 'IN_ZCOLOR SLOT={slot} NAPR=0')
        self.unload = config.get('unload', 'IN_ZCOLOR SLOT={slot} NAPR=1')
        self.enabled = False    # переменная мода afc, читается на klippy:ready
        self.n = 0
        self.slots = {}         # слот -> {'Material', 'HEX', 'hasFilament'}
        self.map = []           # индекс - инструмент, значение - слот
        self.active = 0         # активный слот (1-based), 0 - нет
        self.palette = []       # палитра C5Pro (HEX), на AD5X пусто
        self.types = []         # типы пластика для выбора (без скрытых)
        self.last = 0.          # время последнего пересчёта
        self.map_mtime = -1
        self.state = 'Idle'     # Loading / Unloading во время операции
        self.error = None       # текст последней ошибки загрузки/выгрузки
        self.spools = {}        # слот -> spool_id Spoolman
        self.spool_sig = {}     # слот -> ((HEX, тип) катушки, armed): смена слота мимо катушки сбрасывает её
        self.prev_has = {}      # слот -> наличие прутка на прошлом пересчёте
        self.active_spool = None  # spool_id, переданный Moonraker как активный
        self.native_q = None    # очередь /control родного экрана (отдельный поток, по порядку)
        self.pending = {}       # слот -> (HEX, тип, до): записано, но zmod_color ещё не видит
        for cmd in ('SET_COLOR', 'SET_MATERIAL', 'SET_MAP', 'SET_WEIGHT', 'CHANGE_TOOL', 'TOOL_UNLOAD', 'LANE_UNLOAD'):
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))
        for cmd in ('AFC_RESET', 'RESET_FAILURE', 'AFC_CLEAR_MESSAGE'):
            self.gcode.register_command(cmd, self.cmd_AFC_RESET)
        self.gcode.register_command('SET_SPOOL_ID', self.cmd_SET_SPOOL_ID)
        self.printer.register_event_handler('klippy:ready', self._ready)

    def _ready(self):
        self.color = self.printer.lookup_object('zmod_color')
        self.save_variables = self.printer.lookup_object('save_variables', None)
        self.enabled = self.save_variables is not None and self.save_variables.allVariables.get('afc', 0) == 1
        if not self.enabled:
            return
        self.reactor = self.printer.get_reactor()
        self.webhooks = self.printer.lookup_object('webhooks')
        v = self.save_variables.allVariables
        self.spools = {int(k[14:]): sid for k, sid in v.items() if k.startswith('afc_spool_lane') and sid}
        self.printer.add_object('AFC', _Obj(self._afc_status))
        self.objs = set()
        # IFS Jacker сообщает число каналов через ~30 с после старта: регистрируем сохранённое
        # число lane сразу, чтобы морда увидела их без перезагрузки страницы
        self._resize(max(self.color.color_limit, v.get('afc_lanes', 0)))
        self._resize(self.color.color_limit)

    # Число lane = zmod_color.color_limit (IFS Jacker меняет его на лету). Объекты только
    # добавляются; лишние не попадают в списки AFC и юнитов
    def _resize(self, n, save=False):
        self.n = n
        for name in self._units():
            if name not in self.objs:
                self.objs.add(name)
                self.printer.add_object(f'AFC_{UNIT} {name}', _Obj(lambda e, name=name: {
                    'lanes': self._lanes(name), 'extruders': [], 'hubs': [], 'buffers': []}))
        for i in range(1, n + 1):
            if i not in self.objs:
                self.objs.add(i)
                self.printer.add_object(f'AFC_lane lane{i}', _Obj(lambda e, i=i: self._lane_status(e, i)))
        if save and n != self.save_variables.allVariables.get('afc_lanes', 0):
            self._save('afc_lanes', n)

    # Пересчёт не чаще раза в секунду; команды сбрасывают self.last для немедленного обновления
    def _refresh(self, eventtime):
        if eventtime - self.last < 1.:
            return
        self.last = eventtime
        st = self.color.get_status(eventtime)
        if self.color.color_limit != self.n:
            self._resize(self.color.color_limit, save=True)
        self.slots = {int(s['ID']): s for s in st['slots']}
        for i, (h, m, until) in list(self.pending.items()):
            s = self.slots.get(i)
            if s is None or (s['HEX'], s['Material']) == (h, m) or eventtime > until:
                del self.pending[i]
            else:
                s.update(HEX=h, Material=m)
        self.palette = st.get('palette', [])    # C5Pro: цвет хранится индексом палитры
        self.types = [t for t in st['valid_types'][:-1] if t not in st.get('hidden_types', [])]
        self.active = st.get('active_tool_id', -1) + 1
        try:
            mtime = os.stat(FILE_CONFIG).st_mtime
        except OSError:
            mtime = None
        if mtime != self.map_mtime:
            self.map_mtime = mtime
            try:
                with open(FILE_CONFIG, 'r') as f:
                    self.map = [int(x) for x in json.load(f)]
            except Exception:
                self.map = []
            if not self.map:
                self.map = list(range(1, self.n + 1))
        self._check_spools()

    # Сброс катушки: слот перезаправили (пруток вынут) или сменили цвет/тип мимо катушки.
    # Активная катушка Moonraker (учёт расхода) - катушка активной lane.
    def _check_spools(self):
        for i in list(self.spools):
            s = self.slots.get(i, {})
            cur, has = (s.get('HEX'), s.get('Material')), bool(s.get('hasFilament'))
            want, armed = self.spool_sig.get(i, (None, False))
            if not armed:
                if want is None or cur == want:     # ждём, пока слот примет цвет/тип катушки
                    self.spool_sig[i] = (cur, True)
            elif cur != want or (self.prev_has.get(i) and not has):
                self._set_spool(i, 0)
            self.prev_has[i] = has
        sid = self.spools.get(self.active, 0)
        if (self.spools or self.active_spool) and sid != self.active_spool:
            try:
                self.webhooks.call_remote_method('spoolman_set_active_spool', spool_id=sid or None)
                self.active_spool = sid
            except Exception:
                pass    # Moonraker ещё не подключён или нет Spoolman

    def _save(self, name, value):
        self.reactor.register_callback(lambda e: self.gcode.run_script(f'SAVE_VARIABLE VARIABLE={name} VALUE={value}'))

    def _set_spool(self, i, sid):
        if sid:
            self.spools[i] = sid
            self._fetch_spool(i, sid)
        else:
            self.spools.pop(i, None)
        self.spool_sig.pop(i, None)
        self._save(f'afc_spool_lane{i}', sid)
        self.last = 0.

    # Цвет и тип катушки из Spoolman -> слот (HTTP в потоке, запись - в reactor)
    # Запрос к Spoolman через прокси Moonraker (только из потока)
    @staticmethod
    def _spoolman(method, path, body=None):
        req = {'request_method': method, 'path': path}
        if body is not None:
            req['body'] = body
        r = requests.post(SPOOLMAN, json=req, timeout=10)
        r.raise_for_status()
        res = r.json()['result']
        return res.get('response', res) if isinstance(res, dict) and 'response' in res else res

    def _fetch_spool(self, i, sid):
        def worker():
            try:
                fil = self._spoolman('GET', f'/v1/spool/{sid}')['filament']
                hexc, mat = (fil.get('color_hex') or '').upper(), (fil.get('material') or '').upper()
            except Exception as e:
                logging.info(f'zmod_afc: spoolman spool {sid}: {e}')
                return
            self.reactor.register_async_callback(lambda e: self._apply_spool(i, sid, hexc, mat))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_spool(self, i, sid, hexc, mat):
        if self.spools.get(i) != sid:
            return
        types = sorted(self.color.valid_types[:-1], key=len, reverse=True)
        mat = mat if mat in types else next((t for t in types if t in mat), None)   # PLA+ -> PLA
        try:
            self.spool_sig[i] = (self._write(i, hexc or None, mat), False)
        except Exception as e:
            logging.info(f'zmod_afc: spool {sid} -> lane{i}: {e}')

    def _t(self, key):
        return MSG[key][0 if self.color.lang == 'ru' else 1]

    def _weight(self, i):
        return self.save_variables.allVariables.get(f'afc_weight_lane{i}', 0) or DEFAULT_WEIGHT

    def _units(self):
        return [UNIT] if self.n <= 4 else [f'{UNIT}_{u + 1}' for u in range((self.n + 3) // 4)]

    def _unit(self, i):
        return UNIT if self.n <= 4 else f'{UNIT}_{(i + 3) // 4}'

    def _lanes(self, unit=None):
        return [f'lane{i}' for i in range(1, self.n + 1) if unit is None or self._unit(i) == unit]

    def _afc_status(self, eventtime):
        self._refresh(eventtime)
        lane = f'lane{self.active}' if self.active else None
        return {'current_load': lane, 'current_lane': lane, 'next_lane': None,
                'current_state': 'Error' if self.error else self.state,
                'current_toolchange': 0, 'number_of_toolchanges': 0, 'spoolman': None,
                'td1_present': False, 'lane_data_enabled': False, 'error_state': self.error is not None,
                'bypass_state': False, 'quiet_mode': False, 'position_saved': False,
                'extruders': [], 'hubs': [], 'units': [f'{UNIT} {u}' for u in self._units()], 'lanes': self._lanes(),
                'buffers': [], 'led_state': False,
                'message': {'message': self.error, 'type': 'error' if self.error else None}}

    def _lane_status(self, eventtime, i):
        self._refresh(eventtime)
        s = self.slots.get(i, {})
        has = bool(s.get('hasFilament'))
        tooled = self.active == i
        mat = s.get('Material', '?')
        return {'name': f'lane{i}', 'unit': self._unit(i), 'hub': None, 'extruder': None,
                'buffer': None, 'buffer_status': None, 'lane': i,
                'map': [f'T{t}' for t, slot in enumerate(self.map) if slot == i],
                'load': has, 'prep': has, 'tool_loaded': tooled, 'loaded_to_hub': tooled,
                'material': None if mat in ('', '?') else mat, 'spool_id': self.spools.get(i),
                'color': '#' + (s.get('HEX') or 'FFFFFF'), 'weight': self._weight(i),
                'extruder_temp': None, 'runout_lane': None, 'dist_hub': 0, 'filament_status_led': '',
                'filament_status': 'In Tool' if tooled else 'Ready' if has else 'Not Ready',
                'status': 'Tooled' if tooled else 'Loaded' if has else 'None'}

    def _slot(self, gcmd, current=False):
        lane = gcmd.get('LANE', None)
        if lane is None and current:   # TOOL_UNLOAD без LANE - текущая lane (HelixScreen)
            self._refresh(self.printer.get_reactor().monotonic())
            if not self.active:
                raise gcmd.error(f"AFC: {self._t('no_lane')}")
            return self.active
        lane = lane or ''
        i = int(lane[4:]) if lane.lower().startswith('lane') and lane[4:].isdigit() else 0
        if not 1 <= i <= self.n:
            raise gcmd.error(f'AFC: unknown lane {lane}')
        return i

    def _set(self, gcmd, hexc=None, mat=None):
        self._refresh(self.printer.get_reactor().monotonic())
        self._write(self._slot(gcmd), hexc, mat)

    def _write(self, i, hexc=None, mat=None):
        s = self.slots.get(i, {})
        hexc = self._snap((hexc or s.get('HEX') or 'FFFFFF').lstrip('#').upper())
        mat = (mat or s.get('Material') or 'PLA').upper()
        c = self.color
        if mat not in c.valid_types[:-1]:
            raise self.printer.command_error(f"AFC: {mat}? {', '.join(c.valid_types[:-1])}")
        if c.display:
            self._native(i, mat, hexc)
        else:
            code, resp = c.set_printer_data_detail(i, mat, f'#{hexc}')
            if code != 200:
                raise self.printer.command_error(f'AFC: {resp}')
        s.update(HEX=hexc, Material=mat)   # SET_COLOR и SET_MATERIAL идут одним скриптом
        self.slots[i] = s
        self.pending[i] = (hexc, mat, self.reactor.monotonic() + 10.)
        self.last = 0.
        return hexc, mat

    # Родной экран: HTTP /control не в reactor (до 60 с при зависшем экране), а в своём потоке.
    # Очередь сохраняет порядок (SET_COLOR, затем SET_MATERIAL), ошибка - в message AFC
    def _native(self, i, mat, hexc):
        if self.native_q is None:
            self.native_q = queue.Queue()
            threading.Thread(target=self._native_worker, daemon=True).start()
        self.native_q.put((i, mat, hexc))

    def _native_worker(self):
        while True:
            i, mat, hexc = self.native_q.get()
            try:
                code, resp = self.color.zsend_post_request('/control', payload={
                    'cmd': 'msConfig_cmd', 'args': {'slot': i, 'mt': mat, 'rgb': f'#{hexc}'}})
            except Exception as e:
                code, resp = None, e
            if code != 200:
                self.reactor.register_async_callback(lambda e, err=f'lane{i}: {resp}': self._native_error(err))

    def _native_error(self, err):
        self.error = err
        self.gcode.respond_info(f'AFC: {err}')

    # Ближайший цвет палитры (C5Pro хранит индекс, цвет вне палитры стал бы белым)
    def _snap(self, hexc):
        if not self.palette or hexc in self.palette:
            return hexc
        lab = lambda h: self.color.rgb_to_lab(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        l1 = lab(hexc)
        return min(self.palette, key=lambda h: self.color.delta_e76(*l1, *lab(h)))

    def cmd_SET_COLOR(self, gcmd):
        self._set(gcmd, hexc=gcmd.get('COLOR'))

    # Точное имя - сразу, иначе окно выбора из подходящих (или всех) типов
    def cmd_SET_MATERIAL(self, gcmd):
        self._refresh(self.printer.get_reactor().monotonic())
        mat = gcmd.get('MATERIAL', '').strip().upper()
        if not mat or mat in self.types:
            gcmd.respond_raw("// action:prompt_end")
            return self._set(gcmd, mat=mat or None)
        i = self._slot(gcmd)
        types = [t for t in self.types if mat in t] or self.types
        gcmd.respond_raw("// action:prompt_end")
        gcmd.respond_raw(f"// action:prompt_begin {self._t('material')} lane{i}")
        gcmd.respond_raw("// action:prompt_button_group_start")
        for n, t in enumerate(types):
            if n and n % 4 == 0:
                gcmd.respond_raw("// action:prompt_button_group_end")
                gcmd.respond_raw("// action:prompt_button_group_start")
            gcmd.respond_raw(f"// action:prompt_button {t}|SET_MATERIAL LANE=lane{i} MATERIAL={t}|primary")
        gcmd.respond_raw("// action:prompt_button_group_end")
        gcmd.respond_raw(f"// action:prompt_footer_button {self._t('cancel')}|RESPOND TYPE=command MSG=action:prompt_end")
        gcmd.respond_raw("// action:prompt_show")

    # NFC-метка: катушка с UID в доп. поле card_uids (HEX через запятую, пишут приложения SpoolLink)
    def _card(self, i, uid):
        def worker():
            try:
                found = next((sp['id'] for sp in self._spoolman('GET', '/v1/spool')
                              if uid in json.loads(sp.get('extra', {}).get('card_uids', '""')).upper().split(',')), 0)
            except Exception as e:
                logging.info(f'zmod_afc: spoolman card {uid}: {e}')
                return
            self.reactor.register_async_callback(lambda e: self._set_spool(i, found) if found
                                                 else self.gcode.respond_info(f"AFC: {self._t('no_card').format(uid)}"))
        threading.Thread(target=worker, daemon=True).start()

    # SET_SPOOL_ID LANE= SPOOL_ID= (пусто или 0 - снять катушку) или CARD_UID= (найти по метке)
    def cmd_SET_SPOOL_ID(self, gcmd):
        i = self._slot(gcmd)
        sid = gcmd.get('SPOOL_ID', '').strip()
        sid = int(sid) if sid.isdigit() else 0
        uid = gcmd.get('CARD_UID', '').strip().upper()
        if uid:
            return self._card(i, uid)
        self._set_spool(i, sid)

    def cmd_SET_WEIGHT(self, gcmd):
        i = self._slot(gcmd)
        weight = max(0, int(gcmd.get_float('WEIGHT', 0.)))   # 0 - вернуть вес по умолчанию
        self.gcode.run_script_from_command(f'SAVE_VARIABLE VARIABLE=afc_weight_lane{i} VALUE={weight}')

    def cmd_SET_MAP(self, gcmd):
        i = self._slot(gcmd)
        tool = gcmd.get('MAP').upper()
        if not (tool.startswith('T') and tool[1:].isdigit()):
            raise gcmd.error(f'AFC: bad MAP {tool}')
        t = int(tool[1:])
        m = self.map + [(k % self.n) + 1 for k in range(len(self.map), t + 1)]
        m[t] = i
        atomic_write(FILE_CONFIG, json.dumps(m, indent=2))
        self.map = m
        self.last = 0.

    # Загрузка/выгрузка: current_state на время операции, ошибка - в error_state/message
    def _run(self, gcmd, template, state, current=False):
        i = self._slot(gcmd, current)
        self.state, self.error = state, None
        try:
            self.gcode.run_script_from_command(template.format(slot=i, tool=i - 1))
        except self.printer.command_error as e:
            self.error = f'lane{i}: {e}'
            raise
        finally:
            self.state = 'Idle'
            self.last = 0.

    def cmd_CHANGE_TOOL(self, gcmd):
        self._run(gcmd, self.load, 'Loading')

    def cmd_TOOL_UNLOAD(self, gcmd):
        self._run(gcmd, self.unload, 'Unloading', current=True)

    def cmd_LANE_UNLOAD(self, gcmd):
        self._run(gcmd, self.unload, 'Unloading')

    def cmd_AFC_RESET(self, gcmd):
        self.error = None

def load_config(config):
    return zmod_afc(config)
