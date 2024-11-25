# Патч обезьяны для функционирования импортируемых модулей python асинхронно
import gevent.monkey

gevent.monkey.patch_all()

from flask import Flask, request, send_from_directory, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

import argparse
import os
import signal

import sqlite3
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

from gevent import subprocess, spawn
from gevent.subprocess import check_output

import pandas as pd

import datetime
from dateutil.parser import parse

import json
import re
import shutil
import time

from utils.correct_start import check_correct_application_structure
import utils.constants_and_paths as constants
import utils.routine_operations as operations
import utils.client_operations as client_operations
import utils.create_dataframe_reports as create_reports

from jinja.pylib.get_template import render_slice, render_grid, render_bounce

from loguru import logger

from typing import Dict, List, Tuple, Union

VERSION = '1.0.3'

clients = {}

app = Flask(__name__, static_folder="./web", template_folder="./web", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Переменная под идентификатор сокета (sid), вызывающего процесс
sid_proc = None

# Переменная под объект гринлета обновления тегов
update_greenlet = None
# Переменная под объект гринлета изменения обновлененного файла тегов на основе списка исключений
change_update_greenlet = None
# Переменная под объект модуля subprocess процесса обновления тегов
p_kks_all = None
# Переменная под объект гринлета выполнения запроса по срезам тегов
signals_greenlet = None
# Переменная под объект гринлета выполнения запроса сетки
grid_greenlet = None
# Переменная под объект гринлета выполнения запроса дребезга
bounce_greenlet = None


@app.route("/", defaults={"path": ""})
@app.route("/<string:path>")
@app.route("/<path:path>")
def catch_all(path):
    return app.send_static_file("index.html")


@app.route('/api_urls.js')
def get_api_urls_js():
    """
    Функция посылки js файла с URL бэкенда
    :return: ./web/api_urls.js
    """
    return send_file('./web/api_urls.js')


@app.route('/bootstrap/dist/css/bootstrap.min.css')
def get_bootstrap_css():
    """
    Функция запроса файла bootstrap.css
    :return: Возвращает файл bootstrap.css в header html
    """
    logger.info(f"get_bootstrap_css()")
    logger.info(f"get style bootstrap/dist/css/bootstrap.css")
    return send_from_directory('static/bootstrap/dist/css/', 'bootstrap.min.css')


@app.route('/bootstrap/dist/js/bootstrap.bundle.min.js')
def get_bootstrap_js():
    """
    Функция запроса скрипта bootstrap.bundle.min.js
    :return: Возвращает скрипт bootstrap.bundle.min.js в html
    """
    logger.info(f"get_bootstrap_js()")
    logger.info(f"get script /bootstrap/dist/js/bootstrap.bundle.min.js")
    return send_from_directory('static/bootstrap/dist/js/', 'bootstrap.bundle.min.js')


@app.route('/plotly.js-dist-min/plotly.min.js')
def get_plotly_js():
    """
    Функция запроса скрипта plotly.min.js
    :return: Возвращает скрипт plotly.min.js в html
    """
    logger.info(f"get_plotly_js()")
    logger.info(f"get script /plotly.js-dist-min/plotly.min.js")
    return send_from_directory('static/plotly.js-dist-min/', 'plotly.min.js')


@app.route("/tags.csv")
def get_tags_csv():
    return send_file(constants.CSV_TAGS)


@app.route("/signals_slice.csv")
def get_signals_slice_csv():
    return send_file(constants.CSV_SIGNALS)


@app.route("/code.csv")
def get_code_csv():
    return send_file(constants.CSV_CODE)


@app.route("/grid.csv")
def get_grid_csv():
    return send_file(constants.CSV_GRID)


@app.route("/bounce.csv")
def get_bounce_csv():
    return send_file(constants.CSV_BOUNCE)


@app.route("/config.json")
def get_config_json():
    return send_file(constants.CONFIG)


@app.route("/signals_slice.pdf")
def get_signals_slice_pdf():
    return send_file(constants.REPORT_SLICE)


@app.route("/grid.zip")
def get_grid_zip():
    return send_file(constants.REPORT_GRID_ZIP)


@app.route("/bounce.pdf")
def get_bounce_pdf():
    return send_file(constants.REPORT_BOUNCE)


@socketio.on("connect")
def connect():
    """
    Процедура регистрирует присоединение нового клиента и открытие сокета
    :return:
    """
    clients[request.sid] = request.sid
    logger.info("connect")
    logger.info(request.sid)


@socketio.on("disconnect")
def disconnect():
    """
    Процедура регистрирует разъединение клиента и закрытие сокета
    :return:
    """
    del clients[request.sid]
    logger.info("disconnect")
    logger.info(request.sid)


@socketio.on("get_file_checked")
def get_file_checked() -> Tuple[bool, str, bool]:
    """
    Функция возвращает результат проверки существования файла тегов kks_all.csv или верность настройки клиента Clickhouse
    :return: True/False результат проверки существования файла тегов kks_all.csv
    """
    logger.info(f"get_file_checked()")

    global CLIENT_MODE

    client_status = False
    ip, port, username, password = client_operations.read_clickhouse_server_conf()
    try:
        client = client_operations.create_client(ip, port, username, password)
        logger.info("Clickhouse connected")
        client_status = True
        client.close()
        logger.info("Clickhouse disconnected")
    except clickhouse_exceptions.Error as error:
        logger.error(error)

    return os.path.isfile(constants.DATA_KKS_ALL), CLIENT_MODE, client_status


@socketio.on("get_client_mode")
def get_client_mode() -> str:
    """
    Функция возвращает выбранный режим работы клиента
    :return: строка ('OPC'/'CH') наименования выбранного режима клиента
    """
    logger.info(f"get_client_mode()")
    global CLIENT_MODE

    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)
        CLIENT_MODE = config["mode"]
        logger.info(CLIENT_MODE)

    return CLIENT_MODE


@socketio.on("change_client_mode")
def change_client_mode(client_mode: str) -> Union[None, str]:
    """
    Процедура записывает в файл выбранный режим работы клиента
    :param client_mode: строка ('OPC'/'CH') наименования выбранного режима клиента
    :return:
    """
    logger.info(f"change_client_mode()")

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"started_greenlet is running")
        return f"Выполняется запрос для другого клиента. Изменение режима клиента временно невозможно"

    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)

    config["mode"] = client_mode

    with open(constants.CONFIG, "w") as write_config:
        json.dump(config, write_config, indent=4)


@socketio.on("get_server_config")
def get_server_config() -> Tuple[str, bool]:
    """
    Функция возвращает конфигурацию клиента OPC UA или Clickhouse
    :return: строка конфигурации клиента OPC UA, True/False результат проверки существования файла тегов kks_all.csv
    """
    logger.info(f"get_server_config()")
    global CLIENT_MODE
    sid = request.sid

    if CLIENT_MODE == 'OPC':
        with open(constants.CLIENT_SERVER_CONF, "r") as readfile:
            server_config = readfile.readline()
            logger.info(server_config)

        return f'Текущая конфигурация клиента OPC UA: {server_config}', os.path.isfile(constants.DATA_KKS_ALL)

    if CLIENT_MODE == 'CH':
        ip, port, username, password = client_operations.read_clickhouse_server_conf()
        host = f"{ip}:{port}"

        client = client_operations.get_client(sid, socketio, ip, port, username, password)
        try:
            check = client.command("CHECK TABLE archive.static_data")
            client.close()
            logger.info("Clickhouse disconnected")
            return f'Текущая конфигурация клиента CH: {host}, {username}', bool(check)
        except AttributeError as attr_error:
            logger.error(attr_error)
            return client, os.path.isfile(constants.DATA_KKS_ALL)
        except clickhouse_exceptions.Error as error:
            logger.error(error)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"{error}\n", "serviceFlag": False},
                          to=sid)

    return f'Конфигурация клиента не обнаружена!!!', os.path.isfile(constants.DATA_KKS_ALL)


