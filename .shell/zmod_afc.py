# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
# Эмуляция AFC (ArmoredTurtle/AFC-Klipper-Add-On) поверх zmod_color:
# панель AFC и диалог выбора lane перед печатью во Fluidd/Mainsail.
# Статус - только zmod_color.get_status() (slots, active_tool_id), карта T->слот - FILE_CONFIG.
# Общий для AD5X и C5Pro; команды загрузки/выгрузки задаются в [zmod_afc].

import os
import json
from .zmod_color import atomic_write, FILE_CONFIG

UNIT = 'IFS'
DEFAULT_WEIGHT = 1000
MSG = {
    'material': ('Материал', 'Material'),
    'cancel':   ('Отмена', 'Cancel'),
    'no_lane':  ('Нет загруженной lane', 'No lane loaded'),
}

class _Obj:
    def __init__(self, fn):
        self.get_status = fn

class zmod_afc:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.prompt = config.getboolean('prompt', False)  # показывать ли окно Z-Mod перед печатью
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
        for cmd in ('SET_COLOR', 'SET_MATERIAL', 'SET_MAP', 'SET_WEIGHT', 'CHANGE_TOOL', 'TOOL_UNLOAD', 'LANE_UNLOAD'):
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))
        for cmd in ('AFC_RESET', 'RESET_FAILURE', 'AFC_CLEAR_MESSAGE'):
            self.gcode.register_command(cmd, self.cmd_AFC_RESET)
        self.gcode.register_command('SET_SPOOL_ID', lambda gcmd: None)  # шлёт диалог филамента, не нужен
        self.printer.register_event_handler('klippy:ready', self._ready)

    def _ready(self):
        self.color = self.printer.lookup_object('zmod_color')
        self.save_variables = self.printer.lookup_object('save_variables', None)
        self.enabled = self.save_variables is not None and self.save_variables.allVariables.get('afc', 0) == 1
        if not self.enabled:
            return
        self.n = self.color.color_limit
        self.printer.add_object('AFC', _Obj(self._afc_status))
        self.printer.add_object(f'AFC_{UNIT} {UNIT}', _Obj(
            lambda e: {'lanes': self._lanes(), 'extruders': [], 'hubs': [], 'buffers': []}))
        for i in range(1, self.n + 1):
            self.printer.add_object(f'AFC_lane lane{i}', _Obj(lambda e, i=i: self._lane_status(e, i)))

    # Пересчёт не чаще раза в секунду; команды сбрасывают self.last для немедленного обновления
    def _refresh(self, eventtime):
        if eventtime - self.last < 1.:
            return
        self.last = eventtime
        st = self.color.get_status(eventtime)
        self.slots = {int(s['ID']): s for s in st['slots']}
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

    def _t(self, key):
        return MSG[key][0 if self.color.lang == 'ru' else 1]

    def _weight(self, i):
        return self.save_variables.allVariables.get(f'afc_weight_lane{i}', 0) or DEFAULT_WEIGHT

    def _lanes(self):
        return [f'lane{i}' for i in range(1, self.n + 1)]

    def _afc_status(self, eventtime):
        self._refresh(eventtime)
        lane = f'lane{self.active}' if self.active else None
        return {'current_load': lane, 'current_lane': lane, 'next_lane': None,
                'current_state': 'Error' if self.error else self.state,
                'current_toolchange': 0, 'number_of_toolchanges': 0, 'spoolman': None,
                'td1_present': False, 'lane_data_enabled': False, 'error_state': self.error is not None,
                'bypass_state': False, 'quiet_mode': False, 'position_saved': False,
                'extruders': [], 'hubs': [], 'units': [f'{UNIT} {UNIT}'], 'lanes': self._lanes(),
                'buffers': [], 'led_state': False,
                'message': {'message': self.error, 'type': 'error' if self.error else None}}

    def _lane_status(self, eventtime, i):
        self._refresh(eventtime)
        s = self.slots.get(i, {})
        has = bool(s.get('hasFilament'))
        tooled = self.active == i
        mat = s.get('Material', '?')
        return {'name': f'lane{i}', 'unit': UNIT, 'hub': None, 'extruder': None,
                'buffer': None, 'buffer_status': None, 'lane': i,
                'map': [f'T{t}' for t, slot in enumerate(self.map) if slot == i],
                'load': has, 'prep': has, 'tool_loaded': tooled, 'loaded_to_hub': tooled,
                'material': None if mat in ('', '?') else mat, 'spool_id': None,
                'color': '#' + (s.get('HEX') or 'FFFFFF'), 'weight': self._weight(i),
                'extruder_temp': None, 'runout_lane': None, 'dist_hub': 0, 'filament_status_led': '',
                'filament_status': 'In Tool' if tooled else 'Ready' if has else 'Not Ready',
                'status': 'Tooled' if tooled else 'Loaded' if has else 'None'}

    # Для SET_ZCOLOR: карта AFC вместо значений по умолчанию, окно Z-Mod скрыто
    def apply(self, defaults, silent):
        self._refresh(self.printer.get_reactor().monotonic())
        tools = [self.map[t] if t < len(self.map) and 1 <= self.map[t] <= self.n else d
                 for t, d in enumerate(defaults)]
        return tools, (silent if self.prompt or silent else 1)

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
        i = self._slot(gcmd)
        s = self.slots.get(i, {})
        hexc = self._snap((hexc or s.get('HEX') or 'FFFFFF').lstrip('#').upper())
        mat = (mat or s.get('Material') or 'PLA').upper()
        c = self.color
        if mat not in c.valid_types[:-1]:
            raise gcmd.error(f"AFC: {mat}? {', '.join(c.valid_types[:-1])}")
        if c.display:
            code, resp = c.zsend_post_request('/control', payload={
                'cmd': 'msConfig_cmd', 'args': {'slot': i, 'mt': mat, 'rgb': f'#{hexc}'}})
        else:
            code, resp = c.set_printer_data_detail(i, mat, f'#{hexc}')
        if code != 200:
            raise gcmd.error(f'AFC: {resp}')
        s.update(HEX=hexc, Material=mat)   # SET_COLOR и SET_MATERIAL идут одним скриптом
        self.slots[i] = s
        self.last = 0.

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
