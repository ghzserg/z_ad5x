# Virtual sdcard support (print files directly from a host g-code file)
#
# Copyright (C) 2018-2024  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, logging, io, re
import chelper

VALID_GCODE_EXTS = {'gcode', 'g', 'gco', 'gx'}
VALID_GCODE_T = frozenset([b'T0', b'T1', b'T2', b'T3'])
VALID_M104_T = frozenset(['M104', 'M109'])
EXTRUDER_COUNT = 4

_REGEX_T_VALUE = re.compile(rb'T(\d+)')
_REGEX_S_VALUE = re.compile(rb'S(\d+)')
_REGEX_SET_VELOCITY = re.compile(rb'SET_VELOCITY_LIMIT')
_REGEX_SET_PA = re.compile(rb'SET_PRESSURE_ADVANCE')

DEFAULT_ERROR_GCODE = """
{% if 'heaters' in printer %}
   TURN_OFF_HEATERS
{% endif %}
"""

SD_WORK_BATCH_TIME = 0.005
SD_WORK_BATCH_PAUSE = 0.001

# fp add for preheat (nozzle pre-heating)
FIND_ONE = 1
FIND_OK = 2
FIND_NO = 3
FIND_PRINT_END = 4

class VirtualSD:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:shutdown",
                                            self.handle_shutdown)
        # sdcard state
        sd = config.get('path')
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd))
        self.current_file = None
        self.file_position = self.file_size = 0
        # Print Stat Tracking
        self.print_stats = self.printer.load_object(config, 'print_stats')
        # Work timer
        self.reactor = self.printer.get_reactor()
        self.must_pause_work = self.cmd_from_sd = False
        self.next_file_position = 0
        self.work_timer = None
        self.load_channel = 0
        self.print_channel = 0
        self.speed_factor = 100
        self.speed_factor_enable = 0
        self.change_filament = False
        self.enable_ffm = False
        self.channel_x = 0.0;
        self.channel_y = 0.0;
        self.channel_z = 0.0;
        self.channel_e = 0.0;
        self.channel_speed = 0;
        self.pa_enable = 0
        self.adjust_M106P2 = 0
        self.adjust_M106 = 0
        self.factor_M106P2 = 0
        self.factor_M106 = 0
        self.pa_value_t0 = 99.0
        self.pa_value_t1 = 99.0
        self.pa_value_t2 = 99.0
        self.pa_value_t3 = 99.0
        self.m104 = b"M104"
        self.m109 = b"M109"
        self.set_velocity_limit = ""
        self.channel_pause_z = "0.0";
        self.channel_pause_x = "0.0";
        self.channel_pause_y = "0.0";
        self.channel_pause_is_z = False;
        self.channel_pause_is_x = False;
        self.channel_pause_is_y = False;
        self.after_channel_g1 = False;
        self.doingChangeEx = False;
        self.g1_lines = []
        self.need_check_ex = False
        self.no_filament_check_ex = False
        self.gcode_ex_used = ['T99', 'T99', 'T99', 'T99', 'T99', 'T99']
        self.gcode_ex_used_changed = ['T99', 'T99', 'T99', 'T99', 'T99', 'T99']
        # fp add for preheat (nozzle pre-heating)
        self.find_flag = FIND_PRINT_END
        self.find_next_fname = None
        self.partial_input = b""
        self.find_seek = 0
        self.heater_head = []
        self.active_head = None
        self.has_preheat = False
        self.pretemp = 160
        # fp add: preheat only if more than 2 nozzles are actually used
        self.preheat_enable = False
        # Error handling
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.on_error_gcode = gcode_macro.load_template(
            config, 'on_error_gcode', DEFAULT_ERROR_GCODE)
        # Register commands
        self.gcode = self.printer.lookup_object('gcode')
        # Fast path for simple G0/G1 moves
        self.gcode_move = None
        self.chelper_ffi, self.chelper_lib = chelper.get_ffi()
        self._g1_params = None
        for cmd in ['M20', 'M21', 'M23', 'M24', 'M25', 'M26', 'M27']:
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))
        for cmd in ['M28', 'M29', 'M30']:
            self.gcode.register_command(cmd, self.cmd_error)
        self.gcode.register_command(
            "SDCARD_RESET_FILE", self.cmd_SDCARD_RESET_FILE,
            desc=self.cmd_SDCARD_RESET_FILE_help)
        self.gcode.register_command(
            "SDCARD_PRINT_FILE", self.cmd_SDCARD_PRINT_FILE,
            desc=self.cmd_SDCARD_PRINT_FILE_help)
        self.gcode.register_command(
            "SDCARD_CLEAR_REFUELLING", self.cmd_SDCARD_CLEAR_REFUELLING,
            desc=self.cmd_SDCARD_CLEAR_REFUELLING_help)
        self.gcode.register_command(
            "SDCARD_SET_CHANNEL", self.cmd_SDCARD_SET_CHANNEL,
            desc=self.cmd_SDCARD_SET_CHANNEL_help)
        self.gcode.register_command(
            "SDCARD_SET_PAUSE_STATE", self.cmd_SDCARD_SET_PAUSE_STATE,
            desc=self.cmd_SDCARD_SET_PAUSE_STATE_help)    
        self.gcode.register_command(
            "SDCARD_ENABLE_FFM", self.cmd_SDCARD_ENABLE_FFM,
            desc=self.cmd_SDCARD_ENABLE_FFM_help)  
        self.gcode.register_command(
            "SDCARD_SET_GCODE_EX_USED_BASE", self.cmd_SDCARD_SET_GCODE_EX_USED_BASE,
            desc=self.cmd_SDCARD_SET_GCODE_EX_USED_BASE_help)
        self.gcode.register_command(
            "SDCARD_SET_GCODE_EX_USED_CHANGED", self.cmd_SDCARD_SET_GCODE_EX_USED_CHANGED,
            desc=self.cmd_SDCARD_SET_GCODE_EX_USED_CHANGED_help)
        self.gcode.register_command(
            "SDCARD_SET_NEED_CHECK_EX", self.cmd_SDCARD_SET_NEED_CHECK_EX,
            desc=self.cmd_SDCARD_SET_NEED_CHECK_EX_help)
        self.gcode.register_command(
            "SDCARD_NO_FILAMENT_CHECK_EX", self.cmd_SDCARD_NO_FILAMENT_CHECK_EX,
            desc=self.cmd_SDCARD_NO_FILAMENT_CHECK_EX_help)
        self.gcode.register_command(
            "SET_PA_ADVANCE", self.cmd_SET_PA_ADVANCE,
            desc=self.cmd_SET_PA_ADVANCE_help)
        self.gcode.register_command(
            "SET_FAN_M106P2", self.cmd_SET_FAN_M106P2,
            desc=self.cmd_SET_FAN_M106P2_help)
        self.gcode.register_command(
            "SET_FAN_M106", self.cmd_SET_FAN_M106,
            desc=self.cmd_SET_FAN_M106_help)
        self.gcode.register_command(
            "SET_SPEED_PERCENT", self.cmd_SET_SPEED_PERCENT,
            desc=self.cmd_SET_SPEED_PERCENT_help)    
    def handle_shutdown(self):
        if self.work_timer is not None:
            self.must_pause_work = True
            try:
                readpos = max(self.file_position - 1024, 0)
                readcount = self.file_position - readpos
                self.current_file.seek(readpos)
                data = self.current_file.read(readcount + 128)
            except:
                logging.exception("virtual_sdcard shutdown read")
                return
            logging.info("Virtual sdcard (%d): %s\nUpcoming (%d): %s",
                         readpos, repr(data[:readcount]),
                         self.file_position, repr(data[readcount:]))
    def stats(self, eventtime):
        if self.work_timer is None:
            return False, ""
        return True, "sd_pos=%d" % (self.file_position,)
    def get_file_list(self, check_subdirs=False):
        if check_subdirs:
            flist = []
            prefix_len = len(self.sdcard_dirname) + 1
            for root, dirs, files in os.walk(self.sdcard_dirname, followlinks=True):
                for name in files:
                    dot_pos = name.rfind('.')
                    if dot_pos == -1:
                        continue
                    ext = name[dot_pos + 1:]
                    if ext not in VALID_GCODE_EXTS:
                        continue
                    full_path = os.path.join(root, name)
                    r_path = full_path[prefix_len:]
                    size = os.path.getsize(full_path)
                    flist.append((r_path, size))
            flist.sort(key=lambda f: f[0].lower())
            return flist
        else:
            dname = self.sdcard_dirname
            try:
                filenames = os.listdir(dname)
                result = []
                for fname in sorted(filenames, key=str.lower):
                    if fname.startswith('.'):
                        continue
                    full_path = os.path.join(dname, fname)
                    if os.path.isfile(full_path):
                        result.append((fname, os.path.getsize(full_path)))
                return result
            except:
                logging.exception("virtual_sdcard get_file_list")
                raise self.gcode.error("Unable to get file list")
    def get_status(self, eventtime):
        return {
            'file_path': self.file_path(),
            'progress': self.progress(),
            'is_active': self.is_active(),
            'file_position': self.file_position,
            'file_size': self.file_size,
            'channel': self.print_channel,
            'refuelling': self.change_filament,
            'after_channel_g1': self.after_channel_g1,
            'velocity_limit': self.set_velocity_limit,
            'doingChangeEx': self.doingChangeEx,
        }
    def file_path(self):
        if self.current_file:
            return self.current_file.name
        return None
    def progress(self):
        if self.file_size:
            return float(self.file_position) / self.file_size
        else:
            return 0.
    def is_active(self):
        return self.work_timer is not None
    def do_pause(self):
        if self.work_timer is not None:
            self.must_pause_work = True
            while self.work_timer is not None and not self.cmd_from_sd:
                self.reactor.pause(self.reactor.monotonic() + .001)
    def do_resume(self):
        if self.work_timer is not None:
            raise self.gcode.error("SD busy")
        self.must_pause_work = False
        self.g1_lines = []
        self.work_timer = self.reactor.register_timer(
            self.work_handler, self.reactor.NOW)
    def do_cancel(self):
        if self.current_file is not None:
            self.do_pause()
            self.current_file.close()
            self.current_file = None
            self.change_filament = False
            self.print_stats.note_cancel()
        self.file_position = self.file_size = 0
    # G-Code commands
    def cmd_error(self, gcmd):
        raise gcmd.error("SD write not supported")
    def _reset_file(self):
        if self.current_file is not None:
            self.do_pause()
            self.current_file.close()
            self.current_file = None
        self.file_position = self.file_size = 0
        self.print_stats.reset()
        self.printer.send_event("virtual_sdcard:reset_file")
    cmd_SDCARD_RESET_FILE_help = "Clears a loaded SD File. Stops the print "\
        "if necessary"
    def cmd_SDCARD_RESET_FILE(self, gcmd):
        if self.cmd_from_sd:
            raise gcmd.error(
                "SDCARD_RESET_FILE cannot be run from the sdcard")
        self._reset_file()
    cmd_SDCARD_PRINT_FILE_help = "Loads a SD file and starts the print.  May "\
        "include files in subdirectories."
    def cmd_SDCARD_PRINT_FILE(self, gcmd):
        if self.work_timer is not None:
            raise gcmd.error("SD busy")
        self._reset_file()
        filename = gcmd.get("FILENAME")
        if filename[0] == '/':
            filename = filename[1:]
        self._load_file(gcmd, filename, check_subdirs=True)
        self.do_resume()
    cmd_SDCARD_CLEAR_REFUELLING_help = "get printing pause line gcode "
    def cmd_SDCARD_CLEAR_REFUELLING(self, gcmd):
        self.change_filament = False
    cmd_SDCARD_SET_CHANNEL_help = "set load channel "
    def cmd_SDCARD_SET_CHANNEL(self, gcmd):
        channel = gcmd.get_int('CHANNEL')
        self.set_velocity_limit = ""
        self.load_channel = channel
        self.print_channel = channel
        logging.info("Set channel , start print: %d ", channel)
    cmd_SDCARD_SET_PAUSE_STATE_help = "set SDCARD_SET_PAUSE_STATE "
    def cmd_SDCARD_SET_PAUSE_STATE(self, gcmd):
        x = gcmd.get_float('X')
        y = gcmd.get_float('Y')
        z = gcmd.get_float('Z')
        e = gcmd.get_float('E')
        speed = gcmd.get_int('SPEED')
        self.channel_x = x
        self.channel_y = y
        self.channel_z = z
        self.channel_e = e
        self.channel_speed = speed
        self.after_channel_g1 = False;
    cmd_SDCARD_SET_GCODE_EX_USED_BASE_help = "print gcode file used extruder"
    def cmd_SDCARD_SET_GCODE_EX_USED_BASE(self, gcmd):
        index = gcmd.get_int('INDEX')
        ex = gcmd.get("EXTRUDER")
        self.gcode_ex_used[index] = ex
    cmd_SDCARD_SET_GCODE_EX_USED_CHANGED_help = "print gcode file changed extruder"
    def cmd_SDCARD_SET_GCODE_EX_USED_CHANGED(self, gcmd):
        index = gcmd.get_int('INDEX')
        ex = gcmd.get("EXTRUDER")
        self.gcode_ex_used_changed[index] = ex
    cmd_SDCARD_SET_NEED_CHECK_EX_help = "enable check extrude when print"
    def cmd_SDCARD_SET_NEED_CHECK_EX(self, gcmd):
        enable = gcmd.get_int('CHECK')
        self.need_check_ex = False
        if enable == 1:
            self.need_check_ex = True
    cmd_SDCARD_NO_FILAMENT_CHECK_EX_help = "no filament enable check other extrude when print"
    def cmd_SDCARD_NO_FILAMENT_CHECK_EX(self, gcmd):
        enable = gcmd.get_int('CHECK')
        self.no_filament_check_ex = False
        if enable == 1:
            self.no_filament_check_ex = True
    cmd_SDCARD_ENABLE_FFM_help = "enable ffm "
    def cmd_SDCARD_ENABLE_FFM(self, gcmd):
        enable = gcmd.get_int('ENABLE')
        self.enable_ffm = False
        if enable == 1:
            self.enable_ffm = True
    def cmd_SET_PA_ADVANCE(self, gcmd):
        self.pa_value_t0 = gcmd.get_float('T0')
        self.pa_value_t1 = gcmd.get_float('T1')
        self.pa_value_t2 = gcmd.get_float('T2')
        self.pa_value_t3 = gcmd.get_float('T3')
        self.pa_enable = gcmd.get_int('ENABLE')
        logging.info("set advance pa_value: (%f), (%f), (%f), (%f)",self.pa_value_t0,self.pa_value_t1,self.pa_value_t2,self.pa_value_t3)
    cmd_SET_PA_ADVANCE_help = "print change pa value"
    def cmd_SET_FAN_M106P2(self, gcmd):
        self.adjust_M106P2 = gcmd.get_int('ADJUSTED')
        self.factor_M106P2 = gcmd.get_int('FACTOR')
    cmd_SET_FAN_M106P2_help = "print change M106 P2"
    def cmd_SET_FAN_M106(self, gcmd):
        self.adjust_M106 = gcmd.get_int('ADJUSTED')
        self.factor_M106 = gcmd.get_int('FACTOR')
    cmd_SET_FAN_M106_help = "print change M106"
    def cmd_SET_SPEED_PERCENT(self, gcmd):
        self.speed_factor = gcmd.get_int('PERCENT')
        self.speed_factor_enable = gcmd.get_int('ENABLE')
    cmd_SET_SPEED_PERCENT_help = "print change speed M220 Sxx"
    def cmd_M20(self, gcmd):
        # List SD card
        files = self.get_file_list()
        gcmd.respond_raw("Begin file list")
        for fname, fsize in files:
            gcmd.respond_raw("%s %d" % (fname, fsize))
        gcmd.respond_raw("End file list")
    def cmd_M21(self, gcmd):
        # Initialize SD card
        gcmd.respond_raw("SD card ok")
    def cmd_M23(self, gcmd):
        # Select SD file
        if self.work_timer is not None:
            raise gcmd.error("SD busy")
        self._reset_file()
        #self.print_channel = 0
        self.change_filament = False
        self.enable_ffm = False
        self.set_velocity_limit = ""
        filename = gcmd.get_raw_command_parameters().strip()
        if filename.startswith('/'):
            filename = filename[1:]
        self._load_file(gcmd, filename)
    def _load_file(self, gcmd, filename, check_subdirs=False):
        files = self.get_file_list(check_subdirs)
        flist = [f[0] for f in files]
        files_by_lower = { fname.lower(): fname for fname, fsize in files }
        fname = filename
        self.find_next_fname = fname  # fp add for preheat
        try:
            #if fname not in flist:
                #fname = files_by_lower[fname.lower()]
            fname = os.path.join(self.sdcard_dirname, fname)
            f = io.open(fname, 'rb')
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            f.seek(0)
        except:
            logging.exception("virtual_sdcard file open")
            raise gcmd.error("Unable to open file")
        gcmd.respond_raw("File opened:%s Size:%d" % (filename, fsize))
        gcmd.respond_raw("File selected")
        self.current_file = f
        self.file_position = 0
        self.file_size = fsize
        self.print_stats.set_current_file(filename)
    def cmd_M24(self, gcmd):
        # Start/resume SD print
        self.do_resume()
    def cmd_M25(self, gcmd):
        # Pause SD print
        self.do_pause()
    def cmd_M26(self, gcmd):
        # Set SD position
        if self.work_timer is not None:
            raise gcmd.error("SD busy")
        pos = gcmd.get_int('S', minval=0)
        self.file_position = pos
    def cmd_M27(self, gcmd):
        # Report SD print status
        if self.current_file is None:
            gcmd.respond_raw("Not SD printing.")
            return
        gcmd.respond_raw("SD printing byte %d/%d"
                         % (self.file_position, self.file_size))
    def get_file_position(self):
        return self.next_file_position
    def set_file_position(self, pos):
        self.next_file_position = pos
    def is_cmd_from_sd(self):
        return self.cmd_from_sd
    _REGEX_COORD_X = re.compile(r'X([\d.]+)')
    _REGEX_COORD_Y = re.compile(r'Y([\d.]+)')
    _REGEX_COORD_Z = re.compile(r'Z([\d.]+)')

    def extract_coord(self, line, coord_char):
        if coord_char == 'X':
            match = self._REGEX_COORD_X.search(line)
        elif coord_char == 'Y':
            match = self._REGEX_COORD_Y.search(line)
        elif coord_char == 'Z':
            match = self._REGEX_COORD_Z.search(line)
        else:
            return '0'
        return match.group(1) if match else '0'

    # fp add for preheat (nozzle pre-heating) - start
    def _remap_head(self, head):
        # Map an original T<n> head to its remapped target using the
        # SDCARD_SET_GCODE_EX_USED_BASE/CHANGED tables. Returns bytes
        # like b'T2'. If no remap entry exists, fall back to T<n> % 4.
        if not isinstance(head, bytes):
            head = head.encode()
        try:
            idx = int(head[1:].decode())
        except (ValueError, IndexError):
            return head
        # Always honour the remap tables for preheat, independent of the
        # need_check_ex / no_filament_check_ex switches. The tables default to
        # 'T99' so an unset entry simply falls through to the %4 fallback.
        str_base = "T%d" % idx
        try:
            i_base = self.gcode_ex_used.index(str_base)
        except ValueError:
            i_base = -1
        if i_base >= 0 and self.gcode_ex_used_changed[i_base] != 'T99':
            return self.gcode_ex_used_changed[i_base].encode()
        return (b'T%d' % (idx % EXTRUDER_COUNT))

    def find_next_active_channel(self, file_pos, lines, partial_input, head):
        # First find lines already buffered
        self.find_flag = FIND_NO
        self.partial_input = b""
        self.find_seek = 0

        remain_lines = list(lines)
        self.heater_head = []
        # The current head is already active (being heated by the normal M104
        # flow); it must NOT be preheated again. Track it separately so it is
        # also excluded from the cool-down pass.
        self.active_head = self._remap_head(head)
        self.partial_input = partial_input
        self.find_seek = file_pos
        while remain_lines:
            line = remain_lines.pop()
            # Get preheat temp
            if not self.has_preheat:
                if b"set nozzle temperature" in line and b"cooldown" in line:
                    logging.info("set nozzle_1 '%s' ", line)
                    match = re.search(rb'S(\d+)', line)
                    if match:
                        self.pretemp = int(match.group(1))
                        self.has_preheat = True
            if line in VALID_GCODE_T:
                remapped = self._remap_head(line)
                # Collect the (remapped) head used in the model
                if remapped not in self.heater_head:
                    self.heater_head.append(remapped)

                if self.find_flag == FIND_ONE:
                    self.find_flag = FIND_OK
                    self._finish_preheat()
                    return
                else:
                    self.find_flag = FIND_ONE

        try:
            fname = os.path.join(self.sdcard_dirname, self.find_next_fname)
            f = io.open(fname, 'rb')
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            f.seek(0)
        except:
            logging.exception("virtual_sdcard file open")
            raise
        f.seek(self.find_seek)
        # Read file 8192*N
        for i in range(10):
            try:
                data = f.read(8192)
                self.find_seek = self.find_seek + 8192
            except:
                logging.exception("find_next_active_channel read")
                break
            if not data:
                self.find_flag = FIND_PRINT_END
                f.close()
                f = None
                return
            remain_lines = data.split(b'\n')
            remain_lines[0] = self.partial_input + remain_lines[0]
            self.partial_input = remain_lines.pop()
            remain_lines.reverse()

            while remain_lines:
                line = remain_lines.pop()
                # Get preheat temp
                if not self.has_preheat:
                    if b"set nozzle temperature" in line and b"cooldown" in line:
                        logging.info("set nozzle_2 '%s' ", line)
                        match = re.search(rb'S(\d+)', line)
                        if match:
                            self.pretemp = int(match.group(1))
                            self.has_preheat = True
                if line in VALID_GCODE_T:
                    remapped = self._remap_head(line)
                    if remapped not in self.heater_head:
                        self.heater_head.append(remapped)
                    if self.find_flag == FIND_ONE:
                        self.find_flag = FIND_OK
                        self._finish_preheat()
                        f.close()
                        f = None
                        return
                    else:
                        self.find_flag = FIND_ONE

        # Other head cooling
        self._finish_preheat()
        f.close()
        f = None

    def _finish_preheat(self):
        # Decide whether preheat should be enabled: only when more than
        # 2 distinct nozzles are actually used in the model.
        self.preheat_enable = len(self.heater_head) > 2
        if self.preheat_enable:
            # Preheat the (remapped) heads actually used in the model, in
            # natural T order (T0 -> T1 -> T2 -> T3) so the next-needed head
            # is heated first rather than in file-scan order. Skip the current
            # active head - it is already printing at its normal temperature
            # and must not be overridden back to the preheat temperature.
            for h in VALID_GCODE_T:
                remapped = self._remap_head(h)
                if remapped in self.heater_head \
                        and remapped != self.active_head:
                    self.gcode.run_script(
                        f"M104 S{self.pretemp} {remapped.decode()}")
        # Note: do NOT actively cool down any head here. The scan is
        # incremental (only heads seen so far are in heater_head), so cooling
        # heads "not yet seen" would drop a soon-to-be-used nozzle to 0 right
        # before it is switched to, causing the target to jump to 0 and then
        # re-heat after the tool change.

    def find_next_block_data(self):
        try:
            fname = os.path.join(self.sdcard_dirname, self.find_next_fname)
            f = io.open(fname, 'rb')
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            f.seek(0)
        except:
            logging.exception("virtual_sdcard file open")
            raise
        f.seek(self.find_seek)
        # Read file 8192*N
        try:
            data = f.read(8192)
            self.find_seek = self.find_seek + 8192
        except:
            logging.exception("find_next_block_data read")
        if not data:
            self.find_flag = FIND_PRINT_END
            f.close()
            f = None
            return
        remain_lines = data.split(b'\n')
        remain_lines[0] = self.partial_input + remain_lines[0]
        self.partial_input = remain_lines.pop()
        remain_lines.reverse()

        while remain_lines:
            line = remain_lines.pop()
            # Get preheat temp
            if not self.has_preheat:
                if b"set nozzle temperature" in line and b"cooldown" in line:
                    logging.info("set nozzle_3 '%s' ", line)
                    match = re.search(rb'S(\d+)', line)
                    if match:
                        self.pretemp = int(match.group(1))
                        self.has_preheat = True
            if line in VALID_GCODE_T:
                remapped = self._remap_head(line)
                if remapped not in self.heater_head:
                    self.heater_head.append(remapped)
                if self.find_flag == FIND_ONE:
                    self.find_flag = FIND_OK
                    self._finish_preheat()
                    f.close()
                    f = None
                    return
                else:
                    self.find_flag = FIND_ONE
        f.close()
        f = None
    # fp add for preheat (nozzle pre-heating) - end

    # Background work timer
    def work_handler(self, eventtime):
        logging.info("Starting SD card print (position %d)", self.file_position)
        self.reactor.unregister_timer(self.work_timer)
        try:
            self.current_file.seek(self.file_position)
        except:
            logging.exception("virtual_sdcard seek")
            self.work_timer = None
            return self.reactor.NEVER
        self.print_stats.note_start()
        gcode_mutex = self.gcode.get_mutex()
        if self.gcode_move is None:
            self.gcode_move = self.printer.lookup_object('gcode_move')
            self._g1_params = self.chelper_ffi.new("struct gcode_g1_params *")
        partial_input = b""
        lines = []
        exclude_line = ""
        exclude_flag = False
        error_message = None
        busy_pause = 0.002
        busy_pause_max = 0.020
        batch_start = self.reactor.monotonic()
        # fp add for preheat
        seek_pos = self.file_position
        self.find_flag = FIND_OK
        self.has_preheat = False
        # end
        while not self.must_pause_work:
            if not lines:
                try:
                    _rt = self.reactor.monotonic()
                    data = self.current_file.read(32768)
                    # fp add for preheat
                    seek_pos += 32768
                    if self.find_flag != FIND_OK and self.find_flag != FIND_PRINT_END:
                        self.find_next_block_data()
                    # end
                    _rd = self.reactor.monotonic() - _rt
                    if _rd > 0.100:
                        logging.warning(
                            "virtual_sdcard: slow gcode read %.3fs"
                            " at file_position %d", _rd, self.file_position)
                except:
                    logging.exception("virtual_sdcard read")
                    break
                if not data:
                    self.current_file.close()
                    self.current_file = None
                    logging.info("Finished SD card print")
                    self.gcode.respond_raw("Done printing file")
                    break
                raw_lines = data.split(b'\n')
                raw_lines[0] = partial_input + raw_lines[0]
                partial_input = raw_lines.pop()
                lines.extend(reversed(raw_lines))
                self.reactor.pause(self.reactor.NOW)
                batch_start = self.reactor.monotonic()
                continue
            # Pause if any other request is pending in the gcode class
            if gcode_mutex.test():
                self.reactor.pause(self.reactor.monotonic() + busy_pause)
                busy_pause = min(busy_pause_max, busy_pause * 2.)
                batch_start = self.reactor.monotonic()
                continue
            busy_pause = 0.002
            # Dispatch command
            self.cmd_from_sd = True
            line = lines.pop()
            next_file_position = self.file_position + len(line) + 1
            self.next_file_position = next_file_position

            if not line.startswith(b";"):
                t_match = (_REGEX_T_VALUE.search(line)
                           if b'T' in line else None)
                if t_match:
                    ex_index = t_match.group(1).decode()
                    if self.need_check_ex or self.no_filament_check_ex:
                        str_base = "T" + ex_index
                        try:
                            i_base = self.gcode_ex_used.index(str_base)
                        except ValueError:
                            i_base = -1
                        if i_base >= 0:
                            changed_ex = self.gcode_ex_used_changed[i_base]
                            line = line.replace(
                                str_base.encode(), changed_ex.encode(), 1)
                        else:
                            line = line.replace(
                                str_base.encode(),
                                f'T{int(ex_index) % EXTRUDER_COUNT}'.encode(), 1)
                    else:
                        line = line.replace(
                            f'T{ex_index}'.encode(),
                            f'T{int(ex_index) % EXTRUDER_COUNT}'.encode(), 1)

                raw = line.lstrip()
                c0 = raw[:1]
                if c0 == b"S":
                    if _REGEX_SET_VELOCITY.search(line):
                        self.set_velocity_limit = line.decode().rstrip()
                    elif _REGEX_SET_PA.search(line) and self.pa_enable == 1:
                        pa_values = [self.pa_value_t0, self.pa_value_t1,
                                     self.pa_value_t2, self.pa_value_t3]
                        pa_value = pa_values[self.load_channel] if self.load_channel < 4 else self.pa_value_t0
                        if pa_value > 10.0:
                            self.gcode.run_script(line.decode())
                        else:
                            self.gcode.run_script(f"SET_PRESSURE_ADVANCE ADVANCE={pa_value}")
                        self.file_position = self.next_file_position
                        continue

                if c0 == b"M" and b'M106' in line:
                    comment_pos = line.find(b';')
                    if comment_pos != -1:
                        line = line[:comment_pos]
                    line = line.strip()
                    s_match = _REGEX_S_VALUE.search(line)
                    if s_match:
                        speed = int(s_match.group(1))
                        if b'P2' in line and self.adjust_M106P2 == 1:
                            target_speed = speed + int(self.factor_M106P2 * 255 / 100)
                            self.gcode.run_script(f"M106 P2 S{target_speed}")
                            self.file_position = self.next_file_position
                            continue
                        elif b'P' not in line and self.adjust_M106 == 1:
                            target_speed = speed + int(self.factor_M106 * 255 / 100)
                            self.gcode.run_script(f"M106 S{target_speed}")
                            self.file_position = self.next_file_position
                            continue

                if self.after_channel_g1 and (b'G1' in line or b'G0' in line):
                    comment_pos = line.find(b';')
                    if comment_pos != -1:
                        line = line[:comment_pos]
                    line = line.strip()
                    line_text = line.decode()

                    self.channel_pause_is_z = 'Z' in line_text
                    self.channel_pause_is_x = 'X' in line_text
                    self.channel_pause_is_y = 'Y' in line_text

                    if self.channel_pause_is_z:
                        self.channel_pause_z = self.extract_coord(line_text, 'Z')
                    if self.channel_pause_is_x:
                        self.channel_pause_x = self.extract_coord(line_text, 'X')
                    if self.channel_pause_is_y:
                        self.channel_pause_y = self.extract_coord(line_text, 'Y')

                    if self.channel_pause_is_y and self.channel_pause_is_x:
                        self.gcode.run_script(f"G1 X{self.channel_pause_x} Y{self.channel_pause_y} F36000")
                        if self.channel_pause_is_z:
                            self.gcode.run_script(f"G1 Z{self.channel_pause_z} F500")
                        else:
                            self.gcode.run_script(f"G1 Z{self.channel_z} F500")
                        self.after_channel_g1 = False
                        self.channel_pause_is_z = False
                        self.channel_pause_is_y = False
                        self.channel_pause_is_x = False
                    self.doingChangeEx = False
                    self.file_position = self.next_file_position
                    continue

                if (c0 == b"M"
                    and (self.m104 in line or self.m109 in line)
                    and b'T' not in line):
                    comment_pos = line.find(b';')
                    if comment_pos != -1:
                        line = line[:comment_pos]
                    line = line.strip() + b" T" + str(self.print_channel).encode()

                if line.startswith(b"EXCLUDE_OBJECT_START"):
                    exclude_line = line.decode()
                elif line.startswith(b"EXCLUDE_OBJECT_END"):
                    exclude_line = line.decode()

                if b"WIPE_TOWER_START" in line:
                    if exclude_line and exclude_line.startswith("EXCLUDE_OBJECT_START"):
                        exclude_line = exclude_line.replace("EXCLUDE_OBJECT_START", "EXCLUDE_OBJECT_END")
                        self.gcode.run_script(exclude_line)
                        exclude_flag = True

                if b"WIPE_TOWER_END" in line and exclude_flag:
                    exclude_flag = False
                    if exclude_line:
                        exclude_line = exclude_line.replace("EXCLUDE_OBJECT_END", "EXCLUDE_OBJECT_START")
                        self.gcode.run_script(exclude_line)

                if line.startswith(b"T") and line in VALID_GCODE_T:
                    # fp add for preheat
                    self.find_next_active_channel(seek_pos, lines, partial_input, line)
                    # end
                    self.print_channel = int(line[1:].decode())
                    if self.print_channel != self.load_channel:
                        self.gcode.run_script("M400")
                        self.change_filament = True
                        self.doingChangeEx = True
                        while self.change_filament:
                            self.reactor.pause(self.reactor.monotonic() + 0.05)
                        self.gcode.run_script(self.set_velocity_limit)
                        self.after_channel_g1 = True
                    self.load_channel = self.print_channel
                    self.change_filament = False
                    self.file_position = self.next_file_position
                    continue

                # Try C-level fast path for simple G0/G1 moves
                fast_ok = False
                g1line = raw
                if (len(g1line) > 1 and g1line.startswith((b'G0', b'G1'))
                    and (len(g1line) <= 2
                         or g1line[2:3] in (b' ', b'\t', b';'))):
                    g1p = self._g1_params
                    if self.chelper_lib.gcode_parse_g1(
                            line, len(line), g1p) == 0:
                        try:
                            x = g1p.X if g1p.has_X else None
                            y = g1p.Y if g1p.has_Y else None
                            z = g1p.Z if g1p.has_Z else None
                            e = g1p.E if g1p.has_E else None
                            f = g1p.F if g1p.has_F else None
                            with gcode_mutex:
                                self.gcode_move.fast_G1(x, y, z, e, f)
                            fast_ok = True
                        except self.gcode.error as e:
                            error_message = str(e)
                            self.gcode._respond_error(error_message)
                            self.printer.send_event("gcode:command_error")
                            try:
                                self.gcode.run_script(
                                    self.on_error_gcode.render())
                            except:
                                logging.exception("virtual_sdcard on_error")
                            break
                        except:
                            msg = ('Internal error on fast-G1'
                                   ' dispatch')
                            logging.exception(msg)
                            self.printer.invoke_shutdown(msg)
                            break
                if not fast_ok:
                    try:
                        self.gcode.run_script(line.decode())
                    except self.gcode.error as e:
                        error_message = str(e)
                        try:
                            self.gcode.run_script(
                                self.on_error_gcode.render())
                        except:
                            logging.exception("virtual_sdcard on_error")
                        break
                    except:
                        logging.exception("virtual_sdcard dispatch")
                        break
            if self.reactor.monotonic() - batch_start >= SD_WORK_BATCH_TIME:
                self.reactor.pause(self.reactor.monotonic() + SD_WORK_BATCH_PAUSE)
                batch_start = self.reactor.monotonic()
            self.cmd_from_sd = False
            self.file_position = self.next_file_position
            # Do we need to skip around?
            if self.next_file_position != next_file_position:
                try:
                    self.current_file.seek(self.file_position)
                except:
                    logging.exception("virtual_sdcard seek")
                    self.work_timer = None
                    return self.reactor.NEVER
                lines = []
                partial_input = b""
        logging.info("Exiting SD card print (position %d)", self.file_position)
        self.work_timer = None
        self.cmd_from_sd = False
        if error_message is not None:
            self.print_stats.note_error(error_message)
        elif self.current_file is not None:
            self.print_stats.note_pause()
        else:
            self.print_stats.note_complete()
        return self.reactor.NEVER

def load_config(config):
    return VirtualSD(config)
