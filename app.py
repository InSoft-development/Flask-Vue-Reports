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

from utils.control import AppControl, DataControl, Task

from utils.correct_start import check_correct_application_structure
import utils.constants_and_paths as constants
import utils.routine_operations as operations
import utils.client_operations as client_operations
import utils.create_dataframe_reports as create_reports

from jinja.pylib.get_template import render_slice, render_grid, render_bounce

from loguru import logger

from typing import Dict, List, Tuple, Union

VERSION = '1.0.4'

app = Flask(__name__, static_folder="./web", template_folder="./web", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route("/", defaults={"path": ""})
@app.route("/<string:path>")
@app.route("/<path:path>")
def catch_all(path):
    """
    Функция инициализации страницы index.html
    :param path: любой путь, начинающийся с /
    :return: ./web/index.html
    """
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
    app_control.set_clients(request.sid)


@socketio.on("disconnect")
def disconnect():
    """
    Процедура регистрирует разъединение клиента и закрытие сокета
    :return:
    """
    app_control.set_clients(request.sid, remove=True)


@socketio.on("get_file_checked")
def get_file_checked() -> Tuple[bool, str, bool]:
    """
    Функция возвращает результат проверки существования файла тегов kks_all.csv или верность настройки клиента Clickhouse
    :return: True/False результат проверки существования файла тегов kks_all.csv
    """
    logger.info(f"get_file_checked()")

    client_status = operations.file_checked_status()
    return os.path.isfile(constants.DATA_KKS_ALL), data_control.client_mode, client_status


@socketio.on("get_client_mode")
def get_client_mode() -> str:
    """
    Функция возвращает выбранный режим работы клиента
    :return: строка ('OPC'/'CH') наименования выбранного режима клиента
    """
    logger.info(f"get_client_mode()")

    data_control.client_mode = client_operations.client_mode()

    return data_control.client_mode


@socketio.on("change_client_mode")
def change_client_mode(client_mode: str) -> Union[None, str]:
    """
    Процедура записывает в файл выбранный режим работы клиента
    :param client_mode: строка ('OPC'/'CH') наименования выбранного режима клиента
    :return: None
    """
    logger.info(f"change_client_mode()")

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return f"Выполняется запрос для другого клиента. Изменение режима клиента временно невозможно"

    client_operations.change_client_mode_to_config(client_mode)


@socketio.on("get_server_config")
def get_server_config() -> Tuple[str, bool]:
    """
    Функция возвращает конфигурацию клиента OPC UA или Clickhouse
    :return: строка конфигурации клиента OPC UA, True/False результат проверки существования файла тегов kks_all.csv
    """
    logger.info(f"get_server_config()")

    sid = request.sid

    return client_operations.server_config(socketio, sid, data_control.client_mode)


@socketio.on("get_last_update_file_kks")
def get_last_update_file_kks() -> str:
    """
    Функция возвращает дату последнего обновления файла тегов kks_all.csv или таблицы clickhouse
    :return: строка даты последнего обновления файла тегов kks_all.csv или таблицы clickhouse
    """
    logger.info(f"get_last_update_file_kks()")

    sid = request.sid

    return operations.last_update_file_kks(socketio, sid, data_control.client_mode)


@socketio.on("get_ip_port_config")
def get_ip_port_config() -> Tuple[str, int, str, int, str, str]:
    """
    Функция возвращает ip-адрес и порт клиента OPC UA и CH
    :return: строка ip-адрес OPC UA, порт OPC UA, ip-адрес CH, порт CH, username CH, password CH
    """
    logger.info(f"get_ip_port_config()")

    return client_operations.get_ip_port_config()


@socketio.on("get_default_fields")
def get_default_fields() -> Union[Dict[str, Union[str, int, bool, List[str]]], str]:
    """
    Функция возвращает конфигурацию вводимых полей для запроса по умолчанию
    :return: json объект полей по умочанию
    """
    logger.info(f"get_default_fields()")

    return operations.default_fields_read(data_control.client_mode)


@socketio.on("change_opc_server_config")
def change_opc_server_config(ip: str, port: int) -> Tuple[bool, str]:
    """
    Функция заменяет строку конфигурации клиента OPC UA
    :param ip: ip-адресс
    :param port: порт
    """
    logger.info(f"change_opc_server_config({ip}, {port})")

    sid = request.sid

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return True, f"Выполняется запрос для другого клиента. " \
                     f"Сохранение конфигурации клиента OPC UA временно невозможно"

    return client_operations.change_opc_server(socketio, sid, ip, port)


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

    sid = request.sid

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return True, f"Выполняется запрос для другого клиента. " \
                     f"Сохранение конфигурации клиента Clickhouse временно невозможно"

    return client_operations.change_ch_server(socketio, sid, ip, port, username, password)


@socketio.on("change_default_fields")
def change_default_fields(default_fields: dict) -> str:
    """
    Процедура сохраняет конфигурацию вводимых полей для запроса по умолчанию в конфиг json
    :param default_fields: json объект полей по умолчанию
    :return:
    """
    logger.info(f"change_default_fields({default_fields})")

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return f"Выполняется запрос для другого клиента. Сохранение параметров временно невозможно"

    return operations.default_fields_write(data_control.client_mode, default_fields)


@socketio.on("upload_config")
def upload_config(file: dict) -> str:
    """
    Функция импортирует пользовательский конфиг
    :param file: json файл конфига
    :return: Строка сообщения об успехе импорта или ошибке
    """
    logger.info(file)

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return f"Выполняется запрос для другого клиента. Импорт конфига временно невозможен"

    return operations.upload_config_process(file)


@socketio.on("get_types_of_sensors")
def get_types_of_sensors() -> List[str]:
    """
    Функция возвращает все типы данных тегов kks, найденных в файле тегов kks_all.csv или в таблице CH
    :return: массив строк типов данных
    """
    logger.info(f"get_types_of_sensors()")

    return operations.types_of_sensors(data_control.client_mode, data_control.kks_all)


@socketio.on("get_kks_tag_exist")
def get_kks_tag_exist(kks_tag: str) -> bool:
    """
    Функция возвращает результат проверки наличия тега в файле тегов kks_all.csv или в Clickhouse
    :param kks_tag: проверяемый тег kks
    :return: True - тег в файле тегов kks_all.csv; False - тега не найден в файле тегов kks_all.csv или это шаблон маски
    """
    logger.info(f"get_kks_tag_exist({kks_tag})")

    return operations.get_kks_tag_exist(data_control.client_mode, data_control.kks_all, kks_tag)


@socketio.on("get_kks_by_masks")
def get_kks_by_masks(types_list: List[str], mask_list: List[str]) -> List[Union[str, None]]:
    """
    Функция возвращает массив kks датчиков из файла тегов kks_all.csv или из Clickhouse по маске шаблона при поиске kks
    :param types_list: массив выбранных пользователем типов данных
    :param mask_list: массив маск шаблонов поиска regex
    :return: массив строк kks датчиков (чтобы не перегружать форму 10000)
    """
    logger.info(f"get_kks_by_masks({types_list}, {mask_list})")

    return operations.kks_by_masks(data_control.client_mode, data_control.kks_all, types_list, mask_list)


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

    if data_control.client_mode == 'OPC':
        return operations.get_kks_opc_ua(data_control.kks_all, types_list, mask_list, kks_list, selection_tag)
    elif data_control.client_mode == 'CH':
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
        app_control.sid_proc = sid

        update_kks_status = client_operations.update_kks_opc_ua(socketio, sid, mode, root_directory)
        if update_kks_status != "success":
            return update_kks_status

        # Пытаемся загрузить kks_all.csv, если он существует в переменную
        try:
            data_control.kks_all, data_control.kks_all_back = operations.kks_all_define(mode, exception_directories)
        except FileNotFoundError as csv_exception:
            logger.error(csv_exception)
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Ошибка при попытке загрузить файл kks_all.csv\nОшибка: {csv_exception}\n",
                           "serviceFlag": True},
                          to=sid)
            return f'{csv_exception}'

        socketio.emit("setUpdateStatus", {"statusString": f"Обновление тегов закончено\n", "serviceFlag": True}, to=sid)
        return f"Обновление тегов закончено\n"

    def update_from_ch_kks_all_spawn() -> str:
        """
        Процедура запуска обновления файла тегов kks_all.csv
        """
        logger.info(f"update_from_ch_kks_all_spawn()")

        logger.info(sid)
        app_control.sid_proc = sid

        return client_operations.update_kks_ch(socketio, sid)

    sid = request.sid
    # Запуск гринлета обновления тегов
    # Если обновление уже идет, выводим в веб-приложении
    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        socketio.emit("setUpdateStatus",
                      {"statusString": f"На сервере выполняется задача {app_control.active_task}. "
                                       f"Обновление тегов временно невозможно\n", "serviceFlag": True},
                      to=sid)
        return

    # Запуск процесса обновления тегов через gevent в зависимости от режима
    if data_control.client_mode == 'OPC':
        if not operations.validate_exception_directories(socketio, sid, mode):
            return
        app_control.active_task = Task.update.value
        app_control.active_greenlet = spawn(update_kks_all_spawn, mode,
                                            root_directory, exception_directories, exception_expert)

    if data_control.client_mode == 'CH':
        app_control.active_task = Task.update.value
        app_control.active_greenlet = spawn(update_from_ch_kks_all_spawn)

    gevent.joinall([app_control.active_greenlet])

    app_control.sid_proc = None