@socketio.on("get_last_update_file_kks")
def get_last_update_file_kks() -> str:
    """
    Функция возвращает дату последнего обновления файла тегов kks_all.csv или таблицы clickhouse
    :return: строка даты последнего обновления файла тегов kks_all.csv или таблицы clickhouse
    """
    logger.info(f"get_last_update_file_kks()")

    global CLIENT_MODE
    sid = request.sid

    if CLIENT_MODE == 'OPC':
        current_path = constants.DATA_KKS_ALL

        if not os.path.isfile(current_path):
            return f"Файл {current_path} не найден"
        logger.info(str(datetime.datetime.fromtimestamp(os.path.getmtime(current_path)).strftime('%Y-%m-%d %H:%M:%S')))
        return str(datetime.datetime.fromtimestamp(os.path.getmtime(current_path)).strftime('%Y-%m-%d %H:%M:%S'))

    if CLIENT_MODE == 'CH':
        ip, port, username, password = client_operations.read_clickhouse_server_conf()

        client = client_operations.get_client(sid, socketio, ip, port, username, password)
        try:
            logger.info("Clickhouse connected")
            modify_time = client.command("SELECT table, metadata_modification_time FROM system.tables "
                                         "WHERE table = 'static_data'")
            logger.info(modify_time[1])
            client.close()
            logger.info("Clickhouse disconnected")
            return modify_time[1]
        except AttributeError as attr_error:
            logger.error(attr_error)
            return client
        except clickhouse_exceptions.Error as error:
            logger.error(error)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"{error}\n", "serviceFlag": False},
                          to=sid)

    return 'Ошибка конфигурации клиента'


@socketio.on("get_ip_port_config")
def get_ip_port_config() -> Tuple[str, int, str, int, str, str]:
    """
    Функция возвращает ip-адрес и порт клиента OPC UA
    :return: строка ip-адресс, строка порта
    """
    logger.info(f"get_ip_port_config()")
    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)
        opc_config = config["opc"]
        logger.info(opc_config)

    ip, port = opc_config["ip"], opc_config["port"]

    ip_ch, port_ch, username, password = client_operations.read_clickhouse_server_conf()
    return ip, port, ip_ch, port_ch, username, password


@socketio.on("get_default_fields")
def get_default_fields() -> Union[Dict[str, Union[str, int, bool, List[str]]], str]:
    """
    Функция возвращает конфигурацию вводимых полей для запроса по умолчанию
    :return: json объект полей по умочанию
    """
    logger.info(f"get_default_fields()")

    global CLIENT_MODE

    try:
        f = open(constants.CONFIG)
    except FileNotFoundError as file_not_found_error_exception:
        logger.error(file_not_found_error_exception)
        default_config_error = f"Файл {constants.CONFIG} не найден. " \
                               f"Установите параметры по умолчанию в конфигураторе"
        return default_config_error
    else:
        with f:
            default_config = json.load(f)
            if not default_config["fields"]:
                default_fields_error = f"Параметры по умолчанию пусты. Установите и сохраните " \
                                       f"параметры по умолчанию в конфигураторе"
                return default_fields_error
            default_fields = default_config["fields"]

    return default_fields[CLIENT_MODE]


@socketio.on("change_opc_server_config")
def change_opc_server_config(ip: str, port: int) -> Tuple[bool, str]:
    """
    Процедура заменяет строку конфигурации клиента OPC UA
    :param ip: ip-адресс
    :param port: порт
    """
    logger.info(f"change_opc_server_config({ip}, {port})")

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"started_greenlet is running")
        return True, f"Выполняется запрос для другого клиента. " \
                     f"Сохранение конфигурации клиента OPC UA временно невозможно"

    # Проверка правильности ввода ip адреса
    if not operations.validate_ip_address(ip):
        return False, ""

    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)

    opc_config = {"ip": ip, "port": port}
    config["opc"] = opc_config

    with open(constants.CONFIG, "w") as write_config:
        json.dump(config, write_config, indent=4)

    with open(constants.CLIENT_SERVER_CONF, "w") as writefile:
        writefile.write(f"opc.tcp://{ip}:{port}")

    with open(constants.CLIENT_SERVER_CONF, "r") as readfile:
        socketio.emit("setUpdateStatus", {"statusString": f"Конфигурация клиента OPC UA обновлена на: "
                                                          f"{readfile.read()}\n", "serviceFlag": False}, to=request.sid)
    return True, ""


@socketio.on("change_ch_server_config")
def change_ch_server_config(ip: str, port: int, username: str, password: str) -> Tuple[bool, str]:
    """
    Процедура заменяет строку конфигурации клиента БД CH
    :param ip: ip-адресс
    :param port: порт
    :param username: имя пользователя
    :param password: пароль
    """
    logger.info(f"change_ch_server_config({ip}, {port}, {username}, {password})")

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"started_greenlet is running")
        return True, f"Выполняется запрос для другого клиента. " \
                     f"Сохранение конфигурации клиента Clickhouse временно невозможно"

    # Проверка правильности ввода ip адреса
    if not operations.validate_ip_address(ip):
        return False, ""

    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)

    clickhouse_config = {
        "ip": ip,
        "port": port,
        "username": username,
        "password": password
    }
    config["clickhouse"] = clickhouse_config

    with open(constants.CONFIG, "w") as write_config:
        json.dump(config, write_config, indent=4)

    ip_ch, port_ch, active_user, password_ch = client_operations.read_clickhouse_server_conf()
    host = f"{ip_ch}:{port_ch}"
    socketio.emit("setUpdateStatus", {"statusString": f"Конфигурация клиента Clickhouse обновлена на: "
                                                      f"{host}, пользователь: {active_user}\n",
                                      "serviceFlag": False}, to=request.sid)
    return True, ""


@socketio.on("change_default_fields")
def change_default_fields(default_fields: dict) -> str:
    """
    Процедура сохраняет конфигурацию вводимых полей для запроса по умолчанию в конфиг json
    :param default_fields: json объект полей по умолчанию
    :return:
    """
    logger.info(f"change_default_fields({default_fields})")

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"started_greenlet is running")
        return f"Выполняется запрос для другого клиента. Сохранение параметров временно невозможно"

    global CLIENT_MODE

    # Приводим строку даты глубины поиска к формату без timezone
    default_fields["dateDeepOfSearch"] = default_fields["dateDeepOfSearch"][:-5]
    logger.info(default_fields)

    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)

    config["fields"][CLIENT_MODE] = default_fields

    with open(constants.CONFIG, "w") as write_config:
        json.dump(config, write_config, indent=4)

    logger.info(f"Файл {constants.CONFIG} был успешно сохранен")
    return ""


@socketio.on("upload_config")
def upload_config(file: dict) -> str:
    """
    Функция импортирует пользовательский конфиг
    :param file: json файл конфига
    :return: Строка сообщения об успехе импорта или ошибке
    """
    logger.info(file)

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"started_greenlet is running")
        return f"Выполняется запрос для другого клиента. Импорт конфига временно невозможен"

    try:
        config = json.loads(file.decode('utf-8'))
    except json.JSONDecodeError as json_error:
        logger.error(json_error)
        return f"Ошибка считывания конфига: {json_error}"
    logger.info(config)

    # Валидация пользовательского конфигурационного файла
    valid_flag, msg = operations.validate_imported_config(config)
    if not valid_flag:
        return f"Ошибка валидации пользовательского конфига: {msg}. Отмена импорта."

    with open(constants.CONFIG, "w") as write_config:
        json.dump(config, write_config, indent=4)

    logger.warning(config)

    return f"Конфиг импортирован. {msg}"


@socketio.on("get_types_of_sensors")
def get_types_of_sensors() -> List[str]:
    """
    Функция возвращает все типы данных тегов kks, найденных в файле тегов kks_all.csv
    :return: массив строк типов данных
    """
    logger.info(f"get_types_of_sensors()")

    global CLIENT_MODE

    if CLIENT_MODE == 'OPC':
        logger.info(KKS_ALL[1].dropna().unique().tolist())
        return KKS_ALL[1].dropna().unique().tolist()

    if CLIENT_MODE == 'CH':
        ip, port, username, password = client_operations.read_clickhouse_server_conf()
        try:
            client = client_operations.create_client(ip, port, username, password)
            logger.info("Clickhouse connected")
            types = client.query_df("SELECT DISTINCT data_type_name FROM archive.v_static_data")
            logger.info(types)
            client.close()
            logger.info("Clickhouse disconnected")
            return types['data_type_name'].tolist()
        except clickhouse_exceptions.Error as error:
            logger.error(error)
            return ['Ошибка конфигурации клиента']
    return ['Ошибка конфигурации клиента']


