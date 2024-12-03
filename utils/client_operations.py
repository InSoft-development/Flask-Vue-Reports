"""
Модуль содержит функции конфигурирования, запуска и отработки клиента OPC UA/БД кликхаус
"""

import clickhouse_connect
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

from gevent import subprocess, spawn
from gevent.subprocess import check_output

import pandas as pd

import json

import os
import datetime
from dateutil.parser import parse
import ipaddress
import re
import shutil

import utils.constants_and_paths as constants
import utils.routine_operations as operations

from loguru import logger

from typing import Dict, List, Tuple, Union
from flask_socketio import SocketIO


p_kks_all = None


def client_mode() -> str:
    """
    Функция возвращает выбранный режим работы клиента
    :return: строка ('OPC'/'CH') наименования выбранного режима клиента
    """
    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)
        logger.info(config["mode"])

    return config["mode"]


def change_client_mode_to_config(mode: str) -> None:
    """
    Процедура записывает в файл выбранный режим работы клиента
    :param mode: строка ('OPC'/'CH') наименования выбранного режима клиента
    :return: None
    """
    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)

    config["mode"] = mode

    with open(constants.CONFIG, "w") as write_config:
        json.dump(config, write_config, indent=4)


def server_config(socketio: SocketIO, sid: int, mode: str) -> [str, bool]:
    """
    Функция возвращает конфигурацию клиента OPC UA или Clickhouse
    :param socketio: объект сокета socketio
    :param sid: идентификатор сокетного соединения, сделавшего запрос
    :param mode: выбранный клиент
    :return: строка конфигурации клиента OPC UA, True/False результат проверки существования файла тегов kks_all.csv
    """
    if mode == 'OPC':
        with open(constants.CLIENT_SERVER_CONF, "r") as readfile:
            opc_server_config = readfile.readline()
            logger.info(opc_server_config)

        return f'Текущая конфигурация клиента OPC UA: {opc_server_config}', os.path.isfile(constants.DATA_KKS_ALL)

    if mode == 'CH':
        ip, port, username, password = read_clickhouse_server_conf()
        host = f"{ip}:{port}"

        client = get_client(sid, socketio, ip, port, username, password)
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


def get_ip_port_config() -> Tuple[str, int, str, int, str, str]:
    """
    Функция возвращает ip-адрес и порт клиента OPC UA и CH
    :return: строка ip-адрес OPC UA, порт OPC UA, ip-адрес CH, порт CH, username CH, password CH
    """
    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)
        opc_config = config["opc"]
        logger.info(opc_config)

    ip, port = opc_config["ip"], opc_config["port"]

    ip_ch, port_ch, username, password = read_clickhouse_server_conf()
    return ip, port, ip_ch, port_ch, username, password


def change_opc_server(socketio: SocketIO, sid: int, ip: str, port: int) -> Tuple[bool, str]:
    """
    Функция заменяет строку конфигурации клиента OPC UA
    :param socketio: объект сокета socketio
    :param sid: идентификатор сокетного соединения, сделавшего запрос
    :param ip: ip-адресс
    :param port: порт
    """
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
                                                          f"{readfile.read()}\n", "serviceFlag": False}, to=sid)
    return True, ""


def change_ch_server(socketio: SocketIO, sid: int, ip: str, port: int, username: str, password: str) \
        -> Tuple[bool, str]:
    """
    Процедура заменяет строку конфигурации клиента БД CH
    :param socketio: объект сокета socketio
    :param sid: идентификатор сокетного соединения, сделавшего запрос
    :param ip: ip-адресс
    :param port: порт
    :param username: имя пользователя
    :param password: пароль
    """
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

    ip_ch, port_ch, active_user, password_ch = read_clickhouse_server_conf()
    host = f"{ip_ch}:{port_ch}"
    socketio.emit("setUpdateStatus", {"statusString": f"Конфигурация клиента Clickhouse обновлена на: "
                                                      f"{host}, пользователь: {active_user}\n",
                                      "serviceFlag": False}, to=sid)
    return True, ""


def read_clickhouse_server_conf() -> Tuple[str, int, str, str]:
    """
    Функция чтения конфигурации клиента Clickhouse
    :return: ip: IPv4 адрес клиента Clickhouse,
             port: порт клиента Clickhouse
             username: имя пользователя клиента Clickhouse
             password: пароль клиента Clickhouse
    """
    logger.info(f"read_clickhouse_server_conf()")

    with open(constants.CONFIG, "r") as read_config:
        config = json.load(read_config)
        server_config = config["clickhouse"]
        ip, port = server_config["ip"], server_config["port"]
        username, password = server_config["username"], server_config["password"]

    return ip, port, username, password


