"""
Модуль содержит функции построения отчетов
"""

import sqlite3
import clickhouse_connect
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

from gevent import subprocess, spawn
from gevent.subprocess import check_output

import pandas as pd

import json
import itertools
import re
import shutil
import time

import os
import datetime
from dateutil.parser import parse

import utils.constants_and_paths as constants
import utils.client_operations as client_operations
import utils.routine_operations as operations

from loguru import logger

from typing import Dict, List, Tuple, Union
from flask_socketio import SocketIO


def create_signals_opc_ua_dataframe(socketio: SocketIO, sid: int, kks_all: pd.DataFrame,
                                    types_list: List[str], selection_tag: str,
                                    mask_list: List[str], kks_list: List[str], quality: List[str],
                                    date: str, last_value_checked: bool, interval_or_date_checked: bool,
                                    interval: int, dimension: str, date_deep_search: str) -> \
        Union[str, None, pd.DataFrame]:
    error_flag = False  # флаг ошибки поиска в архивах

    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Формирование списка kks сигналов\n"}, to=sid)
    kks_requested_list = operations.get_kks_opc_ua(kks_all, types_list, mask_list, kks_list, selection_tag)
    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Список kks сигналов успешно сформирован\n"}, to=sid)

    # Подготовка к выполнению запроса
    # Формирование списка выбранных кодов качества
    correct_quality_list = list(map(lambda x: constants.QUALITY_CODE_DICT[x], quality))
    logger.warning(correct_quality_list)

    # Формирование декартового произведения
    decart_list = [kks_requested_list, correct_quality_list]
    decart_product = []

    for element in itertools.product(*decart_list):
        decart_product.append(element)

    # Сбрасываем обобщенную таблицу
    con_common_data = sqlite3.connect(constants.CLIENT_COMMON_DATA)
    cursor = con_common_data.cursor()
    cursor.execute(f'DROP TABLE IF EXISTS {constants.CLIENT_COMMON_DATA_TABLE}')
    con_common_data.commit()
    con_common_data.close()

    for i, element in enumerate(decart_product):
        # Сохранение датчика с KKS
        csv_tag_kks = pd.DataFrame(data=[element[0]])
        csv_tag_kks.to_csv(constants.CLIENT_KKS, index=False, header=None)

        # Формирование команды для запуска бинарника historian
        command_datetime_begin_time = (parse(date) - datetime.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        command_datetime_end_time = parse(date).strftime("%Y-%m-%dT%H:%M:%SZ")
        command_string = f"./client -b {command_datetime_begin_time} -e " \
                         f"{command_datetime_end_time} -p 100 -t 10000 -r -xw"

        logger.info(f'Получение по OPC UA: {element[0]}->{element[1]}')
        logger.info(command_string)

        socketio.emit("setUpdateSignalsRequestStatus",
                      {"message": f"Получение по OPC UA: {element[0]}->{element[1]}\n"}, to=sid)

        args = ["./client", "-b", f"{command_datetime_begin_time}", "-e", f"{command_datetime_end_time}",
                "-p", "100", "-t", "10000", "-r", "-xw"]

        try:
            subprocess.run(args, capture_output=True, cwd=f"{os.getcwd()}{os.sep}client{os.sep}", check=True)
        except subprocess.CalledProcessError as subprocess_exception:
            # Если произошла ошибка во время вызова клиента, то ловим и выводим исключение
            logger.error(subprocess_exception)
            return f"Произошла ошибка {str(subprocess_exception)}"
        except RuntimeError as run_time_exception:
            # Если произошла ошибка во время выполнении процесса, то ловим и выводим исключение
            logger.error(run_time_exception)
            socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Ошибка: {run_time_exception}\n"}, to=sid)
            return None

        # Достаем фрейм из sqlite
        con_current_data = sqlite3.connect(constants.CLIENT_DATA)

        query_string = f"SELECT {constants.CLIENT_DYNAMIC_TABLE}.*, {constants.CLIENT_STATIC_TABLE}.name AS name " \
                       f"FROM {constants.CLIENT_DYNAMIC_TABLE} " \
                       f"JOIN {constants.CLIENT_STATIC_TABLE} ON " \
                       f"{constants.CLIENT_DYNAMIC_TABLE}.id = {constants.CLIENT_STATIC_TABLE}.id " \
                       f"WHERE name='{element[0]}' AND status='{element[-1]}' " \
                       f"AND t <= '{parse(date).strftime('%Y-%m-%d %H:%M:%S')}' " \
                       f"ORDER BY t DESC LIMIT 1"
        logger.info(query_string)

        df_sqlite = pd.read_sql_query(
            query_string,
            con_current_data, parse_dates=['t'])
        con_current_data.close()
        logger.info(df_sqlite)
        # Если не нашли, то расширяем поиск:
        if df_sqlite.empty:
            logger.info(f"{constants.CLIENT_DATA} пуст")
            socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Расширение поиска в архивах...\n"},
                          to=sid)

            # Получаем предельное время в часах для поиска в глубину в архивах
            if interval_or_date_checked:
                deep_search_in_hour = (parse(date) - parse(date_deep_search)).total_seconds() / 3600
            else:
                delta_interval = interval * constants.DELTA_INTERVAL_IN_SECONDS[dimension]
                calculated_date_deep_search = \
                    (parse(date) - datetime.timedelta(seconds=delta_interval)).strftime("%Y-%m-%dT%H:%M:%SZ")
                deep_search_in_hour = (parse(date) - parse(calculated_date_deep_search)).total_seconds() / 3600

            delta = 2  # Строим запрос на 2 секунды раньше
            delta_prev = 0  # Формирование окна просмотра архива посредстовом сохранения предыдущего datetime
            while df_sqlite.empty:
                logger.info(df_sqlite)
                try:
                    # Формирование повторной команды с расширенной выборкой
                    command_datetime_begin_time = (parse(date) - datetime.timedelta(hours=delta)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ")
                    command_datetime_end_time = (parse(date) - datetime.timedelta(hours=delta_prev)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ")

                    command_string = f"./client -b {command_datetime_begin_time} -e " \
                                     f"{command_datetime_end_time} -p 100 -t 10000 -xw"
                    logger.info(f'Получение по OPC UA: {element[0]}->{element[1]}')
                    logger.info(command_string)

                    args = ["./client", "-b", f"{command_datetime_begin_time}", "-e",
                            f"{command_datetime_end_time}",
                            "-p", "100", "-t", "10000", "-xw"]

                    try:
                        subprocess.run(args, capture_output=True,
                                       cwd=f"{os.getcwd()}{os.sep}client{os.sep}", check=True)
                    except subprocess.CalledProcessError as subprocess_exception:
                        # Если произошла ошибка во время вызова клиента, то ловим и выводим исключение
                        logger.error(subprocess_exception)
                        return f"Произошла ошибка {str(subprocess_exception)}"
                    except RuntimeError as run_time_exception:
                        # Если произошла ошибка во время выполнении процесса, то ловим и выводим исключение
                        logger.error(run_time_exception)
                        socketio.emit("setUpdateSignalsRequestStatus",
                                      {"message": f"Ошибка: {run_time_exception}\n"},
                                      to=sid)
                        return None

                    con_current_data = sqlite3.connect(constants.CLIENT_DATA)
                    df_sqlite = pd.read_sql_query(
                        query_string,
                        con_current_data, parse_dates=['t'])
                    con_current_data.close()
                    delta_prev = delta
                    delta += constants.STEP_OF_BACK_SEARCH
                    # Если больше 1 года
                    if delta > deep_search_in_hour:
                        logger.info(f"За заданный период поиска в часах ({deep_search_in_hour}) "
                                    f"в архиве ничего не нашлось: {element[0]}->{element[1]}")
                        socketio.emit("setUpdateSignalsRequestStatus",
                                      {"message": f"За заданный период поиска в часах ({deep_search_in_hour}) "
                                                  f"в архиве ничего не нашлось: {element[0]}->{element[1]}\n"},
                                      to=sid)
                        error_flag = True
                        break
                except OverflowError:
                    error_flag = True
                    logger.info(f'OverflowError: {element[0]}->{element[1]}')
                    logger.info(f'begin_time = {command_datetime_begin_time}; '
                                f'end_time = {command_datetime_end_time}')
                    socketio.emit("setUpdateSignalsRequestStatus",
                                  {
                                      "message": f"OverflowError: {element[0]}->{element[1]}\n"
                                                 f"begin_time = {command_datetime_begin_time}; "
                                                 f"end_time = {command_datetime_end_time}\n"
                                  },
                                  to=sid)
                    break

        if not error_flag:
            con_common_data = sqlite3.connect(constants.CLIENT_COMMON_DATA)
            logger.info(con_common_data)
            df_sqlite.to_sql(f'{constants.CLIENT_COMMON_DATA_TABLE}', con_common_data,
                             if_exists='append', index=False)
            con_common_data.close()
            logger.info(f'Успешно завершено: {element[0]}->{element[1]}')
            socketio.emit("setUpdateSignalsRequestStatus",
                          {"message": f"Успешно завершено: {element[0]}->{element[1]}\n"}, to=sid)
        error_flag = False

        socketio.emit("setProgressBarSignals", {"count": int((i + 1) / len(decart_product) * 100 * 0.9)},
                      to=sid)  # 0.9 для масштабирования max в 90%

    try:
        con_common_data = sqlite3.connect(constants.CLIENT_COMMON_DATA)

        df_sqlite = pd.read_sql_query(
            f"SELECT * from {constants.CLIENT_COMMON_DATA_TABLE}",
            con_common_data, parse_dates=['t'])
    except Exception as e:
        # Если произошла ошибка с sqlite, то ловим и выводим исключение
        logger.error(f"{constants.CLIENT_COMMON_DATA_TABLE} is empty: {e}")
        socketio.emit("setUpdateSignalsRequestStatus",
                      {"message": f"Никаких данных не нашлось\n"}, to=sid)
        return f"Никаких данных не нашлось"
    finally:
        con_common_data.close()

    df_report = pd.DataFrame(
        columns=['Код сигнала (KKS)', 'Дата и время измерения', 'Значение', 'Качество',
                 'Код качества'],
        data={'Код сигнала (KKS)': df_sqlite['name'],
              'Дата и время измерения': df_sqlite['t'],
              'Значение': df_sqlite['val'],
              'Качество': df_sqlite['status'],
              'Код качества': list(map(lambda x: constants.QUALITY_DICT[x], df_sqlite['status'].to_list()))})
    df_report.fillna("NaN", inplace=True)

    # Отбираем последние по времени значения
    if last_value_checked:
        grouped = df_report.groupby(by='Код сигнала (KKS)')
        df_report = df_report.loc[grouped['Дата и время измерения'].idxmax()]
        logger.info(df_report)

    df_report.to_csv(constants.CSV_SIGNALS, index=False, encoding='utf-8')
    logger.info("Датафрейм сформирован")
    logger.info("Датафрейм доступен для выкачки")
    df_report['Дата и время измерения'] = df_report['Дата и время измерения'].dt.strftime('%Y-%m-%d %H:%M:%S')
    socketio.emit("setUpdateSignalsRequestStatus",
                  {"message": f"Запрос успешно завершен\n"}, to=sid)

    return df_report


def create_signals_ch_dataframe(socketio: SocketIO, sid: int,
                                types_list: List[str], selection_tag: str,
                                mask_list: List[str], kks_list: List[str], quality: List[str],
                                date: str, last_value_checked: bool, interval_or_date_checked: bool,
                                interval: int, dimension: str, date_deep_search: str) -> Union[str, pd.DataFrame]:
    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Формирование списка kks сигналов\n"}, to=sid)
    kks_requested_list = operations.get_kks_ch(types_list, mask_list, kks_list, selection_tag)
    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Список kks сигналов успешно сформирован\n"}, to=sid)
    socketio.emit("setProgressBarSignals", {"count": 10}, to=sid)

    # Формирование запроса sql к Clickhouse
    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Формирование запроса к БД Clickhouse\n"}, to=sid)
    query_string = operations.fill_signals_query(kks_requested_list, quality, date, last_value_checked,
                                                 interval_or_date_checked, interval, dimension, date_deep_search)
    logger.info(query_string)
    socketio.emit("setProgressBarSignals", {"count": 20}, to=sid)

    ip, port, username, password = client_operations.read_clickhouse_server_conf()
    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Запрос к БД Clickhouse\n"}, to=sid)
    socketio.emit("setProgressBarSignals", {"count": 50}, to=sid)
    client = client_operations.create_client(ip, port, username, password)
    logger.info("Clickhouse connected")

    df_signals = client.query_df(query_string)
    logger.info(df_signals)

    socketio.emit("setUpdateSignalsRequestStatus", {"message": f"Запрос к БД Clickhouse выполнен успешно\n"},
                  to=sid)

    client.close()
    logger.info("Clickhouse disconnected")

    if df_signals.empty:
        # Если датафрейм пуст
        logger.warning(df_signals)
        socketio.emit("setUpdateSignalsRequestStatus",
                      {"message": f"Никаких данных не нашлось\n"}, to=sid)
        return f"Никаких данных не нашлось"

    df_report = pd.DataFrame(
        columns=['Код сигнала (KKS)', 'Дата и время измерения', 'Значение', 'Качество',
                 'Код качества'],
        data={'Код сигнала (KKS)': df_signals['kks'],
              'Дата и время измерения': df_signals['timestamp'],
              'Значение': df_signals['val'],
              'Качество': df_signals['q_name'],
              'Код качества': df_signals['quality']})
    df_report.fillna("NaN", inplace=True)

    logger.info(df_report)

    df_report.to_csv(constants.CSV_SIGNALS, index=False, encoding='utf-8')
    logger.info("Датафрейм сформирован")
    logger.info("Датафрейм доступен для выкачки")
    df_report['Дата и время измерения'] = df_report['Дата и время измерения'].dt.strftime('%Y-%m-%d %H:%M:%S')
    socketio.emit("setUpdateSignalsRequestStatus",
                  {"message": f"Запрос успешно завершен\n"}, to=sid)

    return df_report


def create_grid_opc_ua_dataframe(socketio: SocketIO, sid: int,
                                 kks: List[str], date_begin: str, date_end: str, interval: int, dimension: str) -> \
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Сохранение датчика с KKS
    socketio.emit("setUpdateGridRequestStatus", {"message": f"Сохранение датчиков KKS\n"}, to=sid)
    csv_tag_kks = pd.DataFrame(data=kks)
    csv_tag_kks.to_csv(constants.CLIENT_KKS, index=False, header=None)

    # Формирование команд для запуска бинарника historian и скрипта slices.py
    command_datetime_begin_time = parse(date_begin).strftime("%Y-%m-%d %H:%M:%S")
    command_datetime_end_time = parse(date_end).strftime("%Y-%m-%d %H:%M:%S")

    command_datetime_begin_time_binary = parse(date_begin).strftime("%Y-%m-%dT%H:%M:%SZ")
    command_datetime_end_time_binary = parse(date_end).strftime("%Y-%m-%dT%H:%M:%SZ")

    command_string_binary = f"./client -b {command_datetime_begin_time_binary} -e " \
                            f"{command_datetime_end_time_binary} -p 100 -t 10000 -rxw"

    delta_interval = interval * constants.DELTA_INTERVAL_IN_SECONDS[dimension]
    command_string = f'python ./slicer.py -d {delta_interval} ' \
                     f'-t \"{command_datetime_begin_time}\" \"{command_datetime_end_time}\"'

    logger.info("Получение по OPC UA")
    logger.info(command_string_binary)

    socketio.emit("setUpdateGridRequestStatus", {"message": f"Получение по OPC UA валидных тегов\n"}, to=sid)

    socketio.emit("setProgressBarGrid", {"count": 5}, to=sid)

    args = ["./client", "-b", f"{command_datetime_begin_time_binary}", "-e",
            f"{command_datetime_end_time_binary}", "-p", "100", "-t", "10000" "-rxw"]

    subprocess.run(args, capture_output=True, cwd=f"{os.getcwd()}{os.sep}client{os.sep}", check=True)
    socketio.emit("setProgressBarGrid", {"count": 10}, to=sid)

    logger.info("Получение срезов")
    logger.info(command_string)

    socketio.emit("setUpdateGridRequestStatus", {"message": f"Получение срезов\n"}, to=sid)

    args = ["python", "./slicer.py", "-d", f"{delta_interval}",
            "-t", f"{command_datetime_begin_time}", f"{command_datetime_end_time}"]

    socketio.emit("setProgressBarGrid", {"count": 40}, to=sid)
    subprocess.run(args, capture_output=True, cwd=f"{os.getcwd()}{os.sep}client{os.sep}", check=True)
    socketio.emit("setProgressBarGrid", {"count": 50}, to=sid)

    socketio.emit("setUpdateGridRequestStatus", {"message": f"Формирование таблиц отчета\n"}, to=sid)

    df_slice_csv = pd.read_csv(constants.CLIENT_SLICES)
    df_slice_status_csv = pd.read_csv(constants.CLIENT_SLICES_STATUS)

    df_report = pd.DataFrame(df_slice_csv['timestamp'])
    df_report.rename(columns={'timestamp': 'Метка времени'}, inplace=True)

    df_report_slice = pd.DataFrame(df_slice_status_csv['timestamp'])
    df_report_slice.rename(columns={'timestamp': 'Метка времени'}, inplace=True)

    for index, kks in enumerate(df_slice_csv.columns.tolist()[1:]):
        df_report[index] = df_slice_csv[kks]
        df_report_slice[index] = df_slice_status_csv[kks]

    df_report.fillna("NaN", inplace=True)
    df_report_slice.fillna("NaN", inplace=True)

    socketio.emit("setProgressBarGrid", {"count": 70}, to=sid)

    logger.info(df_report)
    logger.info(df_report_slice)

    socketio.emit("setUpdateGridRequestStatus", {"message": f"Сохранение таблиц отчета\n"}, to=sid)
    code = pd.DataFrame(data={
        '№': [i for i in range(len(df_slice_csv.columns.tolist()[1:]))],
        'Обозначение сигнала': [kks for kks in df_slice_csv.columns.tolist()[1:]]})

    return df_report, df_report_slice, code


def create_grid_ch_dataframe(socketio: SocketIO, sid: int,
                             kks: List[str], date_begin: str, date_end: str, interval: int, dimension: str) -> \
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Формирование запроса sql к Clickhouse
    socketio.emit("setUpdateGridRequestStatus", {"message": f"Формирование запроса sql к БД Clickhouse\n"}, to=sid)
    socketio.emit("setProgressBarGrid", {"count": 10}, to=sid)

    query_drop, query_create, query_value, query_status = \
        operations.fill_grid_queries_value(kks, date_begin, date_end, interval, dimension)

    socketio.emit("setProgressBarGrid", {"count": 20}, to=sid)

    ip, port, username, password = client_operations.read_clickhouse_server_conf()

    socketio.emit("setUpdateGridRequestStatus",
                  {"message": f"Запрос к БД Clickhouse (получение значений)\n"}, to=sid)
    socketio.emit("setProgressBarGrid", {"count": 40}, to=sid)
    client = client_operations.create_client(ip, port, username, password)
    logger.info("Clickhouse connected")
    client.command(query_drop)
    client.command(query_create)
    df_slice_csv = client.query_df(query_value)
    socketio.emit("setUpdateGridRequestStatus",
                  {"message": f"Запрос к БД Clickhouse (получение кодов качества)\n"},
                  to=sid)
    df_slice_status_csv = client.query_df(query_status)
    socketio.emit("setProgressBarGrid", {"count": 50}, to=sid)
    client.close()
    logger.info("Clickhouse disconnected")

    socketio.emit("setUpdateGridRequestStatus", {"message": f"Формирование таблиц отчета\n"}, to=sid)

    df_report = pd.DataFrame(df_slice_csv['grid'])
    df_report.rename(columns={'grid': 'Метка времени'}, inplace=True)

    df_report_slice = pd.DataFrame(df_slice_status_csv['grid'])
    df_report_slice.rename(columns={'grid': 'Метка времени'}, inplace=True)

    for index, kks in enumerate(df_slice_csv.columns.tolist()[1:]):
        df_report[index] = df_slice_csv[kks]
        df_report_slice[index] = df_slice_status_csv[kks]

    df_report.fillna(0, inplace=True)
    df_report.fillna("NaN", inplace=True)

    df_report_slice = df_report_slice.astype(str)
    df_report_slice.replace({"<NA>": "missed"}, inplace=True)

    for k in df_report_slice.columns.tolist()[1:]:
        df_report_slice[k] = df_report_slice[k].map(constants.QUALITY_DICT_REVERSE)

    socketio.emit("setProgressBarGrid", {"count": 70}, to=sid)

    logger.info(df_report)
    logger.info(df_report_slice)

    socketio.emit("setUpdateGridRequestStatus", {"message": f"Сохранение таблиц отчета\n"}, to=sid)
    code = pd.DataFrame(data={
        '№': [i for i in range(len(df_slice_csv.columns.tolist()[1:]))],
        'Обозначение сигнала': [kks for kks in df_slice_csv.columns.tolist()[1:]]})

    code.to_csv(constants.CSV_CODE, index=False, encoding='utf-8')
    df_report.to_csv(constants.CSV_GRID, index=False, encoding='utf-8')
    df_report_slice.to_csv(constants.CSV_GRID_STATUS, index=False, encoding='utf-8')

    logger.info("Датафреймы сформированы")
    logger.info("Датафреймы доступны для выкачки")

    return df_report, df_report_slice, code


def create_bounce_opc_ua_dataframe(socketio: SocketIO, sid: int, kks: List[str],
                                   date: str, interval: int, dimension: str) -> Union[str, pd.DataFrame]:
    # Сохранение датчика с KKS
    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Сохранение датчиков KKS\n"}, to=sid)
    csv_tag_kks = pd.DataFrame(data=kks)
    csv_tag_kks.to_csv(constants.CLIENT_KKS, index=False, header=None)

    # Формирование команд для запуска бинарника historian
    delta_interval = interval * constants.DELTA_INTERVAL_IN_SECONDS[dimension]
    command_datetime_begin_time = (parse(date) -
                                   datetime.timedelta(seconds=delta_interval)).strftime("%Y-%m-%dT%H:%M:%SZ")
    command_datetime_end_time = parse(date).strftime("%Y-%m-%dT%H:%M:%SZ")

    command_string = f"./client -b {command_datetime_begin_time} -e " \
                     f"{command_datetime_end_time} -p 100 -t 1 -xw"

    logger.info("get OPC_UA")
    logger.info(command_string)

    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Получение срезов\n"}, to=sid)
    socketio.emit("setProgressBarBounceSignals", {"count": 20}, to=sid)

    args = ["./client", "-b", f"{command_datetime_begin_time}",
            "-e", f"{command_datetime_end_time}", "-p", "100", "-t", "1", "-xw"]

    subprocess.run(args, capture_output=True, cwd=f"{os.getcwd()}{os.sep}client{os.sep}", check=True)
    socketio.emit("setProgressBarBounceSignals", {"count": 50}, to=sid)

    logger.info(f'client finished')

    # Достаем фрейм из sqlite
    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Формирование таблиц отчета\n"}, to=sid)
    con_current_data = sqlite3.connect(constants.CLIENT_DATA)
    query_string_data = f"SELECT * from {constants.CLIENT_DYNAMIC_TABLE}"
    query_string_kks = f"SELECT  * FROM {constants.CLIENT_STATIC_TABLE}"

    df_sqlite = pd.read_sql_query(
        query_string_data,
        con_current_data, parse_dates=['t'])

    df_sqlite_kks = pd.read_sql_query(
        query_string_kks,
        con_current_data)

    con_current_data.close()

    if df_sqlite.empty:
        msg = "Не нашлось ни одного значения из выбранных датчиков. Возможно интервал слишком мал."
        logger.info(msg)
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"{msg}\n"}, to=sid)
        return msg

    df_counts = pd.DataFrame()
    df_counts['Частота'] = df_sqlite['id'].value_counts()
    df_counts.index.name = 'Наименование датчика'
    df_counts['Наименование датчика'] = [df_sqlite_kks.loc[df_sqlite_kks['id'] == id]['name'].values[0]
                                         for id in df_counts.index.values.tolist()]

    socketio.emit("setProgressBarBounceSignals", {"count": 80}, to=sid)
    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Сохранение таблиц отчета\n"}, to=sid)
    df_counts.to_csv(constants.CSV_BOUNCE, index=False, encoding='utf-8')
    logger.info("Датафрейм сформирован")
    logger.info("Датафрейм доступен для выкачки")

    return df_counts


