# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
# Эмуляция AFC (ArmoredTurtle/AFC-Klipper-Add-On) поверх zmod_color:
# панель AFC и диалог выбора lane перед печатью во Fluidd/Mainsail.
# Статус - только zmod_color.get_status() (slots, active_tool_id), карта T->слот - FILE_CONFIG.
# Общий для AD5X и C5Pro; команды загрузки/выгрузки задаются в [zmod_afc].

import os
import json
from .zmod_color import atomic_write, FILE_CONFIG

UNIT = 'IFS'

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
        self.last = 0.          # время последнего пересчёта
        self.map_mtime = -1
        for cmd in ('SET_COLOR', 'SET_MATERIAL', 'SET_MAP', 'CHANGE_TOOL', 'TOOL_UNLOAD', 'LANE_UNLOAD'):
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))
        for cmd in ('SET_WEIGHT', 'SET_SPOOL_ID'):  # шлёт диалог филамента, нам не нужны
            self.gcode.register_command(cmd, lambda gcmd: None)
        self.printer.register_event_handler('klippy:ready', self._ready)

    def _ready(self):
        self.color = self.printer.lookup_object('zmod_color')
        save_variables = self.printer.lookup_object('save_variables', None)
        self.enabled = save_variables is not None and save_variables.allVariables.get('afc', 0) == 1
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

    def _lanes(self):
        return [f'lane{i}' for i in range(1, self.n + 1)]

    def _afc_status(self, eventtime):
        self._refresh(eventtime)
        lane = f'lane{self.active}' if self.active else None
        return {'current_load': lane, 'current_lane': lane, 'next_lane': None, 'current_state': 'Idle',
                'current_toolchange': 0, 'number_of_toolchanges': 0, 'spoolman': None,
                'td1_present': False, 'lane_data_enabled': False, 'error_state': False,
                'bypass_state': False, 'quiet_mode': False, 'position_saved': False,
                'extruders': [], 'hubs': [], 'units': [f'{UNIT} {UNIT}'], 'lanes': self._lanes(),
                'buffers': [], 'message': {'message': None, 'type': None}, 'led_state': False}

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
                'color': '#' + (s.get('HEX') or 'FFFFFF'), 'weight': 1000,
                'extruder_temp': None, 'runout_lane': None, 'dist_hub': 0, 'filament_status_led': '',
                'filament_status': 'In Tool' if tooled else 'Ready' if has else 'Not Ready',
                'status': 'Tooled' if tooled else 'Loaded' if has else 'None'}

    # Для SET_ZCOLOR: карта AFC вместо значений по умолчанию, окно Z-Mod скрыто
    def apply(self, defaults, silent):
        self._refresh(self.printer.get_reactor().monotonic())
        tools = [self.map[t] if t < len(self.map) and 1 <= self.map[t] <= self.n else d
                 for t, d in enumerate(defaults)]
        return tools, (silent if self.prompt or silent else 1)

    def _slot(self, gcmd):
        lane = gcmd.get('LANE')
        i = int(lane[4:]) if lane.lower().startswith('lane') and lane[4:].isdigit() else 0
        if not 1 <= i <= self.n:
            raise gcmd.error(f'AFC: unknown lane {lane}')
        return i

    def _set(self, gcmd, hexc=None, mat=None):
        i = self._slot(gcmd)
        s = self.slots.get(i, {})
        hexc = (hexc or s.get('HEX') or 'FFFFFF').lstrip('#').upper()
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

    def cmd_SET_COLOR(self, gcmd):
        self._set(gcmd, hexc=gcmd.get('COLOR'))

    def cmd_SET_MATERIAL(self, gcmd):
        self._set(gcmd, mat=gcmd.get('MATERIAL'))

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

    def _run(self, gcmd, template):
        i = self._slot(gcmd)
        self.gcode.run_script_from_command(template.format(slot=i, tool=i - 1))
        self.last = 0.

    def cmd_CHANGE_TOOL(self, gcmd):
        self._run(gcmd, self.load)

    def cmd_TOOL_UNLOAD(self, gcmd):
        self._run(gcmd, self.unload)

    def cmd_LANE_UNLOAD(self, gcmd):
        self._run(gcmd, self.unload)

def load_config(config):
    return zmod_afc(config)