def get_client(sid: int, socketio: SocketIO, ip: str, port: int, username: str, password: str) -> \
        Union[str, clickhouse_connect.driver.HttpClient]:
    """
    Функция инициализации и проверки клиента Clickhouse
    :param sid: идентификатор сокета
    :param socketio: объект сокета
    :param ip: IPv4 адрес клиента Clickhouse
    :param port: порт клиента Clickhouse
    :param username: имя пользователя клиента Clickhouse
    :param password: пароль клиента Clickhouse
    :return: объект клиента Clickhouse или строка ошибки
    """
    logger.info(f"get_client({sid}, {socketio}, {ip}, {port}, {username})")
    try:
        client = create_client(ip, port, username, password)
        return client
    except clickhouse_exceptions.DatabaseError as error:
        logger.error(error)
        socketio.emit("setUpdateStatus",
                      {"statusString": f"{error}\n", "serviceFlag": False},
                      to=sid)
        if "AUTHENTICATION_FAILED" in str(error):
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Неверное имя пользователя или пароль\n", "serviceFlag": True},
                          to=sid)
        else:
            socketio.emit("setUpdateStatus",
                          {"statusString": f"Неверно указан IP адрес Clickhouse или порт\n", "serviceFlag": True},
                          to=sid)
        return f"Ошибка конфигурации клиента Clickhouse"


def create_client(ip: str, port: int, username: str, password: str) -> clickhouse_connect.driver.HttpClient:
    """
    Функция инициализации клиента Clickhouse
    :param ip: IPv4 адрес клиента Clickhouse
    :param port: порт клиента Clickhouse
    :param username: имя пользователя клиента Clickhouse
    :param password: пароль клиента Clickhouse
    :return: клиент CH
    """
    return clickhouse_connect.get_client(host=ip, port=port, username=username, password=password)


def get_p_kks_all():
    """
    Функция возвращает объект subprocess p_kks_all
    :return: объект subprocess p_kks_all
    """
    return p_kks_all


def update_kks_opc_ua(socketio: SocketIO, sid: int, mode: str, root_directory: str) -> str:
    """
    Функция обновления тегов kks
    :param socketio: объект сокета
    :param sid: идентификатор сокета
    :param mode: выбранный режим фильтрации обновления тегов
    :param root_directory: корневая папка
    :return: строка статуса выполнения процесса обноваления тегов kks
    """
    global p_kks_all

    if mode == "historian":
        # root_directory = "all"
        root_directory = "begin"

    socketio.sleep(5)
    command_kks_all_string = ["./client", "-k", root_directory, "-c", "all", "-f", 'kks.csv']
    command_tail_kks_all_string = f"wc -l {constants.CLIENT_KKS} && tail -2 {constants.CLIENT_KKS} | head -1"
    logger.info(f'get from OPC_UA all kks and types')
    logger.info(command_kks_all_string)

    args = command_kks_all_string  # команда запуска процесса обновления
    args_tail = command_tail_kks_all_string  # команда получения последнего тега в файле kks_all.csv

    try:
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
            socketio.emit("setUpdateStatus", {"statusString": f"Ошибка: {lines_decode}\n", "serviceFlag": True}, to=sid)
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
            socketio.emit("setUpdateStatus", {"statusString": f"Ошибка: {lines_decode}\n", "serviceFlag": True}, to=sid)
            return lines_decode

        socketio.emit("setUpdateStatus", {"statusString": f"Последняя запись\n", "serviceFlag": True}, to=sid)
        p_tail = subprocess.Popen(args_tail, stdout=subprocess.PIPE, shell=True)
        out_tail, err_tail = p_tail.communicate()
        records = out_tail.decode('utf-8').split('\n')
        count = records[0].split()[0]
        record = records[1].split(';')[0]
        socketio.emit("setUpdateStatus", {"statusString": f"{count}. {record} Успех\n", "serviceFlag": True}, to=sid)
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

    return "success"


def update_kks_ch(socketio: SocketIO, sid: int) -> str:
    """
    Функция проверки доступности БД CH
    :param socketio: объект сокета
    :param sid: идентификатор сокета
    :return: строка статуса проверки доступности БД CH
    """
    ip, port, username, password = read_clickhouse_server_conf()

    socketio.emit("setUpdateStatus", {"statusString": f"соединение с Clickhouse...\n", "serviceFlag": True}, to=sid)
    client = get_client(sid, socketio, ip, port, username, password)
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