@socketio.on("update_cancel")
def update_cancel() -> None:
    """
    Процедура отмены процесса обновления и уничтожения гринлета gevent
    """
    logger.info(f"update_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if app_control.sid_proc != request.sid:
        return

    if app_control.active_greenlet:
        proc_pid = client_operations.get_p_kks_all()
        if proc_pid is not None:
            os.killpg(os.getpgid(proc_pid.pid), signal.SIGINT)

        if app_control.active_task == Task.update.value:
            gevent.killall([app_control.active_greenlet])
            logger.warning(f"Гринлет обновления тегов убит")
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Обновление тегов прервано пользователем\n", "serviceFlag": True},
                          to=request.sid)

            app_control.active_task = None
            app_control.active_greenlet = None

        if app_control.active_task == Task.change_update.value:
            gevent.killall([app_control.active_greenlet])
            logger.warning(f"Гринлет применения списка исключений тегов убит")
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Применение списка исключений прервано пользователем\n",
                           "serviceFlag": True},
                          to=request.sid)
            app_control.active_task = None
            app_control.active_greenlet = None


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
        app_control.sid_proc = sid

        socketio.emit("setUpdateStatus",
                      {"statusString": f"Применение списка исключений к уже обновленному файлу тегов\n",
                       "serviceFlag": False}, to=sid)

        try:
            data_control.kks_all = operations.kks_all_change_update(data_control.kks_all_back, root_directory, exception_directories)
        except re.error as regular_expression_except:
            logger.error(f"Неверный синтаксис регулярного выражения {regular_expression_except}")
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Неверный синтаксис регулярного выражения {regular_expression_except}\n"
                                           f"Отмена операции\n",
                           "serviceFlag": True},
                          to=sid)
            data_control.kks_all = data_control.kks_all_back.copy(deep=True)
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

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        socketio.emit("setUpdateStatus",
                      {"statusString": f"Обновление тегов уже было начато на сервере\n", "serviceFlag": True},
                      to=sid)
        return

    # Запуск изменения обновленного файла тегов на основе списка исключений через gevent
    app_control.active_task = Task.change_update.value
    app_control.active_greenlet = spawn(change_update_kks_all_spawn, root_directory,
                                        exception_directories, exception_expert)
    gevent.joinall([app_control.active_greenlet])

    app_control.sid_proc = None


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
        app_control.sid_proc = sid

        df_report = create_reports.create_signals_opc_ua_dataframe(socketio, sid, data_control.kks_all,
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
        app_control.sid_proc = sid

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

        # Если ошибка или не нашлось ни одного значения, то придет строка
        if type(df_report) is str:
            return df_report

        socketio.emit("setProgressBarSignals", {"count": 90}, to=sid)
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Формирование отчета\n"}, to=sid)
        slice = json.loads(df_report.to_json(orient='records'))
        render_slice(slice, url=f"https://{args_parsed.host}:{args_parsed.port}/")
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Отчет сформирован\n"}, to=sid)

        socketio.emit("setProgressBarSignals", {"count": 95}, to=sid)
        socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Передача данных в веб-приложение...\n"}, to=sid)

        return slice

    sid = request.sid

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return f"Запрос уже выполняется для другого клиента. Попробуйте выполнить запрос позже"
    # Запуск запроса срезов через gevent в зависимости от режима
    app_control.active_task = Task.signals.value
    if data_control.client_mode == 'OPC':
        app_control.active_greenlet = spawn(get_signals_data_spawn, types_list, selection_tag,
                                            mask_list, kks_list, quality, date,
                                            last_value_checked, interval_or_date_checked,
                                            interval, dimension, date_deep_search)

    if data_control.client_mode == 'CH':
        app_control.active_greenlet = spawn(get_signals_from_ch_data_spawn,
                                            types_list, selection_tag, mask_list, kks_list, quality, date,
                                            last_value_checked, interval_or_date_checked,
                                            interval, dimension, date_deep_search)

    gevent.joinall([app_control.active_greenlet])
    app_control.sid_proc = None
    return app_control.active_greenlet.value


@socketio.on("signals_data_cancel")
def signals_data_cancel() -> None:
    """
    Процедура отмены процесса выполнения запросов срезов и уничтожения гринлета gevent
    """
    logger.info(f"signals_data_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if app_control.sid_proc != request.sid:
        return

    if app_control.active_greenlet:
        gevent.killall([app_control.active_greenlet])
        app_control.active_task = None
        app_control.active_greenlet = None

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

        app_control.sid_proc = sid

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

        data_control.report_df = df_report.copy(deep=True)
        data_control.report_status = df_report_slice.copy(deep=True)

        code.to_csv(constants.CSV_CODE, index=False, encoding='utf-8')
        df_report.to_csv(constants.CSV_GRID, index=False, encoding='utf-8')
        df_report_slice.to_csv(constants.CSV_GRID_STATUS, index=False, encoding='utf-8')

        logger.info("Датафреймы сформированы")
        logger.info("Датафреймы доступны для выкачки")

        data_control.report_df = pd.read_csv(constants.CSV_GRID)
        data_control.report_status = pd.read_csv(constants.CSV_GRID_STATUS)

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

        app_control.sid_proc = sid

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

        data_control.report_df = pd.read_csv(constants.CSV_GRID)
        data_control.report_status = pd.read_csv(constants.CSV_GRID_STATUS)

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

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return f"Запрос уже выполняется для другого клиента. Попробуйте выполнить запрос позже"
    # Запуск запроса срезов через gevent в зависимости от режима
    app_control.active_task = Task.grid.value
    if data_control.client_mode == 'OPC':
        app_control.active_greenlet = spawn(get_grid_data_spawn, kks, date_begin, date_end, interval, dimension)

    if data_control.client_mode == 'CH':
        app_control.active_greenlet = spawn(get_grid_from_ch_data_spawn, kks, date_begin, date_end, interval, dimension)

    gevent.joinall([app_control.active_greenlet])
    app_control.sid_proc = None
    return app_control.active_greenlet.value


@socketio.on("get_grid_part_data")
def get_grid_part_data(first: int, last: int) -> Tuple[dict, dict]:
    """
    Функция выгрузки части данных таблицы сетки
    :param first: индекс начальной строки выгрузки скроллера
    :param last: индекс конечной строки выгрузки скроллера
    :return: json объекты для заполнения таблицы сетки
    """
    logger.info(f"get_grid_part_data({first}, {last})")

    return data_control.get_part_data(first, last)


@socketio.on("get_grid_sorted_and_filtered_data")
def get_grid_sorted_and_filtered_data(params: str) -> Tuple[dict, dict, int]:
    """
    Функция фильтрации по столбцам таблицы сетки
    :param params: объект сортировки и фильтра таблицы сетки
    :return: json объекты для заполнения осортированной таблицы сетки и размер получившегося датафрейма
    """
    logger.info(f"get_grid_sorted_and_filtered_data({params})")

    data_control.report_df = pd.read_csv(constants.CSV_GRID)
    data_control.report_status = pd.read_csv(constants.CSV_GRID_STATUS)

    params = json.loads(params)

    return data_control.get_sorted_and_filtered_data(params, constants.FIRST, constants.LAST)


@socketio.on("grid_data_cancel")
def grid_data_cancel() -> None:
    """
    Процедура отмены процесса выполнения запросов сетки и уничтожения гринлета gevent
    :return:
    """
    logger.info(f"grid_data_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if app_control.sid_proc != request.sid:
        return

    if app_control.active_greenlet:
        gevent.killall([app_control.active_greenlet])
        app_control.active_task = None
        app_control.active_greenlet = None

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
        app_control.sid_proc = sid

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
        app_control.sid_proc = sid

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

    if app_control.active_greenlet:
        logger.warning(f"{app_control.active_greenlet} гринлет выполняется; задача {app_control.active_task}")
        return f"Запрос уже выполняется для другого клиента. Попробуйте выполнить запрос позже"

    # Запуск запроса дребезга через gevent в зависимости от режима
    app_control.active_task = Task.bounce.value
    if data_control.client_mode == 'OPC':
        app_control.active_greenlet = spawn(get_bounce_signals_data_spawn, kks, date, interval, dimension, top)

    if data_control.client_mode == 'CH':
        app_control.active_greenlet = spawn(get_bounce_from_ch_signals_data_spawn, kks, date, interval, dimension, top)

    gevent.joinall([app_control.active_greenlet])
    app_control.sid_proc = None
    return app_control.active_greenlet.value


@socketio.on("bounce_data_cancel")
def bounce_data_cancel() -> None:
    """
    Процедура отмены процесса выполнения запросов дребезга сигналов и уничтожения гринлета gevent
    :return:
    """
    logger.info(f"bounce_data_cancel()")

    # Проверка, что отмена запроса пришла от вызвавшего его клиента
    if app_control.sid_proc != request.sid:
        return

    if app_control.active_greenlet:
        gevent.killall([app_control.active_greenlet])
        app_control.active_task = None
        app_control.active_greenlet = None

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

    # Инициализируем объекты управления гринлеттами и данными веб-приложения
    app_control = AppControl()
    data_control = DataControl()

    with open(constants.CONFIG, "r") as config_file:
        config = json.load(config_file)
        data_control.client_mode = config["mode"]

    # Записываем в файл server.conf клиента OPC UA ip адрес и порт из конфига
    with open(constants.CLIENT_SERVER_CONF, "w") as writefile:
        writefile.write(f"opc.tcp://{config['opc']['ip']}:{config['opc']['port']}")

    try:
        data_control.kks_all = pd.read_csv(constants.DATA_KKS_ALL, header=None, sep=';')
        data_control.kks_all_back = pd.read_csv(constants.DATA_KKS_ALL_BACK, header=None, sep=';')
        logger.info(f"dataframe {constants.DATA_KKS_ALL} has been loaded")
        logger.info(f"dataframe {constants.DATA_KKS_ALL_BACK} has been loaded")
    except FileNotFoundError as e:
        logger.info(e)
        data_control.kks_all = pd.DataFrame()
        data_control.kks_all_back = pd.DataFrame()

    # Перезаполняем в bundle версии файл api_urls.js для настройки проксирования
    with open(constants.WEB_API_URLS_JS, 'r') as read_file:
        api_file = read_file.read()
        replacement_string = re.search("\'(.*)\'", api_file).group()
        api_file = api_file.replace(replacement_string, f"'https://{args_parsed.host}:{args_parsed.port}/'")
    with open(constants.WEB_API_URLS_JS, 'w') as write_file:
        write_file.write(str(api_file))

    data_control.report_df = None
    data_control.report_status = None

    logger.info(f"starting...")
    socketio.run(app, host=args_parsed.host, port=args_parsed.port,
                 keyfile=constants.SSL_KEY, certfile=constants.SSL_CERT)
