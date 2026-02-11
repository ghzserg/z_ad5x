import re
import json
import requests
import logging
import subprocess

FFCONFIG='/usr/prog/config/Adventurer5M.json'
FILE_CONFIG='/usr/data/config/mod_data/file.json'

TRANSLATIONS = {
    'ru': {
        'auto_assign_no_color_match': "Автоназначение: Не удалось подобрать цвет для {}",
        'auto_assign_no_material_match': "Автоназначение: Не удалось подобрать материал для {}",
        'auto_assign_success': "Автоназначение: {} назначен слоту {}",
        'auto_assign_weak_match': "Автоназначение: {} назначен слоту {}, слабое совпадение",
        'auto_select_colors': "Автовыбор цветов",
        'cancel': "Отмена",
        'change_color': "Сменить цвет",
        'change_spool': "Меняю на катушку {}: {} / {}",
        'change_type': "Сменить тип",
        'config_error': "!! Ошибка смены цвета / типа\n{}",
        'config_success': "Настройки сохранены",
        'error_auto_assign_result': "Ошибка автоназначения катушек, код возврата {}",
        'error_color_or_type': "Укажите HEX или TYPE",
        'error_leveling': "Неверный LEVELING: {}. Допустимо: 0 или 1",
        'error_napr': "Недопустимое направление (0-1)",
        'error_native_screen_tool_count': "T4 и выше не поддерживаются на родном экране, найдено T{}",
        'error_no_filename': "Не указано имя файла (FILENAME).",
        'error_slot': "Неверный SLOT. Допустимые: 1-4",
        'error_tool': "Неверный T{}: {}. Допустимо: 1-4",
        'error_type': "Неверный тип материала: {}. Допустимо: {}",
        'file_tool': "Файл",
        'hide_color_selection': "Скрыть выбор цвета, печатать без IFS",
        'load_error': "!! Ошибка загрузки / выгружки\n{}",
        'load_success': "Загрузка началась",
        'load': "Загрузить",
        'no_prepared_data_scanning': "Подготовленные данные о цвете не найдены. Сканирование файла",
        'no_response': "!! Нет ответа от принтера. Настройте принтер: \"Настройки\" -> \"WiFi\" -> \"Сетевой режим\" -> \"Только локальные сети\"\n{}",
        'printing_error': "!! Ошибка печати файла\n{}",
        'prompt_choose': "Выберите катушку для изменения",
        'prompt_leveling_off': "Не снимать карту стола",
        'prompt_leveling_on': "Снять карту стола",
        'prompt_map_color': "Сопоставьте цвет из файла с катушкой",
        'prompt_material': "Загруженный материал",
        'remove_from_extruder': "Извлечь из экструдера",
        'reset_colors': "Сбросить цвета",
        'select_action': "Выберите действие",
        'select_color': "Выберите цвет",
        'select_type': "Выберите тип материала",
        'send_print': "Отправить на печать",
        'spool_info': "Катушка {}: {}/{}",
        'spool': "Катушка",
        'unload_error': "Ошибка выгрузки: {}",
        'unload_success': "Выгрузка начата",
        'unload': "Выгрузить"
    },
    'en': {
        'auto_assign_no_color_match': "Auto-assignment: Couldn't match color for {}",
        'auto_assign_no_material_match': "Auto-assignment: Couldn't match material for {}",
        'auto_assign_success': "Auto-assignment: {} matched to slot {}",
        'auto_assign_weak_match': "Auto-assignment: {} matched to slot {}, weak match",
        'auto_select_colors': "Auto select colors",
        'cancel': "Cancel",
        'change_color': "Change color",
        'change_spool': "Changing to spool {}: {}/{}",
        'change_type': "Change type",
        'config_error': "!! Error changing color/type\n{}",
        'config_success': "Settings saved",
        'error_auto_assign_result': "Spool auto-assignment failed, return code {}",
        'error_color_or_type': "Specify HEX or TYPE",
        'error_leveling': "Invalid LEVELING: {}. Valid: 0 or 1",
        'error_napr': "Invalid direction (0-1)",
        'error_native_screen_tool_count': "T4 or higher not supported on native screen, found T{}",
        'error_no_filename': "Missing FILENAME parameter",
        'error_slot': "Invalid SLOT. Valid: 1-4",
        'error_tool': "Invalid T{}: {}. Valid: 1-4",
        'error_type': "Invalid material type: {}. Valid: {}",
        'file_tool': "In file",
        'hide_color_selection': "Hide color selection, print without IFS",
        'load_error': "!! Load/unload error\n{}",
        'load_success': "Loading started",
        'load': "Load",
        'no_prepared_data_scanning': "Pre-prepared color data not found. Scanning file",
        'no_response': "!! No response from printer. Configure via: \"Settings\" -> \"WiFi\" -> \"Network Mode\" -> \"Local Only\"\n{}",
        'printing_error': "!! File printing error\n{}",
        'prompt_choose': "Select a spool to modify",
        'prompt_leveling_off': "Leveling Off",
        'prompt_leveling_on': "Leveling On",
        'prompt_map_color': "Map file color to spool",
        'prompt_material': "Select print materials",
        'remove_from_extruder': "Remove from extruder",
        'reset_colors': "Reset colors",
        'select_action': "Select action",
        'select_color': "Select color",
        'select_type': "Select material type",
        'send_print': "Start print",
        'spool_info': "Spool {}: {}/{}",
        'spool': "in spool",
        'unload_error': "Unloading error: {}",
        'unload_success': "Unloading started",
        'unload': "Unload"
    },
    'de': {
        'auto_assign_no_color_match': "Autozuweisung: Farbe für {} nicht gefunden",
        'auto_assign_no_material_match': "Autozuweisung: Material für {} nicht gefunden",
        'auto_assign_success': "Autozuweisung: {} dem Slot {} zugewiesen",
        'auto_assign_weak_match': "Autozuweisung: {} dem Slot {} zugewiesen, schwache Übereinstimmung",
        'auto_select_colors': "Farben auto-wählen",
        'cancel': "Abbrechen",
        'change_color': "Farbe ändern",
        'change_spool': "Wechsle zu Spule {}: {}/{}",
        'change_type': "Typ ändern",
        'config_error': "!! Fehler beim Ändern von Farbe/Typ\n{}",
        'config_success': "Einstellungen gespeichert",
        'error_auto_assign_result': "Spulenzuweisung fehlgeschlagen, Rückgabecode {}",
        'error_color_or_type': "Geben Sie HEX oder TYP an",
        'error_leveling': "Ungültiges LEVELING: {}. Erlaubt: 0 oder 1",
        'error_napr': "Ungültige Richtung (0-1)",
        'error_native_screen_tool_count': "T4 oder höher wird vom Original-Display nicht unterstützt, T{} gefunden",
        'error_no_filename': "Dateiname nicht angegeben (FILENAME)",
        'error_slot': "Ungültiger SLOT. Erlaubt: 1-4",
        'error_tool': "Ungültiges T{}: {}. Erlaubt: 1-4",
        'error_type': "Ungültiger Materialtyp: {}. Erlaubt: {}",
        'file_tool': "In Datei",
        'hide_color_selection': "Farbauswahl ausblenden, ohne IFS drucken",
        'load_error': "!! Fehler beim Laden/Entladen\n{}",
        'load_success': "Laden gestartet",
        'load': "Laden",
        'no_prepared_data_scanning': "Vorbereitete Farbdaten nicht gefunden. Datei wird gescannt",
        'no_response': "!! Keine Antwort vom Drucker. Konfigurieren Sie: \"Einstellungen\" -> \"WLAN\" -> \"Netzwerkmodus\" -> \"Nur lokal\"\n{}",
        'printing_error': "!! Fehler beim Drucken der Datei\n{}",
        'prompt_choose': "Wählen Sie eine Spule zum Ändern",
        'prompt_leveling_off': "Drucken ohne Bett-Nivellierung",
        'prompt_leveling_on': "Drucken mit Bett-Nivellierung",
        'prompt_map_color': "Farbe aus Datei einer Spule zuordnen",
        'prompt_material': "Geladenes Material",
        'remove_from_extruder': "Vom Extruder entfernen",
        'reset_colors': "Farben zurücksetzen",
        'select_action': "Aktion auswählen",
        'select_color': "Farbe auswählen",
        'select_type': "Materialtyp auswählen",
        'send_print': "Druck starten",
        'spool_info': "Spule {}: {}/{}",
        'spool': "in Spule",
        'unload_error': "Fehler beim Entladen: {}",
        'unload_success': "Entladen gestartet",
        'unload': "Entladen"
    },
    'fr': {
        'auto_assign_no_color_match': "Assignation auto : Impossible de faire correspondre la couleur pour {}",
        'auto_assign_no_material_match': "Assignation auto : Impossible de faire correspondre le matériau pour {}",
        'auto_assign_success': "Assignation auto : {} associé au slot {}",
        'auto_assign_weak_match': "Assignation auto : {} associé au slot {}, correspondance faible",
        'auto_select_colors': "Sélection auto couleurs",
        'cancel': "Annuler",
        'change_color': "Changer la couleur",
        'change_spool': "Changement vers la bobine {}: {}/{}",
        'change_type': "Changer le type",
        'config_error': "!! Erreur lors du changement de couleur/type\n{}",
        'config_success': "Paramètres enregistrés",
        'error_auto_assign_result': "Échec de l'assignation auto des bobines, code {}",
        'error_color_or_type': "Indiquez HEX ou TYPE",
        'error_leveling': "LEVELING invalide: {}. Autorisé: 0 ou 1",
        'error_napr': "Direction invalide (0-1)",
        'error_native_screen_tool_count': "T4 ou supérieur non supporté sur l'écran d'origine, T{} trouvé",
        'error_no_filename': "Nom de fichier non spécifié (FILENAME)",
        'error_slot': "Emplacement SLOT invalide. Autorisé: 1-4",
        'error_tool': "Outil T{} invalide: {}. Autorisé: 1-4",
        'error_type': "Type de matériau invalide: {}. Autorisé: {}",
        'file_tool': "Dans le fichier",
        'hide_color_selection': "Masquer la sélection des couleurs, imprimer sans IFS",
        'load_error': "!! Erreur de chargement/déchargement\n{}",
        'load_success': "Chargement commencé",
        'load': "Charger",
        'no_prepared_data_scanning': "Données de couleur préparées non trouvées. Scan du fichier",
        'no_response': "!! Aucune réponse de l'imprimante. Configurez via : \"Paramètres\" -> \"WiFi\" -> \"Mode réseau\" -> \"Réseau local uniquement\"\n{}",
        'printing_error': "!! Erreur d'impression du fichier\n{}",
        'prompt_choose': "Sélectionnez une bobine à modifier",
        'prompt_leveling_off': "Imprimer sans nivellement du lit",
        'prompt_leveling_on': "Imprimer avec nivellement du lit",
        'prompt_map_color': "Associer la couleur du fichier à une bobine",
        'prompt_material': "Matériau chargé",
        'remove_from_extruder': "Retirer de l'extrudeuse",
        'reset_colors': "Réinitialiser les couleurs",
        'select_action': "Sélectionner une action",
        'select_color': "Sélectionner une couleur",
        'select_type': "Sélectionner un type de matériau",
        'send_print': "Démarrer l'impression",
        'spool_info': "Bobine {}: {}/{}",
        'spool': "dans la bobine",
        'unload_error': "Erreur de déchargement : {}",
        'unload_success': "Déchargement commencé",
        'unload': "Décharger"
    },
    'it': {
        'auto_assign_no_color_match': "Assegnazione auto: Impossibile abbinare il colore per {}",
        'auto_assign_no_material_match': "Assegnazione auto: Impossibile abbinare il materiale per {}",
        'auto_assign_success': "Assegnazione auto: {} abbinato allo slot {}",
        'auto_assign_weak_match': "Assegnazione auto: {} abbinato allo slot {}, corrispondenza debole",
        'auto_select_colors': "Selezione auto colori",
        'cancel': "Annulla",
        'change_color': "Cambia colore",
        'change_spool': "Cambio a bobina {}: {}/{}",
        'change_type': "Cambia tipo",
        'config_error': "!! Errore durante la modifica di colore/tipo\n{}",
        'config_success': "Impostazioni salvate",
        'error_auto_assign_result': "Assegnazione auto bobine fallita, codice di ritorno {}",
        'error_color_or_type': "Specificare HEX o TYPE",
        'error_leveling': "LEVELING non valido: {}. Consentiti: 0 o 1",
        'error_napr': "Direzione non valida (0-1)",
        'error_native_screen_tool_count': "T4 o superiore non supportato sullo schermo nativo, trovato T{}",
        'error_no_filename': "Nome file non specificato (FILENAME)",
        'error_slot': "Slot non valido. Consentiti: 1-4",
        'error_tool': "Strumento T{} non valido: {}. Consentiti: 1-4",
        'error_type': "Tipo di materiale non valido: {}. Consentiti: {}",
        'file_tool': "Nel file",
        'hide_color_selection': "Nascondi selezione colore, stampa senza IFS",
        'load_error': "!! Errore di caricamento/scaricamento\n{}",
        'load_success': "Caricamento avviato",
        'load': "Carica",
        'no_prepared_data_scanning': "Dati colore preparati non trovati. Scansione del file",
        'no_response': "!! Nessuna risposta dalla stampante. Configura tramite: \"Impostazioni\" -> \"WiFi\" -> \"Modalità rete\" -> \"Solo locale\"\n{}",
        'printing_error': "!! Errore di stampa del file\n{}",
        'prompt_choose': "Seleziona una bobina da modificare",
        'prompt_leveling_off': "Stampa senza livellamento del letto",
        'prompt_leveling_on': "Stampa con livellamento del letto",
        'prompt_map_color': "Associa il colore del file alla bobina",
        'prompt_material': "Materiale caricato",
        'remove_from_extruder': "Rimuovere dall'estrusore",
        'reset_colors': "Reimposta colori",
        'select_action': "Seleziona azione",
        'select_color': "Seleziona colore",
        'select_type': "Seleziona tipo di materiale",
        'send_print': "Avvia stampa",
        'spool_info': "Bobina {}: {}/{}",
        'spool': "nella bobina",
        'unload_error': "Errore di scaricamento: {}",
        'unload_success': "Scaricamento avviato",
        'unload': "Scarica"
    },
    'es': {
        'auto_assign_no_color_match': "Asignación auto: No se pudo encontrar el color para {}",
        'auto_assign_no_material_match': "Asignación auto: No se pudo encontrar material para {}",
        'auto_assign_success': "Asignación auto: {} asignado a ranura {}",
        'auto_assign_weak_match': "Asignación auto: {} asignado a ranura {}, coincidencia débil",
        'auto_select_colors': "Selección auto colores",
        'cancel': "Cancelar",
        'change_color': "Cambiar color",
        'change_spool': "Cambiando a carrete {}: {}/{}",
        'change_type': "Cambiar tipo",
        'config_error': "!! Error al cambiar color/tipo\n{}",
        'config_success': "Configuración guardada",
        'error_auto_assign_result': "Fallo en asignación auto de bobinas, código {}",
        'error_color_or_type': "Especifique HEX o TYPE",
        'error_leveling': "LEVELING inválido: {}. Permitido: 0 o 1",
        'error_napr': "Dirección inválida (0-1)",
        'error_native_screen_tool_count': "T4 o superior no soportado en pantalla nativa, se encontró T{}",
        'error_no_filename': "Nombre de archivo no especificado (FILENAME)",
        'error_slot': "Ranura SLOT inválida. Permitidas: 1-4",
        'error_tool': "Herramienta T{} inválida: {}. Permitidas: 1-4",
        'error_type': "Tipo de material inválido: {}. Permitidos: {}",
        'file_tool': "En el archivo",
        'hide_color_selection': "Ocultar selección de color, imprimir sin IFS",
        'load_error': "!! Error de carga/descarga\n{}",
        'load_success': "Carga iniciada",
        'load': "Cargar",
        'no_prepared_data_scanning': "Datos de color preparados no encontrados. Escaneando archivo",
        'no_response': "!! Sin respuesta de la impresora. Configure en: \"Ajustes\" -> \"WiFi\" -> \"Modo de red\" -> \"Solo local\"\n{}",
        'printing_error': "!! Error al imprimir el archivo\n{}",
        'prompt_choose': "Seleccione un carrete para modificar",
        'prompt_leveling_off': "Imprimir sin nivelación de cama",
        'prompt_leveling_on': "Imprimir con nivelación de cama",
        'prompt_map_color': "Mapear color del archivo al carrete",
        'prompt_material': "Material cargado",
        'remove_from_extruder': "Extraer del extrusor",
        'reset_colors': "Restablecer colores",
        'select_action': "Seleccionar acción",
        'select_color': "Seleccionar color",
        'select_type': "Seleccionar tipo de material",
        'send_print': "Iniciar impresión",
        'spool_info': "Carrete {}: {}/{}",
        'spool': "en el carrete",
        'unload_error': "Error de descarga: {}",
        'unload_success': "Descarga iniciada",
        'unload': "Descargar"
    },
    'zh': {
        'auto_assign_no_color_match': "自动分配：无法匹配颜色 {}",
        'auto_assign_no_material_match': "自动分配：无法匹配材料 {}",
        'auto_assign_success': "自动分配：{} 已匹配至槽位 {}",
        'auto_assign_weak_match': "自动分配：{} 已匹配至槽位 {}，弱匹配",
        'auto_select_colors': "自动选择颜色",
        'cancel': "取消",
        'change_color': "更改颜色",
        'change_spool': "正在切换到线轴{}: {}/{}",
        'change_type': "更改类型",
        'config_error': "!! 颜色/类型更改错误\n{}",
        'config_success': "设置已保存",
        'error_auto_assign_result': "料盘自动分配失败，返回代码 {}",
        'error_color_or_type': "请指定HEX或TYPE",
        'error_leveling': "无效的LEVELING: {}。允许值：0或1",
        'error_napr': "方向无效（0-1）",
        'error_native_screen_tool_count': "原生屏幕不支持 T4 或更高版本，发现 T{}",
        'error_no_filename': "未指定文件名（FILENAME）",
        'error_slot': "无效的SLOT。允许值：1-4",
        'error_tool': "无效的T{}: {}。允许值：1-4",
        'error_type': "无效的材料类型: {}。允许值：{}",
        'file_tool': "文件中",
        'hide_color_selection': "隐藏颜色选择，在没有 IFS 的情况下打印",
        'load_error': "!! 加载/卸载错误\n{}",
        'load_success': "开始加载",
        'load': "加载",
        'no_prepared_data_scanning': "未找到预设颜色数据。正在扫描文件",
        'no_response': "!! 打印机无响应。请通过以下方式配置：\"设置\" -> \"WiFi\" -> \"网络模式\" -> \"仅本地网络\"\n{}",
        'printing_error': "!! 文件打印错误\n{}",
        'prompt_choose': "选择要修改的线轴",
        'prompt_leveling_off': "不使用调平打印",
        'prompt_leveling_on': "使用调平打印",
        'prompt_map_color': "将文件颜色映射到线轴",
        'prompt_material': "已加载材料",
        'remove_from_extruder': "从挤出机中取出",
        'reset_colors': "重置颜色",
        'select_action': "选择操作",
        'select_color': "选择颜色",
        'select_type': "选择材料类型",
        'send_print': "开始打印",
        'spool_info': "线轴{}: {}/{}",
        'spool': "在线轴中",
        'unload_error': "卸载错误：{}",
        'unload_success': "开始卸载",
        'unload': "卸载"
    },
    'ja': {
        'auto_assign_no_color_match': "自動割当：{}の色が一致しません",
        'auto_assign_no_material_match': "自動割当：{}の材質が一致しません",
        'auto_assign_success': "自動割当：{}をスロット{}に割り当てました",
        'auto_assign_weak_match': "自動割当：{}をスロット{}に割り当てました（不完全な一致）",
        'auto_select_colors': "色を自動選択",
        'cancel': "キャンセル",
        'change_color': "色を変更",
        'change_spool': "スプール{}に変更中: {}/{}",
        'change_type': "タイプを変更",
        'config_error': "!! 色/タイプ変更エラー\n{}",
        'config_success': "設定が保存されました",
        'error_auto_assign_result': "スプールの自動割当に失敗しました。リターンコード {}",
        'error_color_or_type': "HEXまたはTYPEを指定してください",
        'error_leveling': "無効なLEVELING: {}。0または1のみ有効",
        'error_napr': "方向が無効です（0-1）",
        'error_native_screen_tool_count': "標準画面は T4 以降に対応していません。T{} が見つかりました",
        'error_no_filename': "ファイル名が指定されていません（FILENAME）",
        'error_slot': "無効なSLOTです。1-4が有効",
        'error_tool': "無効なT{}: {}。1-4が有効",
        'error_type': "無効な材料タイプ: {}。有効なタイプ：{}",
        'file_tool': "ファイル内",
        'hide_color_selection': "カラー選択を非表示、IFSなしで印刷",
        'load_error': "!! 読み込み/排出エラー\n{}",
        'load_success': "読み込み開始",
        'load': "読み込む",
        'no_prepared_data_scanning': "事前準備されたカラーデータが見つかりません。ファイルをスキャン中",
        'no_response': "!! プリンターから応答なし。設定方法：\"設定\" -> \"WiFi\" -> \"ネットワークモード\" -> \"ローカルのみ\"\n{}",
        'printing_error': "!! ファイル印刷エラー\n{}",
        'prompt_choose': "変更するスプールを選択",
        'prompt_leveling_off': "ベッドレベリングなしで印刷",
        'prompt_leveling_on': "ベッドレベリングを使用して印刷",
        'prompt_map_color': "ファイルの色をスプールにマッピング",
        'prompt_material': "読み込まれた材料",
        'remove_from_extruder': "エクストルーダーから取り出す",
        'reset_colors': "色をリセット",
        'select_action': "操作を選択",
        'select_color': "色を選択",
        'select_type': "材料タイプを選択",
        'send_print': "印刷を開始",
        'spool_info': "スプール{}: {}/{}",
        'spool': "スプール内",
        'unload_error': "排出エラー：{}",
        'unload_success': "排出を開始",
        'unload': "排出する"
    },
    'ko': {
        'auto_assign_no_color_match': "자동 할당: {}에 대한 색상을 찾을 수 없습니다",
        'auto_assign_no_material_match': "자동 할당: {}에 대한 재질을 찾을 수 없습니다",
        'auto_assign_success': "자동 할당: {}이 슬롯 {}에 매치됨",
        'auto_assign_weak_match': "자동 할당: {}이 슬롯 {}에 매치됨, 부분 일치",
        'auto_select_colors': "색상 자동 선택",
        'cancel': "취소",
        'change_color': "색상 변경",
        'change_spool': "스풀 {}로 교체 중: {}/{}",
        'change_type': "유형 변경",
        'config_error': "!! 색상/유형 변경 오류\n{}",
        'config_success': "설정이 저장되었습니다",
        'error_auto_assign_result': "스풀 자동 할당 실패, 반환 코드 {}",
        'error_color_or_type': "HEX 또는 TYPE을 지정하세요",
        'error_leveling': "잘못된 LEVELING: {}. 0 또는 1만 허용",
        'error_napr': "방향이 잘못되었습니다 (0-1)",
        'error_native_screen_tool_count': "기본 화면에서는 T4 이상이 지원되지 않습니다. T{} 발견됨",
        'error_no_filename': "파일 이름이 지정되지 않음 (FILENAME)",
        'error_slot': "잘못된 SLOT. 1-4만 허용",
        'error_tool': "잘못된 T{}: {}. 1-4만 허용",
        'error_type': "잘못된 재료 유형: {}. 허용된 유형: {}",
        'file_tool': "파일 내",
        'hide_color_selection': "색상 선택 숨기기, IFS 없이 인쇄",
        'load_error': "!! 로드/언로드 오류\n{}",
        'load_success': "로드 시작",
        'load': "로드",
        'no_prepared_data_scanning': "사전 준비된 색상 데이터를 찾을 수 없습니다. 파일을 스캔하는 중",
        'no_response': "!! 프린터 응답 없음. 설정 방법: \"설정\" -> \"WiFi\" -> \"네트워크 모드\" -> \"로컬 전용\"\n{}",
        'printing_error': "!! 파일 인쇄 오류\n{}",
        'prompt_choose': "수정할 스풀 선택",
        'prompt_leveling_off': "레벨링 없이 인쇄",
        'prompt_leveling_on': "레벨링으로 인쇄",
        'prompt_map_color': "파일 색상을 스풀에 매핑",
        'prompt_material': "로드된 재료",
        'remove_from_extruder': "익스트루더에서 제거",
        'reset_colors': "색상 초기화",
        'select_action': "작업 선택",
        'select_color': "색상 선택",
        'select_type': "재료 유형 선택",
        'send_print': "인쇄 시작",
        'spool_info': "스풀 {}: {}/{}",
        'spool': "스풀 내",
        'unload_error': "언로드 오류: {}",
        'unload_success': "언로드 시작",
        'unload': "언로드"
    },
    'pt': {
        'auto_assign_no_color_match': "Atribuição auto: Não foi possível corresponder a cor para {}",
        'auto_assign_no_material_match': "Atribuição auto: Não foi possível corresponder o material para {}",
        'auto_assign_success': "Atribuição auto: {} correspondido ao slot {}",
        'auto_assign_weak_match': "Atribuição auto: {} correspondido ao slot {}, correspondência fraca",
        'auto_select_colors': "Seleção auto de cores",
        'cancel': "Cancelar",
        'change_color': "Alterar cor",
        'change_spool': "Mudando para bobina {}: {}/{}",
        'change_type': "Alterar tipo",
        'config_error': "!! Erro ao alterar cor/tipo\n{}",
        'config_success': "Configurações salvas",
        'error_auto_assign_result': "Falha na atribuição auto de carretel, código de retorno {}",
        'error_color_or_type': "Especifique HEX ou TIPO",
        'error_leveling': "NIVELAMENTO inválido: {}. Válido: 0 ou 1",
        'error_napr': "Direção inválida (0-1)",
        'error_native_screen_tool_count': "T4 ou superior não suportado no ecrã nativo, encontrado T{}",
        'error_no_filename': "Parâmetro NOME_DO_ARQUIVO faltando",
        'error_slot': "SLOT inválido. Válido: 1-4",
        'error_tool': "T{} inválido: {}. Válido: 1-4",
        'error_type': "Tipo de material inválido: {}. Válido: {}",
        'file_tool': "No arquivo",
        'hide_color_selection': "Ocultar seleção de cores, imprimir sem IFS",
        'load_error': "!! Erro de carregamento/descarga\n{}",
        'load_success': "Carregamento iniciado",
        'load': "Carregar",
        'no_prepared_data_scanning': "Dados de cores preparados não encontrados. Escaneando arquivo",
        'no_response': "!! Sem resposta da impressora. Configure via: \"Configurações\" -> \"WiFi\" -> \"Modo de Rede\" -> \"Apenas Local\"\n{}",
        'printing_error': "!! Erro na impressão do arquivo\n{}",
        'prompt_choose': "Selecione uma bobina para modificar",
        'prompt_leveling_off': "Imprimir sem nivelamento da mesa",
        'prompt_leveling_on': "Imprimir com nivelamento da mesa",
        'prompt_map_color': "Mapear cor do arquivo para bobina",
        'prompt_material': "Material carregado",
        'remove_from_extruder': "Remover da extrusora",
        'reset_colors': "Redefinir cores",
        'select_action': "Selecionar ação",
        'select_color': "Selecionar cor",
        'select_type': "Selecionar tipo de material",
        'send_print': "Iniciar impressão",
        'spool_info': "Bobina {}: {}/{}",
        'spool': "na bobina",
        'unload_error': "Erro ao descarregar: {}",
        'unload_success': "Descarga iniciada",
        'unload': "Descarregar"
    },
    "cs": {
        'auto_assign_no_color_match': "Auto-přiřazení: Nepodařilo se shodovat barvu pro {}",
        'auto_assign_no_material_match': "Auto-přiřazení: Nepodařilo se shodovat materiál pro {}",
        'auto_assign_success': "Auto-přiřazení: {} přiřazeno k slotu {}",
        'auto_assign_weak_match': "Auto-přiřazení: {} přiřazeno k slotu {}, slabá shoda",
        'auto_select_colors': "Automatický výběr barev",
        "cancel": "Zrušit",
        "change_color": "Změnit barvu",
        "change_spool": "Měním na cívku {}: {} / {}",
        "change_type": "Změnit typ",
        "config_error": "!! Chyba při změně barvy / typu\n{}",
        "config_success": "Nastavení uložena",
        'error_auto_assign_result': "Automatické přiřazení cívky selhalo, návratový kód {}",
        "error_color_or_type": "Zadejte HEX nebo TYP",
        "error_leveling": "Neplatný LEVELING: {}. Povoleno: 0 nebo 1",
        "error_napr": "Nepovolený směr (0–1)",
        'error_native_screen_tool_count': "Nativní obrazovka nepodporuje T4 nebo vyšší, nalezeno T{}",
        "error_no_filename": "Není zadán název souboru (FILENAME).",
        "error_slot": "Neplatný SLOT. Povolené: 1–4",
        "error_tool": "Neplatný T{}: {}. Povoleno: 1–4",
        "error_type": "Neplatný typ materiálu: {}. Povoleno: {}",
        "file_tool": "Soubor",
        'hide_color_selection': "Skrýt výběr barev, tisknout bez IFS",
        "load_error": "!! Chyba při zavádění / vyndávání\n{}",
        "load_success": "Zavádění spuštěno",
        "load": "Zavést",
        'no_prepared_data_scanning': "Předpřipravená barevná data nebyla nalezena. Skenování souboru",
        "no_response": "!! Tiskárna neodpovídá. Nastavte tiskárnu: „Nastavení“ → „WiFi“ → „Síťový režim“ → „Pouze místní sítě“\n{}",
        "printing_error": "!! Chyba tisku souboru\n{}",
        "prompt_choose": "Vyberte cívku ke změně",
        "prompt_leveling_off": "Tisk bez mapy podložky",
        "prompt_leveling_on": "Tisk s mapou podložky",
        "prompt_map_color": "Přiřaďte barvu ze souboru k cívce",
        "prompt_material": "Nahraný materiál",
        'remove_from_extruder': "Vyjmout z extruderu",
        "reset_colors": "Obnovit barvy",
        "select_action": "Vyberte akci",
        "select_color": "Vyberte barvu",
        "select_type": "Vyberte typ materiálu",
        "send_print": "Odeslat k tisku",
        "spool_info": "Cívka {}: {}/{}",
        "spool": "Cívka",
        "unload_error": "Chyba vyndávání: {}",
        "unload_success": "Vyndávání spuštěno",
        "unload": "Vyndat"
    },
    'tr': {
        'auto_assign_no_color_match': "Otomatik atama: {} için renk eşleşmedi",
        'auto_assign_no_material_match': "Otomatik atama: {} için malzeme eşleşmedi",
        'auto_assign_success': "Otomatik atama: {} yuva {} ile eşleşti",
        'auto_assign_weak_match': "Otomatik atama: {} yuva {} ile eşleşti, zayıf eşleşme",
        'auto_select_colors': "Renkleri otomatik seç",
        'cancel': "İptal",
        'change_color': "Rengi değiştir",
        'change_spool': "{} no'lu makaraya geçiliyor: {}/{}",
        'change_type': "Türü değiştir",
        'config_error': "!! Renk/tür değiştirme hatası\n{}",
        'config_success': "Ayarlar kaydedildi",
        'error_auto_assign_result': "Makara otomatik atama hatası, dönüş kodu {}",
        'error_color_or_type': "HEX veya TÜR belirtin",
        'error_leveling': "Geçersiz SEVİYELEME: {}. Geçerli: 0 veya 1",
        'error_napr': "Geçersiz yön (0-1)",
        'error_native_screen_tool_count': "Yerel ekranda T4 veya üstü desteklenmiyor, T{} bulundu",
        'error_no_filename': "DOSYA_ADI parametresi eksik",
        'error_slot': "Geçersiz YUVAL. Geçerli: 1-4",
        'error_tool': "Geçersiz T{}: {}. Geçerli: 1-4",
        'error_type': "Geçersiz malzeme türü: {}. Geçerli: {}",
        'file_tool': "Dosyada",
        'hide_color_selection': "Renk seçimini gizle, IFS olmadan yazdır",
        'load_error': "!! Yükleme/boşaltma hatası\n{}",
        'load_success': "Yükleme başlatıldı",
        'load': "Yükle",
        'no_prepared_data_scanning': "Önceden hazırlanmış renk verisi bulunamadı. Dosya taranıyor",
        'no_response': "!! Yazıcıdan yanıt alınamadı. Şu yolla yapılandırın: \"Ayarlar\" -> \"WiFi\" -> \"Ağ Modu\" -> \"Sadece Yerel\"\n{}",
        'printing_error': "!! Dosya yazdırma hatası\n{}",
        'prompt_choose': "Değiştirmek için bir makara seçin",
        'prompt_leveling_off': "Seviyeleme Kapalı",
        'prompt_leveling_on': "Seviyeleme Açık",
        'prompt_map_color': "Dosya rengini makarayla eşleştir",
        'prompt_material': "Yüklü malzeme",
        'remove_from_extruder': "Ekstruderden çıkar",
        'reset_colors': "Renkleri sıfırla",
        'select_action': "Bir işlem seçin",
        'select_color': "Renk seçin",
        'select_type': "Malzeme türünü seçin",
        'send_print': "Yazdırmayı başlat",
        'spool_info': "Makaradaki {}: {}/{}",
        'spool': "makara",
        'unload_error': "Boşaltma hatası: {}",
        'unload_success': "Boşaltma başlatıldı",
        'unload': "Boşalt"
    }
}