@socketio.on("get_kks_tag_exist")
def get_kks_tag_exist(kks_tag: str) -> bool:
    """
    Функция возвращает результат проверки наличия тега в файле тегов kks_all.csv или в Clickhouse
    :param kks_tag: проверяемый тег kks
    :return: True - тег в файле тегов kks_all.csv; False - тега не найден в файле тегов kks_all.csv или это шаблон маски
    """
    logger.info(f"get_kks_tag_exist({kks_tag})")

    global CLIENT_MODE

    if CLIENT_MODE == 'OPC':
        return kks_tag in KKS_ALL[0].values
    elif CLIENT_MODE == 'CH':
        ip, port, username, password = client_operations.read_clickhouse_server_conf()
        try:
            client = client_operations.create_client(ip, port, username, password)
            logger.info("Clickhouse connected")

            exist = client.command(f"WITH '{kks_tag}' as i_kks SELECT "
                                   f"EXISTS( SELECT 1 FROM archive.v_static_data "
                                   f"WHERE item_name = i_kks)::bool as EXIST")

            client.close()
            logger.info("Clickhouse disconnected")

            return exist
        except clickhouse_exceptions.Error as error:
            logger.error(error)
    else:
        return False


@socketio.on("get_kks_by_masks")
def get_kks_by_masks(types_list: List[str], mask_list: List[str]) -> List[Union[str, None]]:
    """
    Функция возвращает массив kks датчиков из файла тегов kks_all.csv или из Clickhouse по маске шаблона при поиске kks
    :param types_list: массив выбранных пользователем типов данных
    :param mask_list: массив маск шаблонов поиска regex
    :return: массив строк kks датчиков (чтобы не перегружать форму 10000)
    """
    logger.info(f"get_kks_by_masks({types_list}, {mask_list})")

    global CLIENT_MODE

    # Если маска пустая, то вовзвращаем пустой массив
    if not mask_list:
        return []

    # Если ведем в веб-приложении поиск тегов и очищаем всю строку поиска, то вовзвращаем пустой массив
    if mask_list[0] == '':
        return []

    if CLIENT_MODE == 'OPC':
        kks = KKS_ALL.copy(deep=True)

        kks = kks[kks[1].isin(types_list)]

        for mask in mask_list:
            kks = kks[kks[0].str.contains(mask, regex=True)]

        logger.info(len(kks[0].tolist()))
        return kks[0].tolist()[:constants.COUNT_OF_RETURNED_KKS]

    elif CLIENT_MODE == 'CH':
        ip, port, username, password = client_operations.read_clickhouse_server_conf()
        try:
            client = client_operations.create_client(ip, port, username, password)
            logger.info("Clickhouse connected")

            kks = client.query_df(f"WITH {mask_list} AS arr_reg , {types_list} AS arr_type "
                                  f"SELECT item_name  FROM archive.v_static_data "
                                  f"WHERE data_type_name in arr_type AND "
                                  f"length(multiMatchAllIndices(item_name, arr_reg)) = length(arr_reg)")

            client.close()
            logger.info("Clickhouse disconnected")

            return kks['item_name'].tolist()
        except clickhouse_exceptions.Error as error:
            logger.error(error)
    return []


@socketio.on("get_kks")
def get_kks(types_list: List[str], mask_list: List[str], kks_list: List[str], selection_tag: str = None) -> List[str]:
    """
    Функция возвращает массив kks датчиков из файла тегов kks_all.csv по маске шаблона.
    Используется при выполнеии запросов на бэкенде
    :param types_list: массив выбранных пользователем типов данных
    :param mask_list: массив маск шаблонов поиска regex
    :param kks_list: массив kks напрямую, указанные пользователем
    :param selection_tag: выбранный вид отбора тегов
    :return: массив строк kks датчиков для выполнения запроса
    """
    logger.info(f"get_kks({types_list} ,{mask_list}, {kks_list}, {selection_tag})")

    global CLIENT_MODE

    if CLIENT_MODE == 'OPC':
        return operations.get_kks_opc_ua(KKS_ALL, types_list, mask_list, kks_list, selection_tag)
    elif CLIENT_MODE == 'CH':
        return operations.get_kks_ch(types_list, mask_list, kks_list, selection_tag)


