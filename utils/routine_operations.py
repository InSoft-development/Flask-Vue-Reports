"""
Модуль содержит функции рутинных операций (чтение конфигов из файлов, запись конфигов в файлы)
"""

import os
import clickhouse_connect
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

from loguru import logger

import utils.constants_and_paths as constants


def read_clickhouse_server_conf():
    logger.info(f"read_clickhouse_server_conf()")
    with open(constants.CLIENT_CLICKHOUSE_SERVER_CONF, "r") as clickhouse_config:
        server_config = clickhouse_config.readline().split(',')
        host = server_config[0].split(':')
        ip, port = host[0], host[1]
        username = server_config[1]
        password = server_config[2]
    return ip, port, username, password


def get_client(sid, socketio, ip, port, username, password):
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


def create_client(ip, port, username, password):
    return clickhouse_connect.get_client(host=ip, port=port, username=username, password=password)
