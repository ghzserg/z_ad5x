#!/usr/bin/env python3

import json, os, re, shutil, subprocess, sys, tempfile
import urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "plugins.json")

MOD_CONF = "/root/printer_data/config"
MOD_DATA = MOD_CONF + "/mod_data"
PLUGINS_DIR = MOD_DATA + "/plugins"
PLUGINS_CFG = MOD_DATA + "/plugins.cfg"          # активные плагины Z-Mod
VARIABLES_CFG = MOD_DATA + "/variables.cfg"      # переменные Z-Mod (helix = 1)
REM_CONF = MOD_DATA + "/rem.conf"                # каталоги к удалению при старте принтера
CONF_OUT = MOD_DATA + "/extra_plugins.moonraker.conf"
MR = "http://127.0.0.1:7125"
ON, OFF = "2E7D32", "616161"

LANG_CFG = MOD_DATA + "/lang.cfg"                # язык Z-Mod (language: ru)

# key: plugins, upd_on, upd_off, save, ok, download, clone, disabled, installed, restart, error
T = {
    "en": ["Plugins ({printer})", "Update: On", "Update: Off", "Save (Moonraker restart)", "Ok",
           "Download {name}...", "Clone {name}...", "{name}: Disabled", "{name}: Installed",
           ". Klipper restart, run PLUGINS", "Error {name}: {e}"],
    "ru": ["Плагины ({printer})", "Обновление: Вкл", "Обновление: Выкл", "Сохранить (перезапуск Moonraker)", "Ок",
           "Загрузка {name}...", "Клонирование {name}...", "{name}: отключён", "{name}: установлен",
           ". Перезапуск Klipper, затем выполните PLUGINS", "Ошибка {name}: {e}"],
    "de": ["Plugins ({printer})", "Update: An", "Update: Aus", "Speichern (Moonraker-Neustart)", "OK",
           "{name} wird heruntergeladen...", "{name} wird geklont...", "{name}: Deaktiviert", "{name}: Installiert",
           ". Klipper-Neustart, danach PLUGINS ausführen", "Fehler {name}: {e}"],
    "fr": ["Plugins ({printer})", "Mise à jour : On", "Mise à jour : Off", "Enregistrer (redémarrage de Moonraker)", "OK",
           "Téléchargement de {name}...", "Clonage de {name}...", "{name} : désactivé", "{name} : installé",
           ". Redémarrage de Klipper, puis lancez PLUGINS", "Erreur {name} : {e}"],
    "es": ["Plugins ({printer})", "Actualización: Sí", "Actualización: No", "Guardar (reinicio de Moonraker)", "OK",
           "Descargando {name}...", "Clonando {name}...", "{name}: desactivado", "{name}: instalado",
           ". Reinicio de Klipper, luego ejecute PLUGINS", "Error {name}: {e}"],
    "it": ["Plugin ({printer})", "Aggiornamento: On", "Aggiornamento: Off", "Salva (riavvio di Moonraker)", "OK",
           "Download di {name}...", "Clonazione di {name}...", "{name}: disattivato", "{name}: installato",
           ". Riavvio di Klipper, poi esegui PLUGINS", "Errore {name}: {e}"],
    "pt": ["Plugins ({printer})", "Atualização: Ligada", "Atualização: Desligada", "Guardar (reinício do Moonraker)", "OK",
           "A descarregar {name}...", "A clonar {name}...", "{name}: desativado", "{name}: instalado",
           ". Reinício do Klipper, depois execute PLUGINS", "Erro {name}: {e}"],
    "cs": ["Pluginy ({printer})", "Aktualizace: Zap", "Aktualizace: Vyp", "Uložit (restart Moonraker)", "OK",
           "Stahování {name}...", "Klonování {name}...", "{name}: vypnuto", "{name}: nainstalováno",
           ". Restart Klipperu, poté spusťte PLUGINS", "Chyba {name}: {e}"],
    "tr": ["Eklentiler ({printer})", "Güncelleme: Açık", "Güncelleme: Kapalı", "Kaydet (Moonraker yeniden başlatılır)", "Tamam",
           "{name} indiriliyor...", "{name} klonlanıyor...", "{name}: devre dışı", "{name}: yüklendi",
           ". Klipper yeniden başlatılıyor, ardından PLUGINS çalıştırın", "Hata {name}: {e}"],
    "ja": ["プラグイン ({printer})", "更新: オン", "更新: オフ", "保存 (Moonraker再起動)", "OK",
           "{name} をダウンロード中...", "{name} をクローン中...", "{name}: 無効", "{name}: インストール済み",
           "。Klipperを再起動します。その後PLUGINSを実行してください", "エラー {name}: {e}"],
    "ko": ["플러그인 ({printer})", "업데이트: 켬", "업데이트: 끔", "저장 (Moonraker 재시작)", "확인",
           "{name} 다운로드 중...", "{name} 복제 중...", "{name}: 비활성화됨", "{name}: 설치됨",
           ". Klipper 재시작 후 PLUGINS를 실행하세요", "오류 {name}: {e}"],
    "zh": ["插件 ({printer})", "更新：开启", "更新：关闭", "保存（重启 Moonraker）", "确定",
           "正在下载 {name}...", "正在克隆 {name}...", "{name}：已禁用", "{name}：已安装",
           "。Klipper 将重启，然后运行 PLUGINS", "错误 {name}：{e}"],
}
KEYS = ["plugins", "upd_on", "upd_off", "save", "ok", "download", "clone",
        "disabled", "installed", "restart", "error"]