AUTO_ASSIGN_ANY_SUCCESS =       1 << 0 # Some success occurred (complete success if no other flags). If absent, the original tool data is unmodified.
AUTO_ASSIGN_MATERIAL_FAILURE =  1 << 1 # At least one material could not be matched (either due to missing file data or no matching material loaded)
AUTO_ASSIGN_COLOR_FAILURE =     1 << 2 # At least one color could not be matched (due to missing file data, or no materials loaded at all)
AUTO_ASSIGN_COLOR_WEAK =        1 << 3 # At least one matched color is only a "weak" match
AUTO_ASSIGN_DUPLICATE =         1 << 4 # Two (or more) colors are matched to the same slot

AUTO_ASSIGN_WEAK_COLOR_CUTOFF = (63 ** 2) * 3 # If the squares of each components difference added together, exceed this, it's considered a weak match

class zmod_color:
    def __init__(self, config):
        self.printer = config.get_printer()

        self.display = config.getboolean('display', True)
        self.lang = 'en'
        self.ifs = False
        self.valid_types = ['PLA', 'ABS', 'PETG', 'TPU', 'PLA-CF', 'PETG-CF', 'SILK', '?']
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('GET_ZCOLOR', self.cmd_GET_ZCOLOR)
        self.gcode.register_command('SET_ZCOLOR', self.cmd_SET_ZCOLOR)
        self.gcode.register_command('_SET_EXTRUDER_SLOT', self.cmd_SET_EXTRUDER_SLOT)
        self.gcode.register_command('PRINT_ZCOLOR', self.cmd_PRINT_ZCOLOR)
        self.gcode.register_command('CHANGE_T_ZCOLOR', self.cmd_CHANGE_T_ZCOLOR)
        self.gcode.register_command('_CHANGE_FILAMENT', self.cmd_CHANGE_FILAMENT)
        self.gcode.register_command('RUN_ZCOLOR', self.cmd_RUN_ZCOLOR)
        self.gcode.register_command('CHANGE_ZCOLOR', self.cmd_CHANGE_ZCOLOR)
        self.gcode.register_command('IN_ZCOLOR', self.cmd_IN_ZCOLOR)
        self.gcode.register_command('UPDATE_FF_OFFSET', self.cmd_UPDATE_FF_OFFSET)
        self.printer.register_event_handler("klippy:ready", self._handle_ready)

        with open(FFCONFIG, 'r') as file:
            data = json.load(file)
            self.serialNumber = data['general']['printerSerialNumber']
            self.checkCode = data['general']['lanCode']

    def _handle_ready(self):
        self.zmod = self.printer.lookup_object('zmod', None)
        if self.zmod is not None:
            self.lang = self.zmod.get_lang()

        self.COLOR_MAPPING = {}
        try:
            with open(f"/usr/data/config/mod_data/color/{self.lang}.json", 'r', encoding='utf-8') as f:
                self.COLOR_MAPPING = json.load(f)
        except Exception as e:
            self.COLOR_MAPPING = {}

        self.zmod_ifs = self.printer.lookup_object('zmod_ifs', None)
        self.query_adc = self.printer.lookup_object('query_adc')
        self.virtual_sd = self.printer.lookup_object('virtual_sdcard')

    def cmd_UPDATE_FF_OFFSET(self, gcmd):
        with open(FFCONFIG, 'r') as file:
            data = json.load(file)

            self.CutXOffset = float(data['leftExtruderOffset']['CutXOffset']) - 2.5
            self.CutYOffset = float(data['leftExtruderOffset']['CutYOffset']) - 7.5
            self.yOffset    = float(data['leftExtruderOffset']['yOffset']) + 229

            self.gcode.run_script_from_command(f"SET_GCODE_VARIABLE MACRO=_CUT_PRUTOK VARIABLE=x_cut VALUE={self.CutXOffset:.2f}")
            self.gcode.run_script_from_command(f"SET_GCODE_VARIABLE MACRO=_CUT_PRUTOK VARIABLE=y_cut VALUE={self.CutYOffset:.2f}")
            self.gcode.run_script_from_command(f"SET_GCODE_VARIABLE MACRO=_CLIENT_VARIABLE VARIABLE=custom_park_y VALUE={self.yOffset:.2f}")
            self.gcode.run_script_from_command(f"SET_GCODE_VARIABLE MACRO=_CLIENT_VARIABLE VARIABLE=park_at_cancel_y VALUE={self.yOffset:.2f}")

    def get_display(self):
        return self.display

    def get_printer_ip(self):
        interfaces = ['wlan0', 'eth0']
        for iface in interfaces:
            try:
                result = subprocess.run(
                    ['ip', '-br', 'addr', 'show', iface],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.split()[2].split('/')[0]
            except:
                pass
        return "Not found"

    def get_current_channel(self):
        if self.ifs:
            with open(FFCONFIG, 'r') as file:
                config = json.load(file)
                prutok = int(config["FFMInfo"].get("channel", 0))
                if not self.display:
                    self.zmod_ifs.set_cur_port(prutok)
                return prutok
        return 0

    def get_extruder_sensor(self):
        value, timestamp = self.query_adc.adc["temperature_sensor filamentValue"].get_last_value()
        result = True
        if value > 0.3:
            result = (value >= 0.72)
        return result

    def get_printer_data_detail(self):
        response_data = {
            "detail": {
                "hasMatlStation": False,
                "indepMatlInfo": {
                    },
                "matlStationInfo": {
                    "slotInfos": []
                }
            }
        }

        with open(FFCONFIG, 'r') as file:
            config = json.load(file)

            ffm_info = config["FFMInfo"]
            response_data["detail"]["hasMatlStation"] = self.zmod_ifs.get_ifs_status()
            response_data["detail"]["indepMatlInfo"] = {
                "materialName": ffm_info.get("ffmType0", "N/A"),
                "materialColor": ffm_info["ffmColor0"]
            }

            for i in range(0, 5):
                color_key = f"ffmColor{i}"
                type_key = f"ffmType{i}"

                if color_key in ffm_info:
                    slot = {
                        "slotId": str(i),
                        "materialName": ffm_info.get(type_key, "N/A"),
                        "materialColor": ffm_info[color_key],
                        "hasFilament": self.zmod_ifs.get_port(i)
                    }
                    response_data["detail"]["matlStationInfo"]["slotInfos"].append(slot)

        return 200,response_data

    def set_printer_data_detail(self, zslot, ztype, zcolor):
        if not (0 <= zslot <= 4):
            return 500, "slot must be between 0 and 4"

        if not zcolor.startswith('#'):
            return 500, "Bed color"

        with open(FFCONFIG, 'r') as file:
            config = json.load(file)

            config["FFMInfo"][f"ffmColor{zslot}"] = zcolor
            config["FFMInfo"][f"ffmType{zslot}"] = ztype

            with open(FFCONFIG, 'w', encoding='utf-8') as file:
                json_string = json.dumps(config, indent='\t')
                formatted_json_string = re.sub(r'(":)', r'" : ', json_string)
                file.write(formatted_json_string)
                return 200, formatted_json_string

        return 500, "Error"

    def zsend_post_request(self, api, payload=None, send_data=None):
        base_ip = self.get_printer_ip()
        url = f"http://{base_ip}:8898{api}"
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json"
        }
        if send_data is not None:
            data = send_data
        else:
            data = {}

        data["serialNumber"] = self.serialNumber
        data["checkCode"] = self.checkCode

        if payload is not None:
            data["payload"] = payload

        try:
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=60
            )
            try:
                response_json = response.json()
            except ValueError:
                return None, response.text
            if response_json.get("code") == 0:
                return response.status_code, response_json
            else:
                response_json["send_data"] = data
                response_json["send_url"] = url
                return None, response_json
        except requests.exceptions.RequestException as e:
            return None, str(e)

    def _t(self, key, *args):
        return TRANSLATIONS[self.lang][key].format(*args)

    def parse_printer_response(self, response_data):
        slots_info = []
        self.ifs = response_data.get('detail', {}).get('hasMatlStation', False)
        if self.ifs:
            slots = response_data.get('detail', {}).get('matlStationInfo', {}).get('slotInfos', [])
            for slot in slots:
                if slot.get('hasFilament', True):
                    slot_id = slot.get('slotId', 'N/A')
                    material = slot.get('materialName', 'N/A').upper()
                    hex_color = slot.get('materialColor', '161616').replace("#", "")
                    color_name = self.COLOR_MAPPING.get(hex_color.lower(), hex_color)
                    slots_info.append({
                        'ID': slot_id,
                        'Material': material,
                        'Color': color_name,
                        'HEX': hex_color.upper()
                    })
        else:
            slot = response_data.get('detail', {}).get('indepMatlInfo', {})
            if slot:
                material = slot.get('materialName', 'N/A').upper()
                hex_color = slot.get('materialColor', '161616').replace("#", "")
                color_name = self.COLOR_MAPPING.get(hex_color.lower(), hex_color)
                slots_info.append({
                    'ID': 0,
                    'Material': material,
                    'Color': color_name,
                    'HEX': hex_color.upper()
                })

        return slots_info

    def cmd_SET_EXTRUDER_SLOT(self, gcmd):
        zslot = gcmd.get_int('SLOT', 0)
        if zslot < 1 or zslot > 4:
            raise gcmd.error(self._t('error_slot'))
        if self.display:
            raise gcmd.error("Error: Display on")
        else:
            with open(FFCONFIG, 'r') as file:
                config = json.load(file)

                config["FFMInfo"]["channel"] = zslot
                if not self.display:
                    self.zmod_ifs.set_cur_port(zslot)

                with open(FFCONFIG, 'w', encoding='utf-8') as file:
                    json_string = json.dumps(config, indent='\t')
                    formatted_json_string = re.sub(r'(":)', r'" : ', json_string)
                    file.write(formatted_json_string)
                    gcmd.respond_raw(f"Extruder: {zslot}")

    def cmd_GET_ZCOLOR(self, gcmd):
        silent = gcmd.get_int('SILENT', 0)

        if silent == 0:
            gcmd.respond_raw("// action:prompt_end")
        if self.display:
            status_code, response_data = self.zsend_post_request("/detail")
        else:
            status_code, response_data = self.get_printer_data_detail()
        if status_code:
            if silent == 0:
                #gcmd.respond_raw(json.dumps(response_data))
                gcmd.respond_raw(f"// action:prompt_begin {self._t('prompt_material')}")

            result = self.parse_printer_response(response_data)

            prompt_text = f"Extruder: None ({self.get_current_channel()})"
            button_text = ""
            if self.get_extruder_sensor() and not self.display:
                prompt_text = f"Extruder: {self.get_current_channel()}"
                for slot in result:
                    if self.get_current_channel() == int(slot['ID']):
                        prompt_text = f"Extruder: {slot['ID']}: {slot['Material']}/{slot['Color']}"
                        if silent == 0:
                            button_text = f"// action:prompt_button {self._t('remove_from_extruder')}|_IFS_REMOVE_CURRENT_PRUTOK|primary|{slot['HEX']}"
                        break

            if silent == 0:
                gcmd.respond_raw(f"// action:prompt_text {prompt_text} | IFS: {self.ifs}")
                if button_text:
                    gcmd.respond_raw(f"{button_text}")
                gcmd.respond_raw(f"// action:prompt_text {self._t('prompt_choose')}")
                gcmd.respond_raw("// action:prompt_button_group_start")
            else:
                gcmd.respond_raw(f"// {prompt_text} | IFS: {self.ifs}")
            for slot in result:
                color_name = slot['Color'].replace('_', '/', 1) if slot['Color'].startswith('_') else ''
                btn_text = f"{slot['ID']}: {slot['Material']}{color_name}"
                if silent == 0:
                    gcmd.respond_raw(f"// action:prompt_button {btn_text}|RUN_ZCOLOR SLOT={slot['ID']} HEX={slot['HEX']} TYPE={slot['Material']}|primary|{slot['HEX']}")
                else:
                    gcmd.respond_raw(f"// {btn_text}")

            if silent == 0:
                gcmd.respond_raw("// action:prompt_button_group_end")
                gcmd.respond_raw(f"// action:prompt_footer_button Ok|RESPOND TYPE=command MSG=action:prompt_end")
                gcmd.respond_raw(f"// action:prompt_footer_button {self._t('reset_colors')}|RESET_ZCOLOR")
                gcmd.respond_raw("// action:prompt_show")
        else:
            gcmd.respond_raw(self._t('no_response', json.dumps(response_data)))

    def get_allowed_tool_count(self, gcmd):
        if self.display:
            return 4

        save_variables = self.printer.lookup_object('save_variables', None)
        save_variables = {} if save_variables == None else save_variables.allVariables

        allowed_tool_count = save_variables.get('allowed_tool_count', 0)
        if allowed_tool_count <= 0:
            allowed_tool_count = 4

        return allowed_tool_count

    def get_used_colors(self, gcmd):
        # Returns list of tuples. (tool ID, color, material)

        save_variables = self.printer.lookup_object('save_variables', None)
        save_variables = {} if save_variables == None else save_variables.allVariables

        scan_files_setting = save_variables.get('scan_file_colors', 0)

        if scan_files_setting == 0:
            tool_count = self.get_allowed_tool_count(gcmd)
            return [(i, '', '') for i in range(tool_count)]

        fname = gcmd.get('FILENAME', '')
        if fname == '':
            raise gcmd.error(self._t('error_no_filename'))

        result_colors = []
        highest_result_color = -1
        filament_color_line = ''
        filament_type_line = ''

        color_data_line = ''

        with open(f"/usr/data/gcodes/{fname}", 'r') as f:
            for line_raw in f:
                line = line_raw.strip().casefold()
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
                        _, _, color_data_line = line.partition('=')
                        break
                    if line.startswith('; header_block_end'):
                        if scan_files_setting == 2:
                            tool_count = self.get_allowed_tool_count(gcmd)
                            return [(i, '', '') for i in range(tool_count)]
                        else:
                            gcmd.respond_raw(f"// {self._t('no_prepared_data_scanning')}")

        if color_data_line == '':
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
        else:
            color_data_params = color_data_line.strip().split('|')
            result_colors = [int(color_index) for color_index in color_data_params[0].split(',')]
            filament_colors = color_data_params[1].split(',')
            filament_types = color_data_params[2].split(',')

        return sorted([(tool_index, filament_colors[tool_index], filament_types[tool_index]) for tool_index in result_colors])

    def get_auto_tool_assignments(self, gcmd, orig_tools, raw_slots, output_text, one_based_indexes):
        if len(raw_slots) == 0:
            return AUTO_ASSIGN_MATERIAL_FAILURE | AUTO_ASSIGN_COLOR_FAILURE

        result_flags = 0

        slots = [slot.copy() for slot in raw_slots]
        for slot in slots:
            try:
                slot['red'] = int(slot['HEX'][0:2], 16)
                slot['green'] = int(slot['HEX'][2:4], 16)
                slot['blue'] = int(slot['HEX'][4:6], 16)
            except:
                slot['red'] = -1
                slot['green'] = -1
                slot['blue'] = -1

        tools = [0] * len(orig_tools)
        file_colors = self.file_colors

        for iTool in range(len(tools)):
            for file_color in file_colors:
                if iTool == file_color[0]:  # not a failure if we don't find any match between i and file_color[0] - it is expected on unused tool indexes
                    if self.lang == 'ru':
                        tool_name = f"T{iTool}" if not one_based_indexes else f"цвет {iTool + 1}"
                    else:
                        tool_name = f"tool T{iTool}" if not one_based_indexes else f"color {iTool + 1}"
                    candidates = []
                    if file_color[2] != '':
                        for slot in slots:
                            if (slot['Material'].casefold() == file_color[2].casefold()):
                                candidates += [slot]
                    if len(candidates) == 0:
                        result_flags |= AUTO_ASSIGN_MATERIAL_FAILURE
                        this_material_failure = True
                        candidates = slots
                        output_text += [f"// {self._t('auto_assign_no_material_match', tool_name)}"]
                    else:
                        result_flags |= AUTO_ASSIGN_ANY_SUCCESS
                        this_material_failure = False

                    if file_color[1] == '':
                        result_flags |= AUTO_ASSIGN_COLOR_FAILURE
                        if not this_material_failure:
                            tools[iTool] = int(candidates[0]['ID'])
                        output_text += [f"// {self._t('auto_assign_no_color_match', tool_name)}"]
                        continue

                    closest_slot = None
                    closest_slot_difference = float('inf')

                    file_color_red = int(file_color[1][1:3], 16)
                    file_color_green = int(file_color[1][3:5], 16)
                    file_color_blue = int(file_color[1][5:7], 16)
                    for slot in candidates:
                        if slot['red'] < 0 or slot['green'] < 0 or slot['blue'] < 0:
                            continue

                        this_color_difference = (
                            (file_color_red - slot['red']) ** 2 +
                            (file_color_green - slot['green']) ** 2 +
                            (file_color_blue - slot['blue']) ** 2
                        )

                        if this_color_difference < closest_slot_difference:
                            closest_slot = slot
                            closest_slot_difference = this_color_difference

                    if closest_slot == None:
                        result_flags |= AUTO_ASSIGN_COLOR_FAILURE
                        if not this_material_failure:
                            tools[iTool] = int(candidates[0]['ID'])
                        output_text += [f"// {self._t('auto_assign_no_color_match', tool_name)}"]
                        continue

                    result_flags |= AUTO_ASSIGN_ANY_SUCCESS

                    if closest_slot_difference >= AUTO_ASSIGN_WEAK_COLOR_CUTOFF:
                        result_flags |= AUTO_ASSIGN_COLOR_WEAK

                    if closest_slot_difference >= AUTO_ASSIGN_WEAK_COLOR_CUTOFF:
                        output_text += [f"// {self._t('auto_assign_weak_match', tool_name, closest_slot['ID'])}"]
                    else:
                        output_text += [f"// {self._t('auto_assign_success', tool_name, closest_slot['ID'])}"]

                    tools[iTool] = int(closest_slot['ID'])

        if (result_flags & AUTO_ASSIGN_ANY_SUCCESS) != 0:  # Safety check - only write back to orig_tools if success flag has been marked
            for i in range(len(tools)):
                if tools[i] > 0:
                    orig_tools[i] = tools[i]
                    if (result_flags & AUTO_ASSIGN_DUPLICATE) == 0:
                        for iDupCheck in range(i):
                            if tools[iDupCheck] > 0 and tools[iDupCheck] == tools[i]:
                                result_flags |= AUTO_ASSIGN_DUPLICATE
                                break
        return result_flags


    def cmd_SET_ZCOLOR(self, gcmd):
        save_variables = self.printer.lookup_object('save_variables', None)
        save_variables = {} if save_variables == None else save_variables.allVariables

        one_based_indexes = (save_variables.get('color_menu_1_based', 0) != 0)

        silent = gcmd.get_int('SILENT', 0)

        fname = gcmd.get('FILENAME', '')
        if fname == '':
            raise gcmd.error(self._t('error_no_filename'))

        leveling = gcmd.get_int('LEVELING', 0)
        if leveling not in (0, 1):
            raise gcmd.error(self._t('error_leveling', leveling))

        if gcmd.get_int('ALLOWED_TOOL_COUNT', 0) == 0:
            self.file_colors = self.get_used_colors(gcmd)
            if self.display and any(file_color[0] > 3 for file_color in self.file_colors):
                raise gcmd.error(self._t('error_native_screen_tool_count', len(self.file_colors)))
            auto_assign_setting = save_variables.get('auto_assign_colors', 0)
        else:
            auto_assign_setting = 0

        auto_assign = gcmd.get_int('AUTO_ASSIGN', auto_assign_setting)

        file_colors = self.file_colors
        color_indexes = [file_color[0] for file_color in file_colors]

        leveling_text = (
            self._t('prompt_leveling_on')
            if leveling
            else self._t('prompt_leveling_off')
        )

        auto_selection_output_text = []

        if self.display:
            status_code, response_data = self.zsend_post_request("/detail")
        else:
            status_code, response_data = self.get_printer_data_detail()
        if status_code:
            allowed_tool_count = max(file_colors, key=lambda entry: entry[0])[0] + 1

            result = self.parse_printer_response(response_data)

            if not self.ifs:
                silent = 2
            else:
                if auto_assign == 0:
                    default_values = [result[i]['ID'] if i < len(result) else result[-1]['ID'] for i in range(allowed_tool_count)] if result else [1] * allowed_tool_count
                    tools = []
                    for i in range(allowed_tool_count):
                        tools += [gcmd.get_int(f"T{i}", int(default_values[i]))]
                else:
                    tools = [1] * allowed_tool_count
                    auto_result = self.get_auto_tool_assignments(gcmd, tools, result, auto_selection_output_text, one_based_indexes)

                for i, tool in enumerate(tools):
                    if tool < 1 or tool > 4:
                        raise gcmd.error(self._t('error_tool', i, tool))

            if silent == 0:
                current_tools_param_text = ""
                for i in range(allowed_tool_count):
                    current_tools_param_text += f" T{i}={tools[i]}"
                current_tools_param_text = current_tools_param_text[1:]

                gcmd.respond_raw("// action:prompt_end")
                gcmd.respond_raw(f"// action:prompt_begin {self._t('prompt_material')}")
                prompt_text = f"Extruder: None ({self.get_current_channel()})"
                if self.get_extruder_sensor():
                    prompt_text = f"Extruder: {self.get_current_channel()}"
                    for slot in result:
                        if self.get_current_channel() == int(slot['ID']):
                            prompt_text = f"Extruder: {slot['ID']}: {slot['Material']}/{slot['Color']}"
                            break

                gcmd.respond_raw(f"// action:prompt_text {fname} | {prompt_text}")

                gcmd.respond_raw("// action:prompt_button_group_start")
                color = "006400" if leveling == 1 else "808080"
                gcmd.respond_raw(f"// action:prompt_button {leveling_text}|SET_ZCOLOR SILENT={silent} FILENAME=\"{fname}\" LEVELING={int(not leveling)} ALLOWED_TOOL_COUNT={allowed_tool_count} {current_tools_param_text}| |{color}")
                auto_prompt = f"// action:prompt_button {self._t('auto_select_colors')}|SET_ZCOLOR SILENT={silent} AUTO_ASSIGN=1 FILENAME=\"{fname}\" LEVELING={leveling} ALLOWED_TOOL_COUNT={allowed_tool_count} {current_tools_param_text}| "
                color = "202020" if auto_assign == 0 else \
                        "EE0000" if (auto_result & AUTO_ASSIGN_ANY_SUCCESS) == 0 or (auto_result & (AUTO_ASSIGN_MATERIAL_FAILURE | AUTO_ASSIGN_COLOR_FAILURE)) != 0 else \
                        "AAAA00" if (auto_result & (AUTO_ASSIGN_COLOR_WEAK | AUTO_ASSIGN_DUPLICATE)) != 0 else \
                        "00DD00"
                gcmd.respond_raw(f"{auto_prompt}|{color}")
                gcmd.respond_raw("// action:prompt_button_group_end")

                # gcmd.respond_raw(f"// action:prompt_text {self._t('prompt_map_color')}")

                buttons_per_group = 4
                if len(color_indexes) < 10:
                    buttons_per_group = 3
                if len(color_indexes) < 7:
                    buttons_per_group = 2

                button_index = 0

                for tool_idx, tool_val in enumerate(tools):
                    if tool_idx not in color_indexes:
                        continue
                    if button_index % buttons_per_group == 0:
                        gcmd.respond_raw("// action:prompt_button_group_start")
                    for slot_info in result:
                        if int(slot_info['ID']) != tool_val:
                            continue
                        color_name = slot_info['Color'].replace('_', '/', 1) if slot_info['Color'].startswith('_') else ''

                        tool_name = f"T{tool_idx}" if not one_based_indexes else str(tool_idx+1)

                        btn_text = (
                            f"{tool_name} -> "
                            f"{slot_info['ID']}: "
                            f"{slot_info['Material']}{color_name}"
                        )
                        params = f"LEVELING={leveling} FILENAME=\"{fname}\" ALLOWED_TOOL_COUNT={allowed_tool_count} {current_tools_param_text}"

                        gcmd.respond_raw(
                            f"// action:prompt_button {btn_text}|"
                            f"CHANGE_T_ZCOLOR T={tool_idx} {params}|primary|{slot_info['HEX']}"
                        )
                    if button_index % buttons_per_group == (buttons_per_group - 1) or tool_idx == allowed_tool_count - 1:
                        gcmd.respond_raw("// action:prompt_button_group_end")
                    button_index += 1

                gcmd.respond_raw(
                    f"// action:prompt_footer_button {self._t('send_print')}|"
                    f"PRINT_ZCOLOR LEVELING={leveling} FILENAME=\"{fname}\" ALLOWED_TOOL_COUNT={allowed_tool_count} "
                    f"{current_tools_param_text}|red"
                )
                gcmd.respond_raw(f"// action:prompt_footer_button {self._t('cancel')}|RESPOND TYPE=command MSG=action:prompt_end")
                gcmd.respond_raw("// action:prompt_show")

                for line in auto_selection_output_text:
                    gcmd.respond_raw(line)
            elif silent == 1:
                if auto_assign > 1:
                    # Success bit flag is ignored
                    # The rest is AND'd with the auto assign result, if this is non-zero, print is aborted
                    pass_check = ((auto_assign & ~AUTO_ASSIGN_ANY_SUCCESS) & (auto_result & ~AUTO_ASSIGN_ANY_SUCCESS))
                    if pass_check != 0:
                        for line in auto_selection_output_text:
                            gcmd.respond_raw(line)
                        raise gcmd.error(self._t('error_auto_assign_result', pass_check))

                gcmd.respond_raw(f"// {fname}")
                gcmd.respond_raw(f"// {leveling_text}")
                gcmd.respond_raw("// IFS ON // SAVE_ZMOD_DATA SILENT=1")
                if self.lang == 'ru':
                    gcmd.respond_raw("Скрыть выбор цвета, печатать с IFS")
                else:
                    gcmd.respond_raw("Hide color selection, print with IFS")
                for tool_idx, tool_val in enumerate(tools):
                    for slot_info in result:
                        if int(slot_info['ID']) != tool_val:
                            continue
                        if tool_idx not in [file_color[0] for file_color in self.file_colors]:
                            continue
                        gcmd.respond_raw(
                            f"T{tool_idx} -> "
                            f"{slot_info['ID']}: "
                            f"{slot_info['Material']}/{slot_info['Color']}"
                        )

                new_gcmd_params = {
                        'LEVELING': leveling, 'FILENAME': fname, 'ALLOWED_TOOL_COUNT': allowed_tool_count
                        }

                for i in range(len(tools)):
                    new_gcmd_params[f"T{i}"] = tools[i]

                gcmd2 = self.gcode.create_gcode_command("PRINT_ZCOLOR", "PRINT_ZCOLOR", new_gcmd_params)
                self.cmd_PRINT_ZCOLOR(gcmd2)
            elif silent == 2:
                self.gcode.run_script_from_command(f"SAVE_VARIABLE VARIABLE=print_leveling VALUE={leveling}")
                gcmd.respond_raw(f"// {fname}")
                gcmd.respond_raw(f"// {leveling_text}")
                gcmd.respond_raw("// IFS OFF // SAVE_ZMOD_DATA SILENT=2")
                gcmd.respond_raw(self._t('hide_color_selection'));
                if self.display:
                    data = {
                        "fileName": fname,
                        "levelingBeforePrint": bool(leveling),
                        "flowCalibration": True,
                        "useMatlStation": False
                    }
                    status_code2, response_data2 = self.zsend_post_request("/printGcode", send_data=data)
                    if status_code2 == 200:
                        gcmd.respond_raw(f"Status: {response_data2.get('msg', 'OK')}")
                    else:
                        gcmd.respond_raw(self._t('printing_error', response_data2))
                else:
                    gcmd.respond_raw(f"IFS Off")
                    self.gcode.run_script_from_command("_IFS_OFF")
                    self.gcode.run_script_from_command(f"SDCARD_PRINT_FILE FILENAME=\"{fname}\"")
        else:
            gcmd.respond_raw(self._t('no_response', json.dumps(response_data)))

    def find_t_code(self, filename):
        pattern = re.compile(r'^T([1-9]?[0-9])')

        with open(f"{self.virtual_sd.sdcard_dirname}/{filename}", 'r', encoding='utf-8') as file:
            for i, line in enumerate(file):
                if i > 3000:
                    break;
                stripped_line = line.strip()
                match = pattern.match(stripped_line)
                if match:
                    channel_num = match.group(1)
                    self.gcode.run_script_from_command(f"SET_CURRENT_PRUTOK CHANNEL={channel_num}")
                    return
        self.gcode.run_script_from_command("SET_CURRENT_PRUTOK CHANNEL=0")

    def cmd_PRINT_ZCOLOR(self, gcmd):
        gcmd.respond_raw("// action:prompt_end")
        fname = gcmd.get('FILENAME', '')
        if fname == '':
            raise gcmd.error(self._t('error_no_filename'))

        leveling = gcmd.get_int('LEVELING', 0)
        if leveling not in (0, 1):
            raise gcmd.error(self._t('error_leveling', leveling))

        if self.display:
            status_code, response_data = self.zsend_post_request("/detail")
        else:
            status_code, response_data = self.get_printer_data_detail()
        if status_code:
            allowed_tool_count = gcmd.get_int('ALLOWED_TOOL_COUNT', self.get_allowed_tool_count(gcmd))
            result = self.parse_printer_response(response_data)

            default_values = [result[i]['ID'] if i < len(result) else result[-1]['ID'] for i in range(allowed_tool_count)] if result else [1] * allowed_tool_count

            tools = []
            for i in range(allowed_tool_count):
              tools += [gcmd.get_int(f"T{i}", int(default_values[i]))]

            for i, tool in enumerate(tools):
                if tool < 1 or tool > 4:
                    raise gcmd.error(self._t('error_tool', i, tool))

            material_mappings = []

            for tool_idx, tool_val in enumerate(tools):
                for slot_info in result:
                    if int(slot_info['ID']) != tool_val:
                        continue
                    material_mappings.append({
                        "toolId": tool_idx,
                        "slotId": slot_info['ID'],
                        "materialName": slot_info['Material'],
                        "toolMaterialColor": f"#{slot_info['HEX']}",
                        "slotMaterialColor": f"#{slot_info['HEX']}"
                    })

            self.gcode.run_script_from_command(f"SAVE_VARIABLE VARIABLE=print_leveling VALUE={leveling}")
            if self.display:
                if any(file_color[0] > 3 for file_color in self.file_colors):
                    raise gcmd.error(self._t('error_native_screen_tool_count', len(self.file_colors))) # We should never actually get here with >4 colors. But this check is here just in case.
                data = {
                    "fileName": fname,
                    "levelingBeforePrint": bool(leveling),
                    "flowCalibration": True,
                    "useMatlStation": True,
                    "gcodeToolCnt": len(material_mappings),
                    "materialMappings": material_mappings
                }

                status_code2, response_data2 = self.zsend_post_request("/printGcode", send_data=data)
                if status_code2 == 200:
                    gcmd.respond_raw(f"Status: {response_data2.get('msg', 'OK')}")
                else:
                    gcmd.respond_raw(self._t('printing_error', response_data2))
            else:
                with open(FILE_CONFIG, 'w') as file:
                    json.dump(tools, file, indent=2)

                self.find_t_code(fname)
                self.gcode.run_script_from_command(f"SDCARD_PRINT_FILE FILENAME=\"{fname}\"")
        else:
            gcmd.respond_raw(self._t('no_response', json.dumps(response_data)))

    def cmd_CHANGE_FILAMENT(self, gcmd):
        channel = gcmd.get_int('CHANNEL', None)
        restore = gcmd.get_int('RESTORE', 1)

        if channel is None:
            raise gcmd.error("Error: CHANNEL parameter is required")
            return

        if not self.ifs:
            gcmd.respond_raw(f"info IFS: Off. T{channel} ignore")
            return
        gcmd.respond_raw(f"// T{channel}")

        try:
            with open(FILE_CONFIG, 'r') as f:
                mapping = json.load(f)

            if channel >= len(mapping):
                raise gcmd.error(f"Error: CHANNEL {channel} is out of range (max {len(mapping)-1})")
                return

            spool_number = mapping[channel]
            current_spool_number = self.get_current_channel()

            full_color_change = True
            if self.get_extruder_sensor() and spool_number == current_spool_number:
                save_variables = self.printer.lookup_object('save_variables', None)
                save_variables = {} if save_variables == None else save_variables.allVariables
                if save_variables.get('always_full_color_change', 0) == 0:
                    full_color_change = False

            if full_color_change:
                self.gcode.run_script_from_command(f"INSERT_PRUTOK_IFS PRUTOK={spool_number} NEED_STOP=0 TRASH=0")
            else:
                gcmd.respond_raw(f"Current Prutok = Prutok = {spool_number}")
            self.gcode.run_script_from_command("END_CHANGE_FILAMENT")

        except Exception as e:
            if restore == 1:
                if self.lang == 'ru':
                    msg = f"!! Ошибка при смене филамента: {str(e)}\nВстаю на паузу"
                else:
                    msg = f"!! Filament change error: {str(e)}\nPausing print"
                gcmd.respond_raw(f"{msg}")
                gcmd.respond_raw(f"tgalarm_photo {msg}")
                try:
                    self.gcode.run_script_from_command("IFS_F112")
                    self.gcode.run_script_from_command("IFS_F18")
                except:
                    pass
                pause_resume = self.printer.lookup_object('pause_resume')
                pause_resume.send_pause_command()
                self.gcode.run_script_from_command("PAUSE\nM400\n")
            else:
                if self.lang == 'ru':
                    msg = f"!! Ошибка при смене филамента: {str(e)}\nПечать отменена"
                else:
                    msg = f"!! Filament change error: {str(e)}\nPrint cancelled"
                gcmd.respond_raw(f"{msg}")
                gcmd.respond_raw(f"tgalarm_photo {msg}")
                raise

    def cmd_CHANGE_T_ZCOLOR(self, gcmd):
        save_variables = self.printer.lookup_object('save_variables', None)
        save_variables = {} if save_variables == None else save_variables.allVariables

        one_based_indexes = (save_variables.get('color_menu_1_based', 0) != 0)

        gcmd.respond_raw("// action:prompt_end")
        fname = gcmd.get('FILENAME', '')
        if fname == '':
            raise gcmd.error(self._t('error_no_filename'))

        leveling = gcmd.get_int('LEVELING', 0)
        if leveling not in (0, 1):
            raise gcmd.error(self._t('error_leveling', leveling))

        if self.display:
            status_code, response_data = self.zsend_post_request("/detail")
        else:
            status_code, response_data = self.get_printer_data_detail()
        if status_code:
            allowed_tool_count = gcmd.get_int('ALLOWED_TOOL_COUNT', self.get_allowed_tool_count(gcmd))
            result = self.parse_printer_response(response_data)