@socketio.on("update_kks_all")
def update_kks_all(mode: str, root_directory: str, exception_directories: List[str], exception_expert: bool) -> None:
    """
    Процедура запуска гринлета обновления файла тегов kks_all.csv
    :param mode: выбранный режим фильтрации обновления тегов
    :param root_directory: корневая папка
    :param exception_directories: список исключений
    :param exception_expert: флаг, исключения тегов, помеченных экспертом
    """
    logger.info(f"update_kks_all({mode}, {root_directory}, {exception_directories}, {exception_expert})")

    def update_kks_all_spawn(mode: str, root_directory: str,
                             exception_directories: List[str], exception_expert: bool) -> str:
        """
        Процедура запуска обновления файла тегов kks_all.csv
        :param mode: выбранный режим фильтрации обновления тегов
        :param root_directory: корневая папка
        :param exception_directories: список исключений
        :param exception_expert: флаг, исключения тегов, помеченных экспертом
        """
        logger.info(f"update_kks_all_spawn({mode}, {root_directory}, {exception_directories}, {exception_expert})")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        if mode == "historian":
            # root_directory = "all"
            root_directory = "begin"

        socketio.sleep(5)
        command_kks_all_string = ["./client", "-k", root_directory, "-c", "all", "-f", 'kks.csv']
        # command_tail_kks_all_string = f"wc -l {constants.CLIENT_KKS} && tail -1 {constants.CLIENT_KKS}"
        command_tail_kks_all_string = f"wc -l {constants.CLIENT_KKS} && tail -2 {constants.CLIENT_KKS} | head -1"
        logger.info(f'get from OPC_UA all kks and types')
        logger.info(command_kks_all_string)

        args = command_kks_all_string  # команда запуска процесса обновления
        args_tail = command_tail_kks_all_string  # команда получения последнего тега в файле kks_all.csv

        try:
            global p_kks_all
            out = open(f'client{os.sep}out.log', 'w')
            err = open(f'client{os.sep}err.log', 'w')
            p_kks_all = subprocess.Popen(args, stdout=out, preexec_fn=os.setsid,
                                         stderr=err, cwd=f"{os.getcwd()}{os.sep}client{os.sep}")
            socketio.sleep(10)  # даем небольшое время на наполнение временного файла тегов kks.csv

            # Если процесс завершается сразу, то скорее всего произошла ошибка
            if p_kks_all.poll() is not None:
                err.close()
                out.close()
                with open(f'client{os.sep}out.log', 'r') as err:
                    lines = err.read()
                logger.info(lines)
                lines_decode = str(lines)
                logger.info(lines_decode)
                # Выводим в веб-приложении ошибку
                socketio.emit("setUpdateStatus", {"statusString": f"Ошибка: {lines_decode}\n", "serviceFlag": True},
                              to=sid)
                return lines_decode

            # Ждем окончание процесса обновления тегов клиентом
            while p_kks_all.poll() is None:
                logger.info(p_kks_all)
                # Последний выкаченный тег
                p_tail = subprocess.Popen(args_tail, stdout=subprocess.PIPE, shell=True)
                out_tail, err_tail = p_tail.communicate()
                logger.warning(out_tail)
                logger.warning(out_tail.decode('utf-8'))
                records = out_tail.decode('utf-8').split('\n')
                count = records[0].split()[0]
                record = records[1].split(';')[0]
                socketio.emit("setUpdateStatus", {"statusString": f"{count}. {record} Успех\n", "serviceFlag": False},
                              to=sid)
                logger.info(f"{count}. {record} Успех\n")
                socketio.sleep(5)

            err.close()
            out.close()

            if p_kks_all.returncode != 0:
                with open(f'client{os.sep}out.log', 'r') as err:
                    lines = err.read()
                logger.info(lines)
                lines_decode = str(lines)
                logger.info(lines_decode)
                # Выводим в веб-приложении ошибку
                socketio.emit("setUpdateStatus", {"statusString": f"Ошибка: {lines_decode}\n", "serviceFlag": True},
                              to=sid)
                return lines_decode

            socketio.emit("setUpdateStatus", {"statusString": f"Последняя запись\n", "serviceFlag": True},
                          to=sid)
            p_tail = subprocess.Popen(args_tail, stdout=subprocess.PIPE, shell=True)
            out_tail, err_tail = p_tail.communicate()
            records = out_tail.decode('utf-8').split('\n')
            count = records[0].split()[0]
            record = records[1].split(';')[0]
            socketio.emit("setUpdateStatus", {"statusString": f"{count}. {record} Успех\n", "serviceFlag": True},
                          to=sid)
        except UnicodeError as decode_error:
            if p_kks_all:
                # Убиваем по групповому id, чтобы завершить все дочерние процессы
                os.killpg(os.getpgid(p_kks_all.pid), signal.SIGINT)
                p_kks_all = None
            # Если произошла ошибка во время декодировки тега, то ловим и выводим исключение
            logger.error(decode_error)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Ошибка во время выполнения процесса\nОшибка: {decode_error}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{decode_error}'
        except RuntimeError as run_time_exception:
            if p_kks_all:
                # Убиваем по групповому id, чтобы завершить все дочерние процессы
                os.killpg(os.getpgid(p_kks_all.pid), signal.SIGINT)
                p_kks_all = None
            # Если произошла ошибка во время выполнения процесса, то ловим и выводим исключение
            logger.error(run_time_exception)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Ошибка во время выполнения процесса\nОшибка: {run_time_exception}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{run_time_exception}'

        shutil.copy(constants.CLIENT_KKS, constants.DATA_KKS_ALL)  # копируем kks.csv в data/kks_all.csv
        shutil.copy(constants.CLIENT_KKS, constants.DATA_KKS_ALL_BACK)  # копируем kks.csv в data/kks_all_back.csv
        # Пытаемся загрузить kks_all.csv, если он существует в переменную
        try:
            global KKS_ALL
            global KKS_ALL_BACK
            KKS_ALL = pd.read_csv(constants.DATA_KKS_ALL, header=None, sep=';')
            KKS_ALL_BACK = pd.read_csv(constants.DATA_KKS_ALL_BACK, header=None, sep=';')
            if mode == "exception":
                for exception_directory in exception_directories:
                    KKS_ALL = KKS_ALL[~KKS_ALL[0].str.contains(exception_directory, regex=True)]
                KKS_ALL.to_csv(constants.DATA_KKS_ALL, header=None, sep=';', index=False)
                KKS_ALL = pd.read_csv(constants.DATA_KKS_ALL, header=None, sep=';')
        except re.error as regular_expression_except:
            logger.error(f"Неверный синтаксис регулярного выражения {regular_expression_except}")
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Неверный синтаксис регулярного выражения {regular_expression_except}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{regular_expression_except}'
        except FileNotFoundError as csv_exception:
            logger.error(csv_exception)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Ошибка при попытке загрузить файл kks_all.csv\nОшибка: {csv_exception}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{csv_exception}'

        socketio.emit("setUpdateStatus", {"statusString": f"Обновление тегов закончено\n", "serviceFlag": True},
                      to=sid)
        return f"Обновление тегов закончено\n"

    def update_from_ch_kks_all_spawn() -> str:
        """
        Процедура запуска обновления файла тегов kks_all.csv
        """
        logger.info(f"update_from_ch_kks_all_spawn()")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        ip, port, username, password = client_operations.read_clickhouse_server_conf()

        socketio.emit("setUpdateStatus",
                      {"statusString": f"соединение с Clickhouse...\n", "serviceFlag": True},
                      to=sid)
        client = client_operations.get_client(sid, socketio, ip, port, username, password)
        try:
            logger.info("Clickhouse connected")
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Соединение с Clickhouse успешно установлено\n", "serviceFlag": True},
                          to=sid)
            client.close()
            logger.info("Clickhouse disconnected")
        except AttributeError as attr_error:
            logger.info(attr_error)
            return client

        return f"Обновление тегов закончено\n"

    sid = request.sid
    # Запуск гринлета обновления тегов
    global update_greenlet
    global sid_proc
    global CLIENT_MODE
    # Если обновление уже идет, выводим в веб-приложении
    if update_greenlet:
        logger.warning(f"update_greenlet is running")
        socketio.emit("setUpdateStatus",
                      {"statusString": f"Обновление тегов уже было начато на сервере\n", "serviceFlag": True},
                      to=sid)
        return

    # Запуск процесса обновления тегов через gevent в зависимости от режима
    if CLIENT_MODE == 'OPC':
        # Валидация регулярных выражений
        if mode == "exception":
            try:
                for directory in exception_directories:
                    re.compile(directory)
            except re.error as regular_expression_except:
                logger.error(f"Неверный синтаксис регулярного выражения {regular_expression_except}")
                socketio.emit("setUpdateStatus",
                              {
                                  "statusString": f"Неверный синтаксис регулярного выражения {regular_expression_except}\n",
                                  "serviceFlag": True},
                              to=sid)
                return
        update_greenlet = spawn(update_kks_all_spawn, mode, root_directory, exception_directories, exception_expert)

    if CLIENT_MODE == 'CH':
        update_greenlet = spawn(update_from_ch_kks_all_spawn)

    gevent.joinall([update_greenlet])

    sid_proc = None