def get_lang():
    try:
        with open(LANG_CFG, encoding="utf-8") as f:
            m = re.search(r"^\s*language:\s*(\w+)", f.read(), re.M)
            if m and m.group(1) in T:
                return m.group(1)
    except Exception:
        pass
    return "en"

LANG = get_lang()

def tr(key, **kw):
    return T[LANG][KEYS.index(key)].format(**kw)

def jload(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def jsave(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def readlines(path):
    try:
        with open(path) as f:
            return [l.strip() for l in f.read().splitlines() if l.strip()]
    except Exception:
        return []

def api(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(MR + url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=30).read()

def gcode(*lines):
    with open("/tmp/printer", "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")
            f.flush()

def say(msg):
    msg = str(msg).replace('"', "'").replace("\n", " ")[:300]
    gcode(f'RESPOND MSG="{msg}"')

def sh(cmd):
    if cmd:
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

def my_plugins(printer):
    return {n: p for n, p in jload(CATALOG, {}).items() if printer in p.get("printers", [])}

def path_of(name, p):
    return p.get("path") or os.path.join(PLUGINS_DIR, name)

def pending(path):
    return path in readlines(REM_CONF)

def mark_remove(path):
    lines = readlines(REM_CONF)
    if path not in lines:
        lines.append(path)
        with open(REM_CONF, "w") as f:
            f.write("\n".join(lines) + "\n")

def unmark_remove(path):
    lines = [l for l in readlines(REM_CONF) if l != path]
    if lines:
        with open(REM_CONF, "w") as f:
            f.write("\n".join(lines) + "\n")
    elif os.path.exists(REM_CONF):
        os.remove(REM_CONF)

def zmod_active(name):
    for l in readlines(PLUGINS_CFG):
        if l.startswith("[include") and f"plugins/{name}/" in l:
            return True
    return False

def installed(name, p):
    path = path_of(name, p)
    return os.path.isdir(path) and not pending(path)

def var_on(var):
    for l in readlines(VARIABLES_CFG):
        k, sep, v = l.partition("=")
        if sep and k.strip() == var:
            return v.strip() == "1"
    return False

def is_active(name, p):
    if p.get("type") == "web":
        return var_on(p["var"]) if p.get("var") else installed(name, p)
    return zmod_active(name)

def zmod_set(name, enable):
    gcode(f"{'ENABLE' if enable else 'DISABLE'}_PLUGIN name={name}")

def asset_name(name, p):
    a = jload(os.path.join(path_of(name, p), "release_info.json"), {}).get("asset_name")
    if a:
        return a
    raise RuntimeError("Not release_info.json with asset_name")

def web_install(name, p):
    asset = asset_name(name, p)
    url = f"https://github.com/{p['repo']}/releases/latest/download/{asset}"
    os.makedirs(os.path.join(HERE, "tmp"), exist_ok=True)   # не /tmp: архив ~60 МБ
    tmp = tempfile.mkdtemp(dir=os.path.join(HERE, "tmp"))
    try:
        resp = urllib.request.urlopen(url, timeout=60)
        m = re.search(r"/download/([^/]+)/", resp.geturl())
        tag = m.group(1) if m else "unknown"
        arc = os.path.join(tmp, asset)
        with open(arc, "wb") as f:
            shutil.copyfileobj(resp, f, 1 << 20)
        ext = os.path.join(tmp, "x")
        os.makedirs(ext)
        with zipfile.ZipFile(arc) as z:
            for i in z.infolist():
                z.extract(i, ext)
                mode = (i.external_attr >> 16) & 0o7777
                if mode:
                    os.chmod(os.path.join(ext, i.filename), mode)
        items = os.listdir(ext)
        src = os.path.join(ext, items[0]) if len(items) == 1 and \
            os.path.isdir(os.path.join(ext, items[0])) else ext
        dst = path_of(name, p)
        shutil.move(src, dst)
        jsave(os.path.join(dst, "release_info.json"), {
            "project_name": p["repo"].split("/")[1],
            "project_owner": p["repo"].split("/")[0],
            "version": tag, "asset_name": asset})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def conf_lines():
    try:
        with open(CONF_OUT) as f:
            return f.read().split("\n")
    except Exception:
        return []

def conf_save(lines):
    while lines and not lines[-1].strip():
        lines.pop()
    with open(CONF_OUT, "w") as f:
        f.write("\n".join(lines) + "\n")

def find_block(lines, name, commented):
    hdr = f"[update_manager {name}]"
    for i, l in enumerate(lines):
        if l.strip() == ("#" + hdr if commented else hdr):
            j = i + 1
            while j < len(lines):
                t = lines[j].strip()
                if commented:
                    if not t.startswith("#") or t.startswith("#["):
                        break
                elif t.startswith("["):
                    break
                j += 1
            while j > i + 1 and not lines[j - 1].strip():
                j -= 1
            return i, j
    return None

def sec_state(name):
    lines = conf_lines()
    if find_block(lines, name, False):
        return "on"
    if find_block(lines, name, True):
        return "off"
    return None

def new_block(name, p):
    if p.get("type") == "web":
        b = [f"[update_manager {name}]", "type: web", "channel: stable",
             f"repo: {p['repo']}", f"path: {p['path']}"]
        if p.get("persistent_files"):
            b += ["persistent_files:", f"    {p['persistent_files']}"]
    else:
        b = [f"[update_manager {name}]", "type: git_repo", "channel: stable",
             f"path: {path_of(name, p)}", f"origin: {p['url']}",
             "is_system_service: False", f"primary_branch: {p['branch']}"]
    return b

def set_sec(name, p, mode):
    lines = conf_lines()
    act = find_block(lines, name, False)
    com = find_block(lines, name, True)
    path = path_of(name, p)
    if mode == "on":
        unmark_remove(path)
        if act:
            return
        if com:
            i, j = com
            for k in range(i, j):
                lines[k] = lines[k].replace("#", "", 1) if lines[k].startswith("#") else lines[k]
        else:
            while lines and not lines[-1].strip():
                lines.pop()
            lines += ([""] if lines else []) + new_block(name, p)
    elif mode == "off" and act:
        if not is_active(name, p):
            mark_remove(path)        # обновления выключены и плагин не активен - каталог на удаление
        i, j = act
        for k in range(i, j):
            if lines[k].strip():
                lines[k] = "#" + lines[k]
    elif mode == "remove" and act:
        i, j = act
        if i > 0 and not lines[i - 1].strip():
            i -= 1
        del lines[i:j]
    else:
        return
    conf_save(lines)

# ---------- меню ----------
def btn(label, cmd, color):
    return f"action:prompt_button {label}|{cmd}|{color}"

def menu(printer, override=None):
    override = override or {}
    out = ["action:prompt_begin " + tr("plugins", printer=printer)]
    for name, p in my_plugins(printer).items():
        act = override.get(name, is_active(name, p))
        st = sec_state(name)
        if (act or p.get("ensure_update")) and st is None:
            set_sec(name, p, "on")
            st = "on"
        u = st == "on"
        out.append("action:prompt_button_group_start")
        out.append(btn(name, f"_PLUGIN_TOGGLE NAME={name}", ON if act else OFF))
        out.append(btn(tr("upd_on") if u else tr("upd_off"),
                       f"_PLUGIN_UPD NAME={name}", ON if u else OFF))
        out.append("action:prompt_button_group_end")
    out.append("action:prompt_footer_button " + tr("save") + "|_PLUGINS_APPLY|" + ON)
    out.append("action:prompt_footer_button " + tr("ok") + "|RESPOND TYPE=command MSG=action:prompt_end")
    out.append("action:prompt_show")
    gcode(*[f'RESPOND TYPE=command MSG="{l}"' for l in out])

def toggle(printer, name):
    p = my_plugins(printer).get(name)
    if not p:
        return
    path = path_of(name, p)
    web = p.get("type") == "web"
    final = None                       # ENABLE/DISABLE_PLUGIN - последним, он вызовет FIRMWARE_RESTART
    setvar = None                      # (переменная, значение) для SAVE_VARIABLE, у web-плагина
    new_state = None
    try:
        if is_active(name, p):
            if sec_state(name) != "on":
                mark_remove(path)        # обновления выключены, плагин отключается - каталог на удаление
            if not web:
                final = lambda: zmod_set(name, False)
            elif p.get("var"):
                setvar, new_state = (p["var"], 0), False
            text = tr("disabled", name=name)
        else:
            unmark_remove(path)          # плагин включается - каталог не удалять
            if web:
                if not os.path.isdir(path):
                    say(tr("download", name=name))
                    web_install(name, p)
                    sh(p.get("start_cmd"))
                if p.get("var"):
                    setvar, new_state = (p["var"], 1), True
            else:
                if not os.path.isdir(path):
                    say(tr("clone", name=name))
                    os.makedirs(PLUGINS_DIR, exist_ok=True)
                    r = subprocess.run(["git", "clone", "-b", p["branch"], p["url"], path],
                                       capture_output=True, text=True)
                    if r.returncode != 0:
                        raise RuntimeError(r.stderr.strip())
                final = lambda: zmod_set(name, True)
            if sec_state(name) is None:     # если обновления не выключали вручную - дописываем запись
                set_sec(name, p, "on")
            text = tr("installed", name=name)
        say(text + (tr("restart") if final else ""))
    except Exception as e:
        say(tr("error", name=name, e=e))
        return
    if final:
        final()
    else:
        if setvar:
            gcode(f"SAVE_VARIABLE VARIABLE={setvar[0]} VALUE={setvar[1]}")
        menu(printer, {name: new_state} if new_state is not None else None)

def toggle_updates(printer, name):
    p = my_plugins(printer).get(name)
    if not p:
        return
    set_sec(name, p, "off" if sec_state(name) == "on" else "on")
    menu(printer)

def apply(printer):
    gcode('RESPOND TYPE=command MSG="action:prompt_end"')
    api("POST", "/server/restart")

if __name__ == "__main__":
    cmd, printer = sys.argv[1], sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else None
    gcode('RESPOND TYPE=command MSG="action:prompt_end"')
    try:
        {"menu": lambda: menu(printer),
         "toggle": lambda: toggle(printer, name),
         "updates": lambda: toggle_updates(printer, name),
         "apply": lambda: apply(printer)}[cmd]()
    except Exception as e:
        try:
            say(f"plugman: {e}")
        except Exception:
            pass
