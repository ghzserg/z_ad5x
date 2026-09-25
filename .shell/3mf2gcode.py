import os
import sys
import zipfile
import shutil
import requests

MOONRAKER_URL = "http://127.0.0.1:7125"

def notify_moonraker(relative_filename):
    try:
        url = f"{MOONRAKER_URL}/server/files/metadata"
        requests.post(url, json={"filename": relative_filename}, timeout=5)
    except:
        pass

def convert_all_3mf(watch_dir):
    if not os.path.exists(watch_dir):
        return

    for root, dirs, files in os.walk(watch_dir):
        if any(x in root.split(os.sep) for x in ['.thumbs', '.mod', '.zmod']) or '/.' in root or '\\.' in root:
            continue

        for item in files:
            if item.endswith('.3mf') or item.endswith('.gcode.3mf'):
                file_path = os.path.join(root, item)
                base_name = item.replace('.gcode.3mf', '').replace('.3mf', '')
                final_gcode_name = f"{base_name}.gcode"
                final_gcode_path = os.path.join(root, final_gcode_name)

                rel_dir = os.path.relpath(root, watch_dir)
                if rel_dir == '.':
                    rel_gcode_path = final_gcode_name
                else:
                    rel_gcode_path = os.path.join(rel_dir, final_gcode_name).replace('\\', '/')

                try:
                    with zipfile.ZipFile(file_path, 'r') as z:
                        gcode_in_zip = [f for f in z.namelist() if f.endswith('.gcode')]
                        if not gcode_in_zip:
                            continue

                        with z.open(gcode_in_zip[0]) as source, open(final_gcode_path, 'wb') as target:
                            shutil.copyfileobj(source, target)

                        thumb_in_zip = [f for f in z.namelist() if 'plate_' in f and f.endswith('.png')]
                        if thumb_in_zip:
                            thumb_dir = os.path.join(root, '.thumbs')
                            os.makedirs(thumb_dir, exist_ok=True)
                            final_thumb_path = os.path.join(thumb_dir, f"{final_gcode_name}.png")
                            with z.open(thumb_in_zip[0]) as source, open(final_thumb_path, 'wb') as target:
                                shutil.copyfileobj(source, target)

                    os.remove(file_path)
                    print(rel_gcode_path)
                    notify_moonraker(rel_gcode_path)

                except:
                    pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_all_3mf(os.path.abspath(os.path.expanduser(sys.argv[1])))