@socketio.on("update_cancel")
def update_cancel() -> None:
    """
    Процедура отмены процесса обновления и уничтожения гринлета gevent
    """
    logger.info(f"update_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if sid_proc != request.sid:
        return

    global update_greenlet
    global change_update_greenlet
    global p_kks_all
    if update_greenlet:
        if p_kks_all:
            # Убиваем по групповому id, чтобы завершить все дочерние процессы
            os.killpg(os.getpgid(p_kks_all.pid), signal.SIGINT)
            p_kks_all = None
        gevent.killall([update_greenlet])
        logger.info(f"update_greenlet убит")
        socketio.emit("setUpdateStatus",
                      {"statusString": f"Обновление тегов прервано пользователем\n", "serviceFlag": True},
                      to=request.sid)
        update_greenlet = None

    if change_update_greenlet:
        gevent.killall([change_update_greenlet])
        logger.info(f"change_update_greenlet убит")
        socketio.emit("setUpdateStatus",
                      {"statusString": f"Применение списка исключений прервано пользователем\n", "serviceFlag": True},
                      to=request.sid)
        change_update_greenlet = None


@socketio.on("change_update_kks_all")
def change_update_kks_all(root_directory: str, exception_directories: List[str], exception_expert: bool) -> None:
    """
    Процедура применения списка исключений к уже обновленному файлу тегов
    :param root_directory: корневая папка
    :param exception_directories: список исключений
    :param exception_expert: флаг, исключения тегов, помеченных экспертом
    """
    logger.info(f"change_update_kks_all({root_directory}, {exception_directories}, {exception_expert})")

    def change_update_kks_all_spawn(root_directory: str,
                                    exception_directories: List[str], exception_expert: bool) -> str:
        """
        Процедура применения списка исключений к уже обновленному файлу тегов
        :param root_directory: корневая папка
        :param exception_directories: список исключений
        :param exception_expert: флаг, исключения тегов, помеченных экспертом
        """
        logger.info(f"change_update_kks_all_spawn({root_directory}, {exception_directories}, {exception_expert})")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        socketio.emit("setUpdateStatus",
                      {"statusString": f"Применение списка исключений к уже обновленному файлу тегов\n",
                       "serviceFlag": False}, to=sid)
        try:
            global KKS_ALL
            global KKS_ALL_BACK
            KKS_ALL = KKS_ALL_BACK.copy(deep=True)
            logger.info(KKS_ALL)
            KKS_ALL = KKS_ALL[KKS_ALL[0].str.contains(root_directory, regex=True)]
            logger.info(KKS_ALL)
            for exception_directory in exception_directories:
                KKS_ALL = KKS_ALL[~KKS_ALL[0].str.contains(exception_directory, regex=True)]
                logger.info(KKS_ALL)
            KKS_ALL.to_csv(constants.DATA_KKS_ALL, header=None, sep=';', index=False)
            KKS_ALL = pd.read_csv(constants.DATA_KKS_ALL, header=None, sep=';')
        except re.error as regular_expression_except:
            logger.error(f"Неверный синтаксис регулярного выражения {regular_expression_except}")
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Неверный синтаксис регулярного выражения {regular_expression_except}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{regular_expression_except}'
        except FileNotFoundError as csv_exception:
            logger.error(csv_exception)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Ошибка при попытке загрузить файл kks_all.csv\nОшибка: {csv_exception}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{csv_exception}'
        socketio.emit("setUpdateStatus", {"statusString": f"Применение списка исключений успешно завершено\n",
                                          "serviceFlag": False}, to=sid)

    sid = request.sid

    # Запуск гринлета обновления тегов
    global change_update_greenlet
    global sid_proc
    # Если обновление уже идет, выводим в веб-приложении
    if change_update_greenlet:
        logger.warning(f"change_update_greenlet is running")
        socketio.emit("setUpdateStatus",
                      {"statusString": f"Обновление тегов уже было начато на сервере\n", "serviceFlag": True},
                      to=sid)
        return

    # Запуск изменения обновленного файла тегов на основе списка исключений через gevent
    change_update_greenlet = spawn(change_update_kks_all_spawn, root_directory, exception_directories, exception_expert)
    gevent.joinall([change_update_greenlet])

    sid_proc = None


@socketio.on("get_signals_data")
def get_signals_data(types_list: List[str], selection_tag: str,
                     mask_list: List[str], kks_list: List[str], quality: List[str],
                     date: str, last_value_checked: bool, interval_or_date_checked: bool,
                     interval: int, dimension: str, date_deep_search: str) -> Union[str, dict]:
    """
    Функция запуска гринлета выполнения запроса по срезам тегов
    :param types_list: массив выбранных пользователем типов данных
    :param selection_tag: выбранный вид отбора тегов
    :param mask_list: массив маск шаблонов поиска regex
    :param kks_list: массив kks напрямую, указанные пользователем
    :param quality: массив кодов качества, указанные пользователем
    :param date: дата, указанная пользователем в запросе
    :param last_value_checked: флаг выдачи в таблицах срезов последних по времени значений
    :param interval_or_date_checked: флаг формата задачи даты
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :param date_deep_search: дата глубины поиска данных в архивах
    :return: json объект для заполнения таблицы срезов тегов
    """
    logger.info(f"get_signals_data({types_list}, {selection_tag}, {mask_list}, {kks_list}, {quality}, {date},"
                f"{last_value_checked}, {interval_or_date_checked}, {interval}, {dimension}, {date_deep_search})")

    def get_signals_data_spawn(types_list: List[str], selection_tag: str,
                               mask_list: List[str], kks_list: List[str], quality: List[str],
                               date: str, last_value_checked: bool, interval_or_date_checked: bool,
                               interval: int, dimension: str, date_deep_search: str) -> Union[str, None, dict]:
        """
        Функция запуска выполнения запроса по срезам тегов по OPC UA
        :param types_list: массив выбранных пользователем типов данных
        :param selection_tag: выбранный вид отбора тегов
        :param mask_list: массив маск шаблонов поиска regex
        :param kks_list: массив kks напрямую, указанные пользователем
        :param quality: массив кодов качества, указанные пользователем
        :param date: дата, указанная пользователем в запросе
        :param last_value_checked: флаг выдачи в таблицах срезов последних по времени значений
        :param interval_or_date_checked: флаг формата задачи даты
        :param interval: интервал
        :param dimension: размерность интервала [день, час, минута, секунда]
        :param date_deep_search: дата глубины поиска данных в архивах
        :return: json объект для заполнения таблицы срезов тегов
        """
        logger.info(f"get_signals_data_spawn({types_list}, {selection_tag}, {mask_list}, {kks_list}, {quality}, {date},"
                    f"{last_value_checked}, {interval_or_date_checked}, {interval}, {dimension}, {date_deep_search})")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        df_report = create_reports.create_signals_opc_ua_dataframe(socketio, sid, KKS_ALL,
                                                                   types_list, selection_tag,
                                                                   mask_list, kks_list, quality,
                                                                   date,
                                                                   last_value_checked, interval_or_date_checked,
                                                                   interval, dimension, date_deep_search)
        # Если ошибка или не нашлось ни одного значения, то придет строка
        if type(df_report) is str:
            return df_report
        elif df_report is None:
            return

        socketio.emit("setProgressBarSignals", {"count": 90}, to=sid)
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)
        slice = json.loads(df_report.to_json(orient='records'))
        render_slice(slice, url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarSignals", {"count": 95}, to=sid)
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Передача данных в веб-приложение...\n"},
                      to=sid)
        return slice

    def get_signals_from_ch_data_spawn(types_list: List[str], selection_tag: str,
                                       mask_list: List[str], kks_list: List[str], quality: List[str],
                                       date: str, last_value_checked: bool, interval_or_date_checked: bool,
                                       interval: int, dimension: str, date_deep_search: str) -> Union[str, dict]:
        """
        Функция запуска выполнения запроса по срезам тегов из Clickhouse
        :param types_list: массив выбранных пользователем типов данных
        :param selection_tag: выбранный вид отбора тегов
        :param mask_list: массив маск шаблонов поиска regex
        :param kks_list: массив kks напрямую, указанные пользователем
        :param quality: массив кодов качества, указанные пользователем
        :param date: дата, указанная пользователем в запросе
        :param last_value_checked: флаг выдачи в таблицах срезов последних по времени значений
        :param interval_or_date_checked: флаг формата задачи даты
        :param interval: интервал
        :param dimension: размерность интервала [день, час, минута, секунда]
        :param date_deep_search: дата глубины поиска данных в архивах
        :return: json объект для заполнения таблицы срезов тегов
        """
        logger.info(
            f"get_signals_from_ch_data_spawn({types_list}, {selection_tag}, {mask_list}, {kks_list}, {quality}, {date},"
            f"{last_value_checked}, {interval_or_date_checked}, {interval}, {dimension}, {date_deep_search})")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        try:
            df_report = create_reports.create_signals_ch_dataframe(socketio, sid, types_list, selection_tag,
                                                                   mask_list, kks_list, quality, date,
                                                                   last_value_checked, interval_or_date_checked,
                                                                   interval, dimension, date_deep_search)
        except clickhouse_exceptions.Error as error:
            logger.error(error)
            socketio.emit("setUpdateSignalsRequestStatus",
                          {"message": f"Никаких данных не нашлось\n"}, to=sid)
            return f"Никаких данных не нашлось"

        socketio.emit("setProgressBarSignals", {"count": 90}, to=sid)
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)
        slice = json.loads(df_report.to_json(orient='records'))
        render_slice(slice, url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarSignals", {"count": 95}, to=sid)
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Передача данных в веб-приложение...\n"}, to=sid)

        return slice

    sid = request.sid

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    global sid_proc
    global CLIENT_MODE
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"signals_greenlet is running")
        return f"Запрос уже выполняется для другого клиента. Попробуйте выполнить запрос позже"
    # Запуск запроса срезов через gevent в зависимости от режима
    if CLIENT_MODE == 'OPC':
        signals_greenlet = spawn(get_signals_data_spawn, types_list, selection_tag, mask_list, kks_list, quality, date,
                                 last_value_checked, interval_or_date_checked, interval, dimension, date_deep_search)

    if CLIENT_MODE == 'CH':
        signals_greenlet = spawn(get_signals_from_ch_data_spawn,
                                 types_list, selection_tag, mask_list, kks_list, quality, date,
                                 last_value_checked, interval_or_date_checked, interval, dimension, date_deep_search)

    gevent.joinall([signals_greenlet])
    sid_proc = None
    return signals_greenlet.value


