# (C) 2024-2026 ghzserg https://github.com/ghzserg/zmod
import os
import logging
import json
import hashlib
import threading
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from pathlib import Path
import re

POLY_RE = re.compile(r'POLYGON=\[\[(.*?)\]\]')
NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')
PLATE_GCODE_RE = re.compile(r'Metadata/plate_(\d+)\.gcode')

# Распаковка 3mf и разбор gcode блокируют реактор Klipper (иначе: MCU shutdown: Timer too close),
# поэтому после каждых WORK_SLICE секунд работы реактору отдаётся управление (reactor.pause(NOW):
UNPACK_CHUNK = 16384          # размер блока чтения/записи при распаковке
WORK_SLICE = 0.015            # сколько секунд подряд можно занимать реактор
LINE_CHECK_EVERY = 32         # в циклах по строкам проверять время раз в N строк
METADATA_PAUSE_TIME = 2.0     # пауза после запуска metascan, чтобы Moonraker начал работу

FFCONFIG1='/usr/prog/config/Adventurer5M.json'
FFCONFIG2='/opt/config/Adventurer5M.json'

class zmod:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.lang = config.get('language', 'en')
        self.ff5m = config.getboolean('ff5m', False)
        self.ad5x = config.getboolean('ad5x', False)
        self.c5pro = config.getboolean('c5pro', False)
        self.screen = config.getboolean('screen', True)

        self.gcode = self.printer.lookup_object('gcode')
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.on_error_gcode = gcode_macro.load_template(
            config, 'on_error_gcode', '')

        self.virtual_sdcard = None
        self.sdcard_dirname = ""

        self.gcode.register_command('SAVE_SHAPER', self.cmd_SAVE_SHAPER)
        self.gcode.register_command('ZEXCLUDE', self.cmd_ZEXCLUDE)
        self.gcode.register_command('LOAD_ZOFFSET_NATIVE', self.cmd_LOAD_ZOFFSET_NATIVE)
        self.gcode.register_command('SDCARD_PRINT_FILE_MF', self.cmd_SDCARD_PRINT_FILE_MF)
        self.gcode.register_command('ZEXCLUDE_MF', self.cmd_ZEXCLUDE_MF)

        self.printer.register_event_handler("klippy:ready", self._handle_ready)

    def _handle_ready(self):
        self.virtual_sdcard = self.printer.lookup_object('virtual_sdcard')
        self.sdcard_dirname = self.virtual_sdcard.sdcard_dirname
        self.reactor = self.printer.get_reactor()

    def _yield_reactor(self, seconds):
        """Отдать управление реактору Klipper на seconds секунд."""
        self.reactor.pause(self.reactor.monotonic() + seconds)

    def _throttle_reset(self):
        """Начало долгой операции: отсчёт WORK_SLICE и счётчики начинаются заново."""
        now = self.reactor.monotonic()
        self._throttle_t = now
        self._throttle_start = now
        self._throttle_yields = 0
        self._throttle_spent = 0.0

    def _throttle(self):
        """Вызывать в цикле долгой операции. Если реактор занят дольше WORK_SLICE - отдать управление реактору."""
        now = self.reactor.monotonic()
        if now - self._throttle_t >= WORK_SLICE:
            self.reactor.pause(self.reactor.NOW)
            after = self.reactor.monotonic()
            self._throttle_yields += 1
            self._throttle_spent += after - now
            self._throttle_t = after

    def _throttle_done(self, label):
        """Конец долгой операции: итог в klippy.log (сколько раз отдавали управление и сколько это стоило)."""
        total = self.reactor.monotonic() - self._throttle_start
        logging.info("zmod throttle [%s]: %d yields, %.2f s in yields, %.2f s total",
                     label, self._throttle_yields, self._throttle_spent, total)

    # PLATE
    def cmd_SDCARD_PRINT_FILE_MF(self, gcmd):
        filename = gcmd.get("FILENAME", None)
        if not filename:
            gcmd.respond_raw("SDCARD_PRINT_FILE_MF: FILENAME is required (no file loaded)")
            return
        fname = self._extract_3mf_gcode(filename, gcmd)
        self.gcode.run_script_from_command(f"SDCARD_PRINT_FILE FILENAME=\"{fname}\"")

    def update_metadata_async(self, filename):
        """Запускает повторное сканирование метаданных в Moonraker, не блокируя реактор."""
        encoded = quote(filename, safe="")
        url = "http://127.0.0.1:7125/server/files/metascan?filename=" + encoded

        def _worker():
            req = Request(url, method="POST")
            try:
                with urlopen(req, timeout=30):
                    pass
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _rel_path(self, fname):
        if not fname:
            return fname
        root = self.sdcard_dirname.rstrip('/')
        fname = '/' + fname.lstrip('/')
        if root:
            for prefix in {root, os.path.realpath(root)}:
                if fname == prefix:
                    return ''
                if fname.startswith(prefix + '/'):
                    fname = fname[len(prefix):]
                    break
        return fname.lstrip('/')

    # 3MF
    def _3mf_path(self, fname):
        fname = self._rel_path(fname)
        real_root = os.path.realpath(self.sdcard_dirname)
        path = os.path.join(self.sdcard_dirname, fname)
        if not os.path.realpath(path).startswith(real_root + os.sep):
            raise ValueError("3MF: invalid path")
        return path

    @staticmethod
    def _sliced_plates(names):
        plates = set()
        for name in names:
            m = PLATE_GCODE_RE.fullmatch(name)
            if m:
                plates.add(int(m.group(1)))
        return sorted(plates)

    def get_plates(self, fname):
        if not fname.lower().endswith('.3mf'):
            return []
        try:
            with ZipFile(self._3mf_path(fname), 'r') as zip_ref:
                return self._sliced_plates(zip_ref.namelist())
        except Exception:
            return []

    def get_plate(self, gcmd, fname):
        # Для не-3mf плата не имеет смысла: PLATE игнорируем (даже PLATE=0 или пустой)
        if not fname.lower().endswith('.3mf'):
            return 1
        requested = gcmd.get_int("PLATE", None)
        if requested is not None and requested < 1:
            raise gcmd.error("PLATE must be >= 1")

        plates = self.get_plates(fname)
        if not plates:
            return requested if requested is not None else 1
        if requested is None:
            return plates[0]
        if requested in plates:
            return requested

        chosen = next((p for p in plates if p > requested), plates[0])
        if self.lang == 'ru':
            gcmd.respond_raw(f"// 3MF: плата {requested} не нарезана, используется {chosen}")
        else:
            gcmd.respond_raw(f"// 3MF: plate {requested} is not sliced, using {chosen}")
        return chosen

    @staticmethod
    def _collect_3mf_filaments(elements):
        """<filament id= type= color=> -> [(tool_idx, color, type)], tool_idx 0-based."""
        colors = {}
        for fil in elements:
            fil_id_str = fil.attrib.get("id")
            if not fil_id_str:
                continue
            try:
                tool_idx = int(fil_id_str) - 1
            except ValueError:
                continue
            colors[tool_idx] = (
                tool_idx,
                fil.attrib.get("color", "").strip(),
                fil.attrib.get("type", "").strip()
            )
        return [colors[k] for k in sorted(colors)] or None

    def get_colors(self, fname, plate, gcmd=None):
        """Цвета филаментов платы plate из Metadata/slice_info.config:
        [(tool_idx, color, type)] или None. При неудаче и переданном gcmd выводит причину."""
        debug = ''
        colors = None
        try:
            with ZipFile(self._3mf_path(fname), 'r') as zip_ref:
                if 'Metadata/slice_info.config' not in zip_ref.namelist():
                    debug = "Metadata/slice_info.config not found"
                else:
                    root = ET.fromstring(zip_ref.read('Metadata/slice_info.config'))
                    indexes = []
                    for node in root.iter('plate'):
                        idx = None
                        for md in node.findall('metadata'):
                            if md.attrib.get('key') == 'index':
                                try:
                                    idx = int(md.attrib.get('value'))
                                except (TypeError, ValueError):
                                    pass
                                break
                        if idx is None:
                            continue
                        indexes.append(idx)
                        if idx == plate:
                            colors = self._collect_3mf_filaments(node.iter('filament'))
                            break
                    if not colors:
                        debug = f"no filaments for plate {plate} in slice_info.config (plates: {indexes})"
        except Exception as e:
            debug = f"{type(e).__name__}: {e}"

        if not colors and gcmd is not None:
            gcmd.respond_raw(f"// 3MF: {debug}")
        return colors

    # PLATE
    def _extract_3mf_gcode(self, fname, gcmd):
        if not fname.lower().endswith('.3mf'):
            return fname

        fname = self._rel_path(fname)
        src_3mf_path = os.path.join(self.sdcard_dirname, fname)
        p = Path(fname)

        plate_num = self.get_plate(gcmd, fname)
        stem = p.stem[:-len('.gcode')] if p.stem.lower().endswith('.gcode') else p.stem
        clean_name = f"{stem}.gcode" if plate_num == 1 else f"{stem}_{plate_num}.gcode"

        # Сохраняем подпапки исходного пути внутри 3mf_print
        rel_dir = p.parent.as_posix()
        if rel_dir in ('', '.'):
            rel_gcode = f"3mf_print/{clean_name}"
        else:
            rel_gcode = f"3mf_print/{rel_dir}/{clean_name}"

        target_gcode_path = os.path.join(self.sdcard_dirname, rel_gcode)

        real_root = os.path.realpath(self.sdcard_dirname)
        if not os.path.realpath(target_gcode_path).startswith(real_root + os.sep):
            raise gcmd.error("3MF: invalid path")

        os.makedirs(os.path.dirname(target_gcode_path), exist_ok=True)

        try:
            with ZipFile(src_3mf_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

                gcode_in_zip = f"Metadata/plate_{plate_num}.gcode"
                if gcode_in_zip not in file_list:
                    raise ValueError(f"INVALID_PLATE_NUM:{plate_num}")

                expected_md5 = None
                md5_file_path = gcode_in_zip + ".md5"
                if md5_file_path in file_list:
                    raw_md5_content = zip_ref.read(md5_file_path).decode('utf-8-sig', errors='ignore').strip()
                    if raw_md5_content:
                        expected_md5 = raw_md5_content.split()[0].lower()

                gcmd.respond_raw(f"// 3MF: Unzip {fname}[{plate_num}]...")
                with zip_ref.open(gcode_in_zip) as source, open(target_gcode_path, 'wb') as target:
                    self._throttle_reset()
                    while True:
                        chunk = source.read(UNPACK_CHUNK)
                        if not chunk:
                            break
                        target.write(chunk)
                        self._throttle()
                    self._throttle_done("3mf unzip")

                gcmd.respond_raw(f"// 3MF: Check MD5 {fname}[{plate_num}]...")
                md5_hash = hashlib.md5()
                with open(target_gcode_path, 'rb') as f_check:
                    self._throttle_reset()
                    while True:
                        chunk = f_check.read(UNPACK_CHUNK)
                        if not chunk:
                            break
                        md5_hash.update(chunk)
                        self._throttle()
                    self._throttle_done("3mf md5")

                current_md5 = md5_hash.hexdigest().lower()

                # Если хеш не совпал с тем, что в архиве — удаляем битый файл с диска
                if expected_md5 and current_md5 != expected_md5:
                    if os.path.exists(target_gcode_path):
                        os.remove(target_gcode_path)
                    raise ValueError("MD5_MISMATCH")
                gcmd.respond_raw("// 3MF: Ok")

                self.update_metadata_async(rel_gcode)
                # Даём Moonraker начать сканирование, прежде чем Klipper продолжит подготовку печати
                self._yield_reactor(METADATA_PAUSE_TIME)

                # Загружаем быстрые исключения
                self.cmd_ZEXCLUDE_MF(gcmd)
            return rel_gcode
        except Exception as e:
            if str(e).startswith("INVALID_PLATE_NUM"):
                p_num = str(e).split(":")[-1]
                err = f"!! Ошибка 3MF: Плата N{p_num} не найдена в файле" if self.lang == 'ru' else f"!! 3MF Error: Plate N{p_num} not found in file"
            elif str(e) == "MD5_MISMATCH":
                err = "!! Ошибка MD5: Контрольная сумма gcode не совпадает с файлом .md5 в 3MF" if self.lang == 'ru' else "!! MD5 Error: Extracted G-code hash does not match the internal .md5 file"
            else:
                err = f"!! Ошибка распаковки архива 3MF: {str(e)}" if self.lang == 'ru' else f"!! 3MF unpack error: {str(e)}"
            raise gcmd.error(err)

    # PLATE
    def cmd_ZEXCLUDE_MF(self, gcmd):
        filename = gcmd.get("FILENAME", None)
        if not filename:
            gcmd.respond_raw("ZEXCLUDE_MF: FILENAME is required")
            return

        filename = self._rel_path(filename)
        full_path = os.path.join(self.sdcard_dirname, filename)

        if not full_path.lower().endswith('.3mf'):
            gcmd.respond_raw("ZEXCLUDE_MF: File must be a .3mf archive")
            return

        plate_num = self.get_plate(gcmd, filename)

        try:
            with ZipFile(full_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

                config_file = f'Metadata/plate_{plate_num}.json'
                if config_file not in file_list:
                    gcmd.respond_raw(f"ZEXCLUDE_MF: Configuration file '{config_file}' not found inside 3MF")
                    return

                raw_content = zip_ref.read(config_file).decode('utf-8', errors='ignore')
                data = json.loads(raw_content)

                bbox_all = data.get("bbox_all", None)
                if not bbox_all or len(bbox_all) != 4:
                    gcmd.respond_raw(f"ZEXCLUDE_MF: 'bbox_all' valid data not found in Metadata/plate_{plate_num}.json")
                    return

                if self.c5pro:
                    lo, hi = 0, 256
                elif self.ad5x:
                    lo, hi = 0, 220
                else:
                    lo, hi = -110, 110
                if all(lo <= coord <= hi for coord in (x_min, y_min, x_max, y_max)):
                    exclude_cmd = (
                        f"_SET_FAST_KAMP "
                        f"X_START={x_min:.4f} Y_START={y_min:.4f} "
                        f"X_END={x_max:.4f} Y_END={y_max:.4f} "
                        "FROM=ZEXCLUDE_MF"
                    )
                    self.gcode.run_script_from_command(exclude_cmd)
                else:
                    gcmd.respond_raw(f"!! ZEXCLUDE_MF: Update Orca Slicer >= 2.5.0 !!")

        except FileNotFoundError:
            gcmd.respond_raw(f"ZEXCLUDE_MF: File not found: {full_path}")
            logging.error(f"ZEXCLUDE_MF: File not found: {full_path}")
        except json.JSONDecodeError:
            gcmd.respond_raw("ZEXCLUDE_MF: JSON decode error")
            logging.error("ZEXCLUDE_MF: JSON decode error")
        except Exception as e:
            logging.exception("zexclude_mf_error")
            gcmd.respond_raw(f"ZEXCLUDE_MF: Unexpected error: {str(e)}")

    def get_lang(self):
        return self.lang

    def cmd_LOAD_ZOFFSET_NATIVE(self, gcmd):
        start = gcmd.get_int("START", 0)
        if self.c5pro:
            return

        config_path = FFCONFIG1 if os.path.isfile(FFCONFIG1) else FFCONFIG2 if os.path.isfile(FFCONFIG2) else None
        if not config_path:
            raise gcmd.error(f"LOAD_ZOFFSET_NATIVE: File not found {FFCONFIG1}, {FFCONFIG2}")

        with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)

        try:
            z_probe_offset = data['leftExtruderOffset']['zProbeOffset']
        except KeyError:
            z_probe_offset = 0.0

        zoffset = round(float(z_probe_offset), 4)
        if not self.ad5x and not self.c5pro:
            zoffset += 0.025
            if self.screen or start == 0:
                if self.lang != 'ru':
                    gcmd.respond_raw("Actual Z-Offset for AD5M/AD5MPro is 0.025mm greater than value displayed on native screen")
                    gcmd.respond_raw(f"On native screen: {zoffset-0.025}")
                    gcmd.respond_raw(f"Actual: {zoffset}")
                else:
                    gcmd.respond_raw("Фактический Z-Offset принтера AD5M/AD5MPro на 0.025 мм больше значения, отображаемого на родном экране")
                    gcmd.respond_raw(f"На родном экране: {zoffset-0.025}")
                    gcmd.respond_raw(f"Фактический: {zoffset}")

        self.gcode.run_script_from_command(f"SET_GCODE_OFFSET Z={zoffset:.4f} START={start} FROM=LOAD_ZOFFSET_NATIVE")

    def cmd_ZEXCLUDE(self, gcmd):
        filename = gcmd.get("FILENAME", None)
        if not filename:
            file_path = self.virtual_sdcard.file_path()
            if not file_path:
                gcmd.respond_raw("ZEXCLUDE: FILENAME is required (no file loaded)")
                return
            full_path = file_path
        else:
            filename = self._rel_path(filename)
            full_path = os.path.join(self.sdcard_dirname, filename)

        fast = gcmd.get_int("FAST", 0)
        scan_first = gcmd.get_int("SCAN_FIRST", 0)

        load = (fast == 0)
        if load:
            self.gcode.run_script_from_command("EXCLUDE_OBJECT_DEFINE RESET=1")

        # Прямоугольник по ранее отсканированным исключениям (EXCLUDE_OBJECT_DEFINE)
        x_min = y_min = float('inf')
        x_max = y_max = float('-inf')
        found = False

        # Прямоугольник по первому слою
        f_x_min = f_y_min = float('inf')
        f_x_max = f_y_max = float('-inf')
        f_x_seen = f_y_seen = False

        # 0 - до первого ;LAYER_CHANGE, 1 - внутри первого слоя, 2 - готово или не нужно
        layer_state = 0 if scan_first else 2

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                gcmd.respond_raw(f"ZEXCLUDE: {full_path}")

                max_lines = 3000
                line_num = 0
                self._throttle_reset()
                for line in f:
                    line_num += 1

                    if line_num % LINE_CHECK_EVERY == 0:
                        self._throttle()

                    # После лимита читаем дальше только пока не закончился первый слой
                    if line_num > max_lines and layer_state >= 2:
                        break

                    # --- Сканирование первого слоя ---
                    if layer_state < 2:
                        if line.startswith(';LAYER_CHANGE'):
                            layer_state += 1
                        elif layer_state == 1 and line.startswith('G'):
                            parts = line.split()
                            if parts[0] in ('G1', 'G2', 'G3'):
                                for t in parts[1:]:
                                    c = t[0]
                                    if c == ';':
                                        break
                                    if c != 'X' and c != 'Y':
                                        continue
                                    try:
                                        v = float(t[1:])
                                    except ValueError:
                                        continue
                                    if c == 'X':
                                        f_x_min = min(f_x_min, v)
                                        f_x_max = max(f_x_max, v)
                                        f_x_seen = True
                                    else:
                                        f_y_min = min(f_y_min, v)
                                        f_y_max = max(f_y_max, v)
                                        f_y_seen = True

                    # --- Исключения из заголовка (только первые max_lines строк) ---
                    if line_num > max_lines or not line.startswith('EXCLUDE_OBJECT_DEFINE'):
                        continue

                    if load:
                        try:
                            self.gcode.run_script_from_command(line)
                        except self.gcode.error as e:
                            error_message = str(e)
                            gcmd.respond_raw(f"ZEXCLUDE: Error on line {line_num}: {error_message}")
                            logging.error(f"ZEXCLUDE: Error on line {line_num}: {error_message}")

                            try:
                                self.gcode.run_script_from_command(self.on_error_gcode.render())
                                gcmd.respond_raw("ZEXCLUDE: Error handler executed")
                            except Exception:
                                logging.exception("zexclude_error")
                                gcmd.respond_raw("ZEXCLUDE: Error handler failed")
                            load = False  # дальше не загружаем, но границы считаем
                        except Exception:
                            logging.exception("zexclude_error")
                            gcmd.respond_raw("ZEXCLUDE: Unexpected error during script execution")
                            load = False

                    m = POLY_RE.search(line)
                    if not m:
                        continue

                    nums = [float(n) for n in NUM_RE.findall(m.group(1))]
                    xs = nums[0::2]
                    ys = nums[1::2]
                    if xs and ys:
                        x_min = min(x_min, min(xs))
                        x_max = max(x_max, max(xs))
                        y_min = min(y_min, min(ys))
                        y_max = max(y_max, max(ys))
                        found = True
                self._throttle_done("ZEXCLUDE scan")

        except FileNotFoundError:
            gcmd.respond_raw(f"ZEXCLUDE: File not found: {full_path}")
            logging.error(f"ZEXCLUDE: File not found: {full_path}")
            return
        except Exception:
            logging.exception("zexclude_file_error")
            gcmd.respond_raw("ZEXCLUDE: Unexpected error during file processing")
            return

        # --- Объединяем два прямоугольника ---
        if scan_first:
            if f_x_seen and f_y_seen and f_x_max > f_x_min and f_y_max > f_y_min:
                gcmd.respond_raw(
                    f"ZEXCLUDE: First layer {f_x_min:.1f},{f_y_min:.1f} - {f_x_max:.1f},{f_y_max:.1f}")
                x_min = min(x_min, f_x_min)
                y_min = min(y_min, f_y_min)
                x_max = max(x_max, f_x_max)
                y_max = max(y_max, f_y_max)
                found = True
            else:
                gcmd.respond_raw("ZEXCLUDE: First layer area not found")

        try:
            if found and x_max > x_min and y_max > y_min:
                self.gcode.run_script_from_command(
                    f"_SET_FAST_KAMP X_START={x_min:.4f} Y_START={y_min:.4f} "
                    f"X_END={x_max:.4f} Y_END={y_max:.4f} FROM=ZEXCLUDE")
                gcmd.respond_raw(
                    f"ZEXCLUDE: Fast KAMP area {x_min:.1f},{y_min:.1f} - {x_max:.1f},{y_max:.1f}")
            else:
                self.gcode.run_script_from_command("_RESET_FAST_KAMP FROM=ZEXCLUDE")
                gcmd.respond_raw("ZEXCLUDE: No objects found, fast KAMP reset")
        except self.gcode.error as e:
            error_message = str(e)
            gcmd.respond_raw(f"ZEXCLUDE: Error: {error_message}")
            logging.error(f"ZEXCLUDE: Error: {error_message}")
            try:
                self.gcode.run_script_from_command(self.on_error_gcode.render())
                gcmd.respond_raw("ZEXCLUDE: Error handler executed")
            except Exception:
                logging.exception("zexclude_error")
                gcmd.respond_raw("ZEXCLUDE: Error handler failed")
        except Exception:
            logging.exception("zexclude_error")
            gcmd.respond_raw("ZEXCLUDE: Unexpected error during script execution")

        gcmd.respond_raw("ZEXCLUDE: End")

    def cmd_SAVE_SHAPER(self, gcmd):
        shaper_name = gcmd.get('NAME', '').lower()
        frequency = gcmd.get_float('FREQUENCY', 0.0)
        shaper_axis = gcmd.get('AXIS', '').lower()

        # Валидация параметров
        valid_shapers = ['mzv', 'zv', 'zvd', 'ei', '2hump_ei', '3hump_ei']
        if shaper_name not in valid_shapers:
            if self.lang != 'ru':
                raise gcmd.error("Invalid shaper. Allowed: %s" % ', '.join(valid_shapers))
            else:
                raise gcmd.error("Неверный шейпер. Допустимые: %s" % ', '.join(valid_shapers))
        if frequency <= 0:
            if self.lang != 'ru':
                raise gcmd.error("Frequency must be > 0")
            else:
                raise gcmd.error("Частота должна быть > 0")
        if shaper_axis not in ['x', 'y']:
            if self.lang != 'ru':
                raise gcmd.error("Axis must be X or Y")
            else:
                raise gcmd.error("Ось должна быть X или Y")

        # Сохранение параметров через Klipper API
        configfile = self.printer.lookup_object('configfile')
        configfile.set('input_shaper', 'shaper_type_%s' % shaper_axis, shaper_name)
        configfile.set('input_shaper', 'shaper_freq_%s' % shaper_axis, "%.1f" % frequency)

        # Информационное сообщение
        if self.lang != 'ru':
            gcmd.respond_info(
                "Parameters for axis %s have been saved. Run SAVE_CONFIG to apply changes." %
                shaper_axis.upper()
            )
        else:
            gcmd.respond_info(
                "Параметры для оси %s сохранены. Для применения выполните SAVE_CONFIG" %
                shaper_axis.upper()
            )

def load_config(config):
    return zmod(config)