#            gcmd.respond_raw(json.dumps(response_data, indent=2))

            default_values = [result[i]['ID'] if i < len(result) else result[-1]['ID'] for i in range(allowed_tool_count)] if result else [1] * allowed_tool_count
            tools = []
            for i in range(allowed_tool_count):
              tools += [gcmd.get_int(f"T{i}", int(default_values[i]))]

            for i, tool in enumerate(tools):
                if tool < 1 or tool > 4:
                    raise gcmd.error(self._t('error_tool', i, tool))

            ztool = gcmd.get_int('T', 0)
            if ztool < 0 or ztool >= allowed_tool_count:
                raise gcmd.error(self._t('error_tool', '', ztool))

            params = f"FILENAME=\"{fname}\" LEVELING={leveling} ALLOWED_TOOL_COUNT={allowed_tool_count}"
            for i in range(allowed_tool_count):
                if i == ztool:
                    continue
                params += f" T{i}={tools[i]}"

            gcmd.respond_raw(f"// action:prompt_begin {self._t('prompt_material')}")
            gcmd.respond_raw(f"// action:prompt_text {fname}")

            gcmd.respond_raw(f"// action:prompt_text {self._t('prompt_map_color')}")

            tool_label = f"T{ztool}" if not one_based_indexes else f"Color {ztool+1}"
            gcmd.respond_raw(f"// action:prompt_text {tool_label}:")

            gcmd.respond_raw("// action:prompt_button_group_start")
            for slot in result:
                color_name = slot['Color'].replace('_', '/', 1) if slot['Color'].startswith('_') else ''
                btn_text = (
                    f"{slot['ID']}: "
                    f"{slot['Material']}{color_name}"
                )
                gcmd.respond_raw(
                    f"// action:prompt_button {btn_text}|"
                    f"SET_ZCOLOR T{ztool}={slot['ID']} {params}|primary|{slot['HEX']}"
                )

            gcmd.respond_raw("// action:prompt_button_group_end")
            gcmd.respond_raw(
                f"// action:prompt_footer_button {self._t('cancel')}|"
                f"SET_ZCOLOR T{ztool}={tools[ztool]} {params}"
            )
            gcmd.respond_raw("// action:prompt_show")
        else:
            gcmd.respond_raw(self._t('no_response', json.dumps(response_data)))

    def cmd_RUN_ZCOLOR(self, gcmd):
        gcmd.respond_raw("// action:prompt_end")
        zslot = gcmd.get_int('SLOT', 0)
        if zslot < 0 or zslot > 4:
            raise gcmd.error(self._t('error_slot'))

        zhex = gcmd.get('HEX', '161616').upper()
        ztype = gcmd.get('TYPE', '').upper()
        hide = gcmd.get_int('HIDE', 0)

        if hide == 1:
            if self.display:
                status_code, response_data = self.zsend_post_request("/detail")
            else:
                status_code, response_data = self.get_printer_data_detail()
            if status_code:
                for slot in result:
                    if zslot == slot['ID']:
                        zhex = slot['HEX']
                        ztype = slot['Material']
                        break;
            else:
                gcmd.respond_raw(self._t('no_response', json.dumps(response_data)))
        else:

        color_name = self.COLOR_MAPPING.get(zhex.lower(), zhex)

        if ztype not in self.valid_types:
            raise gcmd.error(self._t('error_type', ztype, ', '.join(self.valid_types[:-1])))

        gcmd.respond_raw(f"// action:prompt_begin {self._t('select_action')}")

        gcmd.respond_raw(f"// action:prompt_text {self._t('spool_info', zslot, ztype, color_name)}")

        gcmd.respond_raw("// action:prompt_button_group_start")
        gcmd.respond_raw(
            f"// action:prompt_button {self._t('change_color')}|"
            f"CHANGE_ZCOLOR SLOT={zslot} TYPE={ztype}|primary|{zhex}"
        )
        gcmd.respond_raw(
            f"// action:prompt_button {self._t('change_type')}|"
            f"CHANGE_ZCOLOR SLOT={zslot} HEX={zhex}|primary"
        )

        if hide == 0:
            gcmd.respond_raw(
                f"// action:prompt_button {self._t('load')}|"
                f"IN_ZCOLOR SLOT={zslot} NAPR=0|primary"
            )
            gcmd.respond_raw(
                f"// action:prompt_button {self._t('unload')}|"
                f"IN_ZCOLOR SLOT={zslot} NAPR=1|primary"
            )
        gcmd.respond_raw("// action:prompt_button_group_end")

        gcmd.respond_raw(f"// action:prompt_footer_button {self._t('cancel')}|RESPOND TYPE=command MSG=action:prompt_end")
        gcmd.respond_raw("// action:prompt_show")

    def cmd_CHANGE_ZCOLOR(self, gcmd):
        gcmd.respond_raw("// action:prompt_end")
        zslot = gcmd.get_int('SLOT', 0)
        if zslot < 0 or zslot > 4:
            raise gcmd.error(self._t('error_slot'))

        zhex = gcmd.get('HEX', '').upper()
        ztype = gcmd.get('TYPE', '').upper()

        if not zhex and not ztype:
            raise gcmd.error(self._t('error_color_or_type'))

        if zhex and ztype:
            if ztype == '?':
                ztype = 'PLA'
            if ztype not in self.valid_types:
                raise gcmd.error(self._t('error_type', ztype, ', '.join(self.valid_types[:-1])))

            if zslot!=0:
                payload = {
                    "cmd": "msConfig_cmd",
                    "args": {
                        "slot": zslot,
                        "mt": ztype,
                        "rgb": f"#{zhex}"
                    }
                }
            else:
                payload = {
                    "cmd": "ipdMsConfig_cmd",
                    "args": {
                        "mt": ztype,
                        "rgb": f"#{zhex}"
                    }
                }

            if self.display:
                status_code, response_data = self.zsend_post_request("/control", payload=payload)
            else:
                status_code, response_data = self.set_printer_data_detail(zslot, ztype, f"#{zhex}")
            if status_code == 200:
                self.cmd_GET_ZCOLOR(gcmd)
                gcmd.respond_raw(self._t('config_success'))
            else:
                gcmd.respond_raw(self._t('config_error', json.dumps(response_data)))
            return

        if ztype:
            if ztype == '?':
                ztype = 'PLA'
            if ztype not in self.valid_types:
                raise gcmd.error(self._t('error_type', ztype, ', '.join(self.valid_types[:-1])))

            gcmd.respond_raw(f"// action:prompt_begin {self._t('select_color')}")
            gcmd.respond_raw(f"// action:prompt_text {self._t('spool_info', zslot, ztype, '')}")
            gcmd.respond_raw("// action:prompt_button_group_start")
            counter = 0
            total_colors = len(self.COLOR_MAPPING)
            for hex_code, color_name in self.COLOR_MAPPING.items():
                color_name = color_name.replace('_', '', 1) if color_name.startswith('_') else '_'
                gcmd.respond_raw(
                    f"// action:prompt_button {color_name} |"
                    f"CHANGE_ZCOLOR SLOT={zslot} TYPE={ztype} HEX={hex_code}|primary|{hex_code}"
                )
                counter += 1
                if counter % 8 == 0 and counter < total_colors:
                    gcmd.respond_raw("// action:prompt_button_group_end")
                    gcmd.respond_raw("// action:prompt_button_group_start")
            gcmd.respond_raw("// action:prompt_button_group_end")
            gcmd.respond_raw(f"// action:prompt_footer_button {self._t('cancel')}|RESPOND TYPE=command MSG=action:prompt_end")
            gcmd.respond_raw("// action:prompt_show")

        if zhex:
            color_name = self.COLOR_MAPPING.get(zhex.lower(), zhex)
            gcmd.respond_raw(f"// action:prompt_begin {self._t('select_type')}")
            gcmd.respond_raw(f"// action:prompt_text {self._t('spool_info', zslot, '', color_name)}")
            gcmd.respond_raw("// action:prompt_button_group_start")
            counter = 0
            total_materials = len(self.valid_types) - 1  # Исключаем '?'
            for material in self.valid_types[:-1]:  # Исключаем '?'
                gcmd.respond_raw(
                    f"// action:prompt_button {material}|"
                    f"CHANGE_ZCOLOR SLOT={zslot} TYPE={material} HEX={zhex}|primary|{zhex}"
                )
                counter += 1
                if counter % 4 == 0 and counter < total_materials:
                    gcmd.respond_raw("// action:prompt_button_group_end")
                    gcmd.respond_raw("// action:prompt_button_group_start")
            gcmd.respond_raw("// action:prompt_button_group_end")
            gcmd.respond_raw(f"// action:prompt_footer_button {self._t('cancel')}|RESPOND TYPE=command MSG=action:prompt_end")
            gcmd.respond_raw("// action:prompt_show")

    # Загрузка выгрузка филамента
    def cmd_IN_ZCOLOR(self, gcmd):
        gcmd.respond_raw("// action:prompt_end")
        zslot = gcmd.get_int('SLOT', 0)
        if zslot < 0 or zslot > 4:
            raise gcmd.error(self._t('error_slot'))

        napr = gcmd.get_int('NAPR', 0)
        if napr not in (0, 1):
            raise gcmd.error(self._t('error_napr'))

        if self.display:
            action = "load" if napr == 0 else "unload"
            if zslot != 0:
                payload = {
                    "cmd": "ms_cmd",
                    "args": {
                        "slot": zslot,
                        "action": napr
                    }
                }
            else:
                payload = {
                    "cmd": "ipdMs_cmd",
                    "args": {
                        "action": napr
                    }
                }

            status_code, response_data = self.zsend_post_request("/control", payload=payload)
            if status_code == 200:
                gcmd.respond_raw(self._t(f'{action}_success'))
            else:
                gcmd.respond_raw(self._t(f'{action}_error', json.dumps(response_data)))
        else:
            if napr == 0:
                self.gcode.run_script_from_command(f"INSERT_PRUTOK_IFS PRUTOK={zslot} TRASH=1")
            else:
                self.gcode.run_script_from_command(f"REMOVE_PRUTOK_IFS PRUTOK={zslot}")

def load_config(config):
    return zmod_color(config)