@socketio.on("signals_data_cancel")
def signals_data_cancel() -> None:
    """
    Процедура отмены процесса выполнения запросов срезов и уничтожения гринлета gevent
    """
    logger.info(f"signals_data_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if sid_proc != request.sid:
        return

    global signals_greenlet
    if signals_greenlet:
        gevent.killall([signals_greenlet])
        signals_greenlet = None

        try:
            wkhtmltopdf_pid = check_output(["pidof", "-s", "wkhtmltopdf"])
            logger.warning(f"wkhtmltopdf pid = {wkhtmltopdf_pid}")
            if wkhtmltopdf_pid:
                os.kill(int(wkhtmltopdf_pid), signal.SIGTERM)
        except subprocess.CalledProcessError as subprocess_exception:
            logger.error(subprocess_exception)


@socketio.on("get_grid_data")
def get_grid_data(kks: List[str], date_begin: str, date_end: str,
                  interval: int, dimension: str) -> Union[str, None, Tuple[dict, dict, int]]:
    """
    Функция запуска гринлета выполнения запроса сетки
    :param kks: массив kks
    :param date_begin: начальная дата сетки
    :param date_end: конечная дата сетки
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :return: json объект для заполнения таблицы сеток и размер датафрейма
    """
    logger.info(f"get_grid_data({kks}, {date_begin}, {date_end}, {interval}, {dimension})")

    def get_grid_data_spawn(kks: List[str], date_begin: str, date_end: str,
                            interval: int, dimension: str) -> Union[str, None, Tuple[dict, dict, int]]:
        """
        Функция запуска выполнения запроса сетки
        :param kks: массив kks
        :param date_begin: начальная дата сетки
        :param date_end: конечная дата сетки
        :param interval: интервал
        :param dimension: размерность интервала [день, час, минута, секунда]
        :return: json объект для заполнения таблицы сеток
        """
        logger.info(f"get_grid_data_spawn({kks}, {date_begin}, {date_end}, {interval}, {dimension})")

        logger.info(sid)
        global sid_proc
        global REPORT_DF
        global REPORT_DF_STATUS
        sid_proc = sid

        try:
            df_report, df_report_slice, code = create_reports.create_grid_opc_ua_dataframe(socketio, sid, kks,
                                                                                           date_begin, date_end,
                                                                                           interval, dimension)
        except subprocess.CalledProcessError as subprocess_exception:
            # Если произошла ошибка во время вызова клиента, то ловим и выводим исключение
            logger.error(subprocess_exception)
            if "ValueError: sampling_period is greater than the duration between start and end" \
                    in str(subprocess_exception):
                logger.error("интервал больше, чем дата начала и конца")
                return f"интервал больше, чем дата начала и конца"
            return f"Произошла ошибка {str(subprocess_exception)}"
        except RuntimeError as run_time_exception:
            # Если произошла ошибка во время выполнении процесса, то ловим и выводим исключение
            logger.error(run_time_exception)
            socketio.emit("setUpdateGridRequestStatus", {"message": f"Ошибка: {run_time_exception}\n"}, to=sid)
            return

        REPORT_DF = df_report.copy(deep=True)
        REPORT_DF_STATUS = df_report_slice.copy(deep=True)

        code.to_csv(constants.CSV_CODE, index=False, encoding='utf-8')
        df_report.to_csv(constants.CSV_GRID, index=False, encoding='utf-8')
        df_report_slice.to_csv(constants.CSV_GRID_STATUS, index=False, encoding='utf-8')

        logger.info("Датафреймы сформированы")
        logger.info("Датафреймы доступны для выкачки")

        REPORT_DF = pd.read_csv(constants.CSV_GRID)
        REPORT_DF_STATUS = pd.read_csv(constants.CSV_GRID_STATUS)

        socketio.emit("setProgressBarGrid", {"count": 90}, to=sid)
        socketio.emit("setUpdateGridRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)
        code = json.loads(code.to_json(orient='records'))

        # Разделение таблиц по группам по 5 датчикам
        grid_separated_json_list, status_separated_json_list, \
        grid_separated_json_list_single, status_separated_json_list_single = \
            operations.prepare_for_grid_render(df_report, df_report_slice)

        parameters_of_request = {
            "date_begin": date_begin,
            "date_end": date_end,
            "interval": interval,
            "dimension": constants.INTERVAL_TO_LOCALE[dimension]
        }

        render_grid(code, grid_separated_json_list, status_separated_json_list,
                    grid_separated_json_list_single, status_separated_json_list_single, parameters_of_request,
                    url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateGridRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarGrid", {"count": 95}, to=sid)
        socketio.emit("setUpdateGridRequestStatus", {"message": f"Передача данных в веб-приложение...\n"}, to=sid)

        return json.loads(df_report[constants.FIRST:constants.LAST].to_json(orient='records')), \
               json.loads(df_report_slice[constants.FIRST:constants.LAST].to_json(orient='records')), \
               len(df_report)

    def get_grid_from_ch_data_spawn(kks: List[str], date_begin: str, date_end: str,
                                    interval: int, dimension: str) -> Union[str, Tuple[dict, dict, int]]:
        """
        Функция запуска выполнения запроса сетки
        :param kks: массив kks
        :param date_begin: начальная дата сетки
        :param date_end: конечная дата сетки
        :param interval: интервал
        :param dimension: размерность интервала [день, час, минута, секунда]
        :return: json объект для заполнения таблицы сеток
        """
        logger.info(f"get_grid_from_ch_data_spawn({kks}, {date_begin}, {date_end}, {interval}, {dimension})")

        logger.info(sid)
        global sid_proc
        global REPORT_DF
        global REPORT_DF_STATUS
        sid_proc = sid

        try:
            df_report, df_report_slice, code = create_reports.create_grid_ch_dataframe(socketio, sid, kks,
                                                                                       date_begin, date_end,
                                                                                       interval, dimension)
        except clickhouse_exceptions.Error as error:
            logger.error(error)
            socketio.emit("setUpdateGridRequestStatus", {"message": f"Ошибка: {error}\n"}, to=sid)
            return str(error)
        except KeyError as error:
            logger.error(error)
            socketio.emit("setUpdateGridRequestStatus",
                          {"message": f"Ошибка: Клиент Clickhouse ничего не нашел\n"}, to=sid)
            return "Ошибка: Клиент Clickhouse ничего не нашел"

        REPORT_DF = pd.read_csv(constants.CSV_GRID)
        REPORT_DF_STATUS = pd.read_csv(constants.CSV_GRID_STATUS)

        socketio.emit("setProgressBarGrid", {"count": 90}, to=sid)
        socketio.emit("setUpdateGridRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)
        code = json.loads(code.to_json(orient='records'))

        # Разделение таблиц по группам по 5 датчикам
        grid_separated_json_list, status_separated_json_list, \
        grid_separated_json_list_single, status_separated_json_list_single = \
            operations.prepare_for_grid_render(df_report, df_report_slice)

        parameters_of_request = {
            "date_begin": date_begin,
            "date_end": date_end,
            "interval": interval,
            "dimension": constants.INTERVAL_TO_LOCALE[dimension]
        }

        render_grid(code, grid_separated_json_list, status_separated_json_list,
                    grid_separated_json_list_single, status_separated_json_list_single, parameters_of_request,
                    url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateGridRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarGrid", {"count": 95}, to=sid)
        socketio.emit("setUpdateGridRequestStatus", {"message": f"Передача данных в веб-приложение...\n"}, to=sid)

        return json.loads(df_report[constants.FIRST:constants.LAST].to_json(orient='records')), \
               json.loads(df_report_slice[constants.FIRST:constants.LAST].to_json(orient='records')), \
               len(df_report)

    sid = request.sid

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    global sid_proc
    global CLIENT_MODE
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"grid_greenlet is running")
        return f"Запрос уже выполняется для другого клиента. Попробуйте выполнить запрос позже"
    # Запуск запроса срезов через gevent в зависимости от режима
    if CLIENT_MODE == 'OPC':
        grid_greenlet = spawn(get_grid_data_spawn, kks, date_begin, date_end, interval, dimension)

    if CLIENT_MODE == 'CH':
        grid_greenlet = spawn(get_grid_from_ch_data_spawn, kks, date_begin, date_end, interval, dimension)

    gevent.joinall([grid_greenlet])
    sid_proc = None
    return grid_greenlet.value


@socketio.on("get_grid_part_data")
def get_grid_part_data(first: int, last: int) -> Tuple[dict, dict]:
    """
    Функция выгрузки части данных таблицы сетки
    :param first: индекс начальной строки выгрузки скроллера
    :param last: индекс конечной строки выгрузки скроллера
    :return: json объекты для заполнения таблицы сетки
    """
    logger.info(f"get_grid_part_data({first}, {last})")
    global REPORT_DF
    global REPORT_DF_STATUS

    return json.loads(REPORT_DF.iloc[first:last].to_json(orient='records')), \
           json.loads(REPORT_DF_STATUS.iloc[first:last].to_json(orient='records'))


def apply_filters(filters: dict) -> None:
    """
    Процедура применения фильтров по столбцов
    :param filters: объект фильтра таблицы сетки
    :return:
    """
    logger.info(f"apply_filters({filters})")

    for key, value in filters.items():
        if value["value"] is None:
            continue

        if value["value"].isspace():
            continue

        FILTERS_OPERATIONS[value["matchMode"]](key, value["value"])


@socketio.on("get_grid_sorted_and_filtered_data")
def get_grid_sorted_and_filtered_data(params: dict) -> Tuple[dict, dict, int]:
    """
    Функция фильтрации по столбцам таблицы сетки
    :param params: объект сортировки и фильтра таблицы сетки
    :return: json объекты для заполнения осортированной таблицы сетки и размер получившегося датафрейма
    """
    logger.info(f"get_grid_sorted_and_filtered_data({params})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF = pd.read_csv(constants.CSV_GRID)
    REPORT_DF_STATUS = pd.read_csv(constants.CSV_GRID_STATUS)

    params = json.loads(params)

    apply_filters(params["filters"])

    if (params["sortField"] is not None) and (params["sortOrder"] is not None):
        REPORT_DF.sort_values(by=[params["sortField"]],
                              ascending=[False if params["sortOrder"] == -1 else True],
                              inplace=True)
        REPORT_DF_STATUS = REPORT_DF_STATUS.reindex(REPORT_DF.index)

    return json.loads(REPORT_DF.iloc[constants.FIRST:constants.LAST].to_json(orient='records')), \
           json.loads(REPORT_DF_STATUS.iloc[constants.FIRST:constants.LAST].to_json(orient='records')), \
           len(REPORT_DF)


def starts_with(col: str, val: str) -> None:
    """
    Процедура фильтрации колонки датафрейма по началу значения
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"starts_with({col}, {val})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF[col] = REPORT_DF[col].astype(str)

    REPORT_DF = REPORT_DF.loc[REPORT_DF[col].str.startswith(val, na=False)]
    REPORT_DF_STATUS = REPORT_DF_STATUS.loc[REPORT_DF_STATUS['Метка времени'].isin(REPORT_DF['Метка времени'])]

    if col != 'Метка времени':
        REPORT_DF[col] = REPORT_DF[col].astype(float)


def contains(col: str, val: str) -> None:
    """
    Процедура фильтрации колонки датафрейма по содержимому значения
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"contains({col}, {val})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF[col] = REPORT_DF[col].astype(str)

    REPORT_DF = REPORT_DF.loc[REPORT_DF[col].str.contains(val, na=False, regex=True)]
    REPORT_DF_STATUS = REPORT_DF_STATUS.loc[REPORT_DF_STATUS['Метка времени'].isin(REPORT_DF['Метка времени'])]

    if col != 'Метка времени':
        REPORT_DF[col] = REPORT_DF[col].astype(float)


def not_contains(col: str, val: str) -> None:
    """
    Процедура фильтрации колонки датафрейма по отсутсвию содержания значения
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"not_contains({col}, {val})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF[col] = REPORT_DF[col].astype(str)

    REPORT_DF = REPORT_DF.loc[~REPORT_DF[col].str.contains(val, na=False, regex=True)]
    REPORT_DF_STATUS = REPORT_DF_STATUS.loc[REPORT_DF_STATUS['Метка времени'].isin(REPORT_DF['Метка времени'])]

    if col != 'Метка времени':
        REPORT_DF[col] = REPORT_DF[col].astype(float)


def ends_with(col: str, val: str) -> None:
    """
    Процедура фильтрации колонки датафрейма по окончанию значения
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"ends_with({col}, {val})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF[col] = REPORT_DF[col].astype(str)

    REPORT_DF = REPORT_DF.loc[REPORT_DF[col].str.endswith(val, na=False)]
    REPORT_DF_STATUS = REPORT_DF_STATUS.loc[REPORT_DF_STATUS['Метка времени'].isin(REPORT_DF['Метка времени'])]

    if col != 'Метка времени':
        REPORT_DF[col] = REPORT_DF[col].astype(float)


def equals(col: str, val: str) -> None:
    """
    Процедура фильтрации колонки датафрейма по равенству значения
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"equals({col}, {val})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF[col] = REPORT_DF[col].astype(str)

    REPORT_DF = REPORT_DF.loc[REPORT_DF[col] == val]
    REPORT_DF_STATUS = REPORT_DF_STATUS.loc[REPORT_DF_STATUS['Метка времени'].isin(REPORT_DF['Метка времени'])]

    if col != 'Метка времени':
        REPORT_DF[col] = REPORT_DF[col].astype(float)


def not_equals(col: str, val: str) -> None:
    """
    Процедура фильтрации колонки датафрейма по не равенству значения
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"not_equals({col}, {val})")
    global REPORT_DF
    global REPORT_DF_STATUS

    REPORT_DF[col] = REPORT_DF[col].astype(str)

    REPORT_DF = REPORT_DF.loc[REPORT_DF[col] != val]
    REPORT_DF_STATUS = REPORT_DF_STATUS.loc[REPORT_DF_STATUS['Метка времени'].isin(REPORT_DF['Метка времени'])]

    if col != 'Метка времени':
        REPORT_DF[col] = REPORT_DF[col].astype(float)


def no_filter(col: str, val: str) -> None:
    """
    Процедура сброса фильтра
    :param col: наименование колонки
    :param val: значение поля фильтрации
    :return:
    """
    logger.info(f"no_filter({col}, {val})")
    return


@socketio.on("grid_data_cancel")
def grid_data_cancel() -> None:
    """
    Процедура отмены процесса выполнения запросов сетки и уничтожения гринлета gevent
    :return:
    """
    logger.info(f"grid_data_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if sid_proc != request.sid:
        return

    global grid_greenlet
    if grid_greenlet:
        gevent.killall([grid_greenlet])
        grid_greenlet = None

        try:
            wkhtmltopdf_pid = check_output(["pidof", "-s", "wkhtmltopdf"])
            logger.warning(f"wkhtmltopdf pid = {wkhtmltopdf_pid}")
            if wkhtmltopdf_pid:
                os.kill(int(wkhtmltopdf_pid), signal.SIGTERM)
        except subprocess.CalledProcessError as subprocess_exception:
            logger.error(subprocess_exception)


@socketio.on("get_bounce_signals_data")
def get_bounce_signals_data(kks: List[str], date: str, interval: int,
                            dimension: str, top: int) -> Union[str, None, dict]:
    """
    Функция запуска гринлета выполнения запроса дребезга
    :param kks: массив kks
    :param date: дата отсчета дребезга
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :param top: количество показываемых датчиков
    :return: json объект для заполнения таблицы дребезга
    """
    logger.info(f"get_bounce_signals_data({kks}, {date}, {interval}, {dimension}, {top})")

    def get_bounce_signals_data_spawn(kks: List[str], date: str, interval: int,
                                      dimension: str, top: int) -> Union[str, None, dict]:
        """
        Функция запуска выполнения запроса дребезга
        :param kks: массив kks
        :param date: дата отсчета дребезга
        :param interval: интервал
        :param dimension: размерность интервала [день, час, минута, секунда]
        :param top: количество показываемых датчиков
        :return: json объект для заполнения таблицы дребезга
        """
        logger.info(f"get_bounce_signals_data_spawn({kks}, {date}, {interval}, {dimension}, {top})")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        try:
            df_counts = create_reports.create_bounce_opc_ua_dataframe(socketio, sid, kks, date, interval, dimension)
            # Если не нашлось ни одного значения из выбранных датчиков, то придет строка
            if type(df_counts) is str:
                return df_counts

        except subprocess.CalledProcessError as subprocess_exception:
            logger.error(subprocess_exception)
            return f"Произошла ошибка {str(subprocess_exception)}"
        except RuntimeError as run_time_exception:
            # Если произошла ошибка во время выполнении процесса, то ловим и выводим исключение
            logger.error(run_time_exception)
            socketio.emit("setUpdateBounceRequestStatus", {"message": f"Ошибка: {run_time_exception}\n"}, to=sid)
            return

        socketio.emit("setProgressBarBounceSignals", {"count": 90}, to=sid)
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)

        parameters_of_request = {
            "date": date,
            "interval": interval,
            "dimension": constants.INTERVAL_TO_LOCALE[dimension],
            "top": top
        }

        bounce = json.loads(df_counts[:int(top)].to_json(orient='records'))
        render_bounce(bounce, parameters_of_request, url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarBounceSignals", {"count": 95}, to=sid)
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"Передача данных в веб-приложение...\n"}, to=sid)

        return bounce

    def get_bounce_from_ch_signals_data_spawn(kks: List[str], date: str, interval: int,
                                              dimension: str, top: int) -> Union[str, dict]:
        """
        Функция запуска выполнения запроса дребезга
        :param kks: массив kks
        :param date: дата отсчета дребезга
        :param interval: интервал
        :param dimension: размерность интервала [день, час, минута, секунда]
        :param top: количество показываемых датчиков
        :return: json объект для заполнения таблицы дребезга
        """
        logger.info(f"get_bounce_from_ch_signals_data_spawn({kks}, {date}, {interval}, {dimension}, {top})")

        logger.info(sid)
        global sid_proc
        sid_proc = sid

        try:
            df_counts = create_reports.create_bounce_ch_dataframe(socketio, sid, kks, date, interval, dimension, top)
            # Если не нашлось ни одного значения из выбранных датчиков, то придет строка
            if type(df_counts) is str:
                return df_counts
        except clickhouse_exceptions.Error as error:
            logger.error(error)
            socketio.emit("setUpdateGridRequestStatus", {"message": f"Ошибка: {error}\n"}, to=sid)
            return f'{error}'

        socketio.emit("setProgressBarBounceSignals", {"count": 90}, to=sid)
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)

        parameters_of_request = {
            "date": date,
            "interval": interval,
            "dimension": constants.INTERVAL_TO_LOCALE[dimension],
            "top": top
        }

        bounce = json.loads(df_counts[:int(top)].to_json(orient='records'))
        render_bounce(bounce, parameters_of_request, url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarBounceSignals", {"count": 95}, to=sid)
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"Передача данных в веб-приложение...\n"}, to=sid)

        return bounce

    sid = request.sid

    global signals_greenlet
    global grid_greenlet
    global bounce_greenlet
    global update_greenlet
    global change_update_greenlet
    global sid_proc
    global CLIENT_MODE
    started_greenlet = [update_greenlet, change_update_greenlet, signals_greenlet, grid_greenlet, bounce_greenlet]
    if any(started_greenlet):
        logger.warning(f"bounce_greenlet is running")
        return f"Запрос уже выполняется для другого клиента. Попробуйте выполнить запрос позже"

    # Запуск запроса дребезга через gevent в зависимости от режима
    if CLIENT_MODE == 'OPC':
        bounce_greenlet = spawn(get_bounce_signals_data_spawn, kks, date, interval, dimension, top)

    if CLIENT_MODE == 'CH':
        bounce_greenlet = spawn(get_bounce_from_ch_signals_data_spawn, kks, date, interval, dimension, top)

    gevent.joinall([bounce_greenlet])
    sid_proc = None
    return bounce_greenlet.value


@socketio.on("bounce_data_cancel")
def bounce_data_cancel() -> None:
    """
    Процедура отмены процесса выполнения запросов дребезга сигналов и уничтожения гринлета gevent
    :return:
    """
    logger.info(f"bounce_data_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if sid_proc != request.sid:
        return

    global bounce_greenlet
    if bounce_greenlet:
        gevent.killall([bounce_greenlet])
        bounce_greenlet = None

        try:
            wkhtmltopdf_pid = check_output(["pidof", "-s", "wkhtmltopdf"])
            logger.warning(f"wkhtmltopdf pid = {wkhtmltopdf_pid}")
            if wkhtmltopdf_pid:
                os.kill(int(wkhtmltopdf_pid), signal.SIGTERM)
        except subprocess.CalledProcessError as subprocess_exception:
            logger.error(subprocess_exception)


def parse_args():
    parser = argparse.ArgumentParser(description="start flask + vue 3 web-application")
    parser.add_argument("-ip", "--host", type=str, help="specify IPv4 address of host", default='localhost')
    parser.add_argument("-p", "--port", type=int, help="specify port", default=8004)
    parser.add_argument("-s", "--structure", default=False, help="prepare structure of web-app",
                        required=False, action="store_true")
    parser.add_argument("-c", "--config", default=False, help="create data/config.json from template",
                        required=False, action="store_true")
    parser.add_argument("-v", "--version", action="version", help="print version", version=f'{VERSION}')
    return parser.parse_args()


if __name__ == '__main__':
    try:
        args_parsed = parse_args()
    except SystemExit:
        logger.info(f'{VERSION} flask socket io + vue 3 web-application version')
        exit(0)

    if args_parsed.config:
        logger.info("Создание шаблона для заполнения конфигурационного файла ./data/config.json")
        check_correct_application_structure()
        with open(constants.CONFIG, 'w') as write_default:
            default_config = constants.CONFIG_DEFAULT
            json.dump(default_config, write_default, indent=4)
        logger.info("Создан шаблон конфигурационного файла ./data/config.json")
        exit(0)

    if args_parsed.structure:
        logger.info("Создание структуры веб-приложения")
        check_correct_application_structure()
        logger.info("Структура создана")
        exit(0)

    check_correct_application_structure()
    # Проверяем наличие конфига
    try:
        f = open(constants.CONFIG)
        config = json.load(f)
        # Валидируем конфиг при запуске бэкенда
        valid_flag, msg = operations.validate_imported_config(config)
        if not valid_flag:
            logger.error(f"Ошибка валидации конфига при запуске: {msg}")
            exit(0)
    except FileNotFoundError:
        logger.error("Отсутствует конфигурационный файл ./data/config.json")
        with open(constants.CONFIG, 'w') as write_default:
            default_config = constants.CONFIG_DEFAULT
            json.dump(default_config, write_default, indent=4)
        logger.warning("Создан шаблон для заполнения конфигурационного файла ./data/config.json")
        exit(0)
    except json.JSONDecodeError as json_error:
        logger.error("Ошибка считывания json файла")
        logger.error(json_error)
        exit(0)

    with open(constants.CONFIG, "r") as config_file:
        config = json.load(config_file)
        CLIENT_MODE = config["mode"]

    # Записываем в файл server.conf клиента OPC UA ip адрес и порт из конфига
    with open(constants.CLIENT_SERVER_CONF, "w") as writefile:
        writefile.write(f"opc.tcp://{config['opc']['ip']}:{config['opc']['port']}")

    try:
        KKS_ALL = pd.read_csv(constants.DATA_KKS_ALL, header=None, sep=';')
        KKS_ALL_BACK = pd.read_csv(constants.DATA_KKS_ALL_BACK, header=None, sep=';')
        logger.info(f"dataframe {constants.DATA_KKS_ALL} has been loaded")
        logger.info(f"dataframe {constants.DATA_KKS_ALL_BACK} has been loaded")
    except FileNotFoundError as e:
        logger.info(e)
        KKS_ALL = pd.DataFrame()
        KKS_ALL_BACK = pd.DataFrame()

    # Перезаполняем в bundle версии файл api_urls.js для настройки проксирования
    with open(constants.WEB_API_URLS_JS, 'r') as read_file:
        api_file = read_file.read()
        replacement_string = re.search("\'(.*)\'", api_file).group()
        api_file = api_file.replace(replacement_string, f"'https://{args_parsed.host}:{args_parsed.port}/'")
    with open(constants.WEB_API_URLS_JS, 'w') as write_file:
        write_file.write(str(api_file))

    REPORT_DF = None
    REPORT_DF_STATUS = None

    FILTERS_OPERATIONS = {
        "startsWith": starts_with,
        "contains": contains,
        "notContains": not_contains,
        "endsWith": ends_with,
        "equals": equals,
        "notEquals": not_equals,
        "noFilter": no_filter
    }

    logger.info(f"starting...")
    socketio.run(app, host=args_parsed.host, port=args_parsed.port,
                 keyfile=constants.SSL_KEY, certfile=constants.SSL_CERT)