def create_bounce_ch_dataframe(socketio: SocketIO, sid: int, kks: List[str],
                               date: str, interval: int, dimension: str, top: int) -> Union[str, pd.DataFrame]:
    # Формирование запроса sql к Clickhouse
    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Формирование запроса sql к Clickhouse\n"}, to=sid)
    socketio.emit("setProgressBarBounceSignals", {"count": 10}, to=sid)

    query_string = operations.fill_bounce_query(kks, date, interval, dimension, top)

    socketio.emit("setProgressBarBounceSignals", {"count": 20}, to=sid)

    ip, port, username, password = client_operations.read_clickhouse_server_conf()
    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Запрос к БД Clickhouse (получение значений)\n"},
                  to=sid)
    socketio.emit("setProgressBarBounceSignals", {"count": 40}, to=sid)
    client = client_operations.create_client(ip, port, username, password)
    logger.info("Clickhouse connected")
    df_bounce = client.query_df(query_string)
    socketio.emit("setProgressBarBounceSignals", {"count": 50}, to=sid)
    client.close()

    logger.info("Clickhouse disconnected")
    logger.info(df_bounce)

    if df_bounce.empty:
        msg = "Не нашлось ни одного значения из выбранных датчиков. Возможно интервал слишком мал."
        logger.info(msg)
        socketio.emit("setUpdateBounceRequestStatus", {"message": f"{msg}\n"}, to=sid)
        return msg

    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Формирование таблиц отчета\n"}, to=sid)

    df_counts = pd.DataFrame()
    df_counts['Частота'] = df_bounce['count_change']
    df_counts.index.name = 'Наименование датчика'
    df_counts['Наименование датчика'] = df_bounce['kks']

    socketio.emit("setProgressBarBounceSignals", {"count": 80}, to=sid)
    socketio.emit("setUpdateBounceRequestStatus", {"message": f"Сохранение таблиц отчета\n"}, to=sid)
    df_counts.to_csv(constants.CSV_BOUNCE, index=False, encoding='utf-8')
    logger.info("Датафрейм сформирован")
    logger.info("Датафрейм доступен для выкачки")

    return df_counts
