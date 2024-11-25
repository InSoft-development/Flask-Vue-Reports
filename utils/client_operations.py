"""
Модуль содержит функции запуска и отработки клиента OPC UA/БД кликхаус
"""

import clickhouse_connect
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

import pandas as pd

import json

import os
import datetime
from dateutil.parser import parse
import ipaddress
import re

import utils.constants_and_paths as constants

from loguru import logger

from typing import Dict, List, Tuple, Union
from flask_socketio import SocketIO


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
    :return:
    """
    return clickhouse_connect.get_client(host=ip, port=port, username=username, password=password)
