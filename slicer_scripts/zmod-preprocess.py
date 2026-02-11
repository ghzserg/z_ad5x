# (C) Namida Verasche aka ninjamida
# MD5 aspects copied (with changes) from addMD5.py

import sys
import hashlib
import os

# Color info

if len(sys.argv) < 2:
    sys.exit()

file_path = sys.argv[1]

with open(file_path, 'r') as f:
    content = f.readlines()

if content[0].strip().casefold().startswith('; md5'):
    content.pop(0)

result_colors = []
highest_result_color = -1
filament_color_line = ''
filament_type_line = ''

color_data_line = ''

header_end_line = -1
remove_existing_line = -1
found_header_end_line = False
found_existing_line = False
old_color_data_line = -1

for line_raw in content:
    line = line_raw.strip().casefold()
    if not found_header_end_line:
        header_end_line += 1
    if not found_existing_line:
        remove_existing_line += 1
    if len(line) == 0:
        continue
    if line[0] == 't':
        try:
            index = int(line[1:])
            if index not in result_colors:
               result_colors += [index]
            highest_result_color = max(highest_result_color, index)
        except:
            pass
    if line[0] == ';':
        if line.startswith('; filament_colour ='):
            _, _, filament_color_line = line.partition('=')
        if line.startswith('; filament_type ='):
            _, _, filament_type_line = line.partition('=')
        if line.startswith('; zmod_color_data ='):
            found_existing_line = True
        if line.startswith('; header_block_end'):
            found_header_end_line = True

filament_colors = filament_color_line.strip().split(';')
filament_types = filament_type_line.strip().split(';')

if filament_colors[0] == '':
    filament_colors = []
if filament_types[0] == '':
    filament_types = []

if len(result_colors) == 0:
  result_colors = [0]
  highest_result_color = 0

if len(filament_colors) <= highest_result_color:
    filament_colors += [''] * (highest_result_color + 1 - len(filament_colors))

if len(filament_types) <= highest_result_color:
    filament_types += [''] * (highest_result_color + 1 - len(filament_types))

tool_indexes_string = ','.join([str(result_color) for result_color in result_colors])
filament_color_string = ','.join(filament_colors)
filament_type_string = ','.join(filament_types)

if not found_header_end_line:
    header_end_line = 0
    
content.insert(header_end_line, f"; zmod_color_data = {tool_indexes_string}|{filament_color_string}|{filament_type_string}\r\n")

if found_existing_line:
    if remove_existing_line > header_end_line: # Should never happen but just in case
        remove_existing_line += 1
    content.pop(remove_existing_line)

# MD5

content = "".join(content).encode('utf-8')

md5_hash = hashlib.md5(content).hexdigest()

md5_line = b'; MD5:' + md5_hash.encode('ascii') + b'\r\n'

new_content = md5_line + content

with open(file_path, 'wb') as f:
    f.write(new_content)