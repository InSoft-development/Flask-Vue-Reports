"""
Модуль содержит функции рутинных операций:  чтение конфигов из файлов,
                                            запись конфигов в файлы,
                                            валидация конфигов,
                                            подготовка тез запросов к БД,
                                            подготовка данных
"""

import clickhouse_connect
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

import pandas as pd

import json
import jsonschema

import os
import datetime
from dateutil.parser import parse
import ipaddress
import re

import utils.constants_and_paths as constants
import utils.client_operations as client_operations

from loguru import logger

from typing import Dict, List, Tuple, Union
from flask_socketio import SocketIO


def get_kks_opc_ua(kks_all: pd.DataFrame,
                   types_list: List[str], mask_list: List[str], kks_list: List[str],
                   selection_tag: str = None) -> List[str]:
    """
    Функция возвращает массив kks датчиков из файла тегов kks_all.csv по маске шаблона.
    Используется при выполнеии запросов на бэкенде
    :param kks_all: pandas фрейм файла тегов kks_all.csv
    :param types_list: массив выбранных пользователем типов данных
    :param mask_list: массив маск шаблонов поиска regex
    :param kks_list: массив kks напрямую, указанные пользователем
    :param selection_tag: выбранный вид отбора тегов
    :return: массив строк kks датчиков для выполнения запроса
    """
    kks_requested_list = []
    kks_descr_list = []
    kks_mask_list = []

    if selection_tag is None:
        selection_tag = "sequential"

    # Отбор тегов kks по типу данных и маске
    kks = kks_all.copy(deep=True)
    kks = kks[kks[1].isin(types_list)]

    list_kks = kks[0].tolist()
    set_list_kks = list(set(kks[0].tolist()))

    # Проверка на дубликаты kks, образовывающиеся при поиске по маске и вручную указанным пользователем
    try:
        assert len(list_kks) == len(set_list_kks)
    except AssertionError:
        logger.warning("В найденных тегах есть дубликаты")

    # Отбор тегов по указанным маскам (полследовательный или с объединением найденных тегов)
    try:
        if mask_list:
            if selection_tag == "sequential":
                for mask in mask_list:
                    kks = kks[kks[0].str.contains(mask, regex=True)]
                kks_mask_list = kks[0].tolist()

            if selection_tag == "union":
                kks_mask_set = set()
                for mask in mask_list:
                    template_kks_set = set(kks[kks[0].str.contains(mask, regex=True)][0].tolist())
                    kks_mask_set = kks_mask_set.union(template_kks_set)
                kks_mask_list = list(kks_mask_set)

        # Отбор тегов,указанных вручную с их объединением
        if kks_list:
            kks_requested_list = [kks for kks in kks_list if kks not in kks_mask_list]

        kks_requested_list += kks_mask_list
        kks_descr_list = kks[kks[0].isin(kks_requested_list)][2].tolist()
        logger.info(len(kks_requested_list))
    except re.error as regular_expression_except:
        logger.info(mask)
        logger.error(f"Неверный синтаксис регулярного выражения {regular_expression_except} в {mask}")
        return ['', mask]
    finally:
        tags_df = pd.DataFrame(columns=['Наименование тега', 'Описание тега'],
                               data={'Наименование тега': kks_requested_list,
                                     'Описание тега': kks_descr_list})
        tags_df.to_csv(constants.CSV_TAGS)
    logger.info(f'Датафрейм {constants.WEB_DIR}tags.csv доступен для выкачки')

    return kks_requested_list


def get_kks_ch(types_list: List[str], mask_list: List[str], kks_list: List[str], selection_tag: str = None) -> List[str]:
    """
    Функция возвращает массив kks датчиков из файла тегов kks_all.csv по маске шаблона.
    Используется при выполнеии запросов на бэкенде
    :param types_list: массив выбранных пользователем типов данных
    :param mask_list: массив маск шаблонов поиска regex
    :param kks_list: массив kks напрямую, указанные пользователем
    :param selection_tag: выбранный вид отбора тегов
    :return: массив строк kks датчиков для выполнения запроса
    """
    kks_requested_list = []
    kks_descr_list = []
    kks_mask_list = []

    if selection_tag is None:
        selection_tag = "sequential"

    ip, port, username, password = client_operations.read_clickhouse_server_conf()
    try:
        client = client_operations.create_client(ip, port, username, password)
        logger.info("Clickhouse connected")

        # Отбор тегов по указанным маскам (полследовательный или с объединением найденных тегов)
        if selection_tag == "sequential":
            kks = client.query_df(f"WITH {mask_list} AS arr_reg, {types_list} AS arr_type "
                                  f"SELECT item_name FROM archive.v_static_data "
                                  f"WHERE data_type_name in arr_type AND "
                                  f"length(multiMatchAllIndices(item_name, arr_reg)) = length(arr_reg)")

            kks_mask_list = kks['item_name'].tolist()

        if selection_tag == "union":
            kks = client.query_df(f"WITH {mask_list} AS arr_reg , {types_list} AS arr_type "
                                  f"SELECT item_name FROM archive.v_static_data "
                                  f"WHERE data_type_name in arr_type AND "
                                  f"multiMatchAny(item_name, arr_reg)")

            kks_mask_list = kks['item_name'].tolist()

        # Отбор тегов,указанных вручную с их объединением
        if kks_list:
            kks_requested_list = [kks for kks in kks_list if kks not in kks_mask_list]

        kks_requested_list += kks_mask_list
        kks = client.query_df(f"WITH {kks_requested_list} AS arr_kks , {types_list} AS arr_type "
                              f"SELECT item_name, item_descr FROM archive.v_static_data "
                              f"WHERE data_type_name in arr_type AND item_name in arr_kks")
        kks_requested_list = kks['item_name'].tolist()
        kks_descr_list = kks['item_descr'].tolist()
        logger.info(len(kks_requested_list))
        client.close()
        logger.info("Clickhouse disconnected")
    except clickhouse_exceptions.DatabaseError as pattern_error:
        logger.error(pattern_error)
        mask_error = [mask for mask in mask_list if mask in str(pattern_error)]
        logger.info(mask_error)
        if not mask_error:
            logger.error(pattern_error)
            return ['', str(pattern_error)]
        logger.error(f"Неверный синтаксис регулярного выражения {pattern_error} в {mask_error[0]}")
        return ['', mask_error[0]]
    except clickhouse_exceptions.Error as error:
        logger.error(error)
    finally:
        tags_df = pd.DataFrame(columns=['Наименование тега', 'Описание тега'],
                               data={'Наименование тега': kks_requested_list,
                                     'Описание тега': kks_descr_list})
        tags_df.to_csv(constants.CSV_TAGS)

    logger.info(f'Датафрейм {constants.WEB_DIR}tags.csv доступен для выкачки')
    return kks_requested_list


def validate_ip_address(ip: str) -> bool:
    """
    Функция валидации IPv4 адреса
    :param ip: строка IP-адреса
    :return: True/False результат валидации строки в IPv4 адрес
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError as ip_validate_error:
        logger.error(ip_validate_error)
        return False


def validate_imported_config(config: dict) -> Tuple[bool, str]:
    """
    Функция валидации импортируемгого конфига
    :param config: json объект конфига
    :return: True/False: результат валидации конфига,
             строка с указанием ошибки валидации, если возвращается False
    """
    logger.info("validate_imported_config")
    logger.info(config)
    # Валидация схемы
    try:
        jsonschema.validate(instance=config, schema=constants.CONFIG_SHEMA)
    except jsonschema.exceptions.ValidationError as valid_error:
        logger.error(valid_error.message)
        return False, valid_error.message

    # Валидация значений
    # Валидация IP
    if not (validate_ip_address(config["clickhouse"]["ip"]) and validate_ip_address(config["opc"]["ip"])):
        return False, "ip адрес в импортируемом конфиге указан не корректно"

    # Проверка соединения с БД Clickhouse по ip и порту
    try:
        client = client_operations.create_client(config["clickhouse"]["ip"], config["clickhouse"]["port"],
                                                 config["clickhouse"]["username"], config["clickhouse"]["password"])
        logger.info("Clickhouse connected")
        client.close()
        logger.info("Clickhouse disconnected")
    except clickhouse_exceptions.Error as error:
        logger.error(error)
        if config["mode"] == "CH":
            return False, "Ошибка конфигурации клиента БД Clickhouse"
        if config["mode"] == "OPC":
            pass

    # Валидация регулярных выражений
    try:
        mode = "OPC"
        for opc_reg in config["fields"]["OPC"]["sensorsAndTemplateValue"]:
            re.compile(opc_reg)
        for opc_reg in config["fields"]["OPC"]["exceptionDirectories"]:
            re.compile(opc_reg)
        mode = "CH"
        for ch_reg in config["fields"]["CH"]["sensorsAndTemplateValue"]:
            re.compile(ch_reg)
    except re.error as reg_error:
        logger.error(reg_error)
        return False, f"Ошибка в синтаксисе регулярных выражений. Режим {mode}, регулярное выражение " \
                      f"{ opc_reg if mode=='OPC' else ch_reg }"

    # Валидация даты глубины поиска в архивах
    try:
        mode = "OPC"
        config["fields"]["OPC"]["dateDeepOfSearch"] = parse(config["fields"]["OPC"]["dateDeepOfSearch"], fuzzy=False)\
            .strftime("%Y-%m-%dT%H:%M:%S")
        mode = "CH"
        config["fields"]["CH"]["dateDeepOfSearch"] = parse(config["fields"]["CH"]["dateDeepOfSearch"], fuzzy=False)\
            .strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError as date_error:
        logger.error(date_error)
        config_clause = config['fields']['OPC']['dateDeepOfSearch'] if mode == 'OPC' \
            else config['fields']['CH']['dateDeepOfSearch']
        return False, f"Ошибка в дате глубины поиска в архивах. Режим {mode}, поле dateDeepOfSearch: " \
                      f"{ config_clause }"

    # Валидация типов данных
    opc_uncorrect = [t for t in config["fields"]["OPC"]["typesOfSensors"] if t not in constants.OPC_TYPES_OF_SENSORS]
    ch_uncorrect = [t for t in config["fields"]["CH"]["typesOfSensors"] if t not in constants.CH_TYPES_OF_SENSORS]

    if opc_uncorrect or ch_uncorrect:
        logger.warning(opc_uncorrect)
        logger.warning(ch_uncorrect)
        return True, f"Предупреждение. Обнаружены следующие типы данных, которые могут отсутствовать " \
                     f"в источниках данных:" \
                     f"\n{'OPC:' + str(opc_uncorrect) if opc_uncorrect else ''} " \
                     f"\n{'CH:' + str(ch_uncorrect) if ch_uncorrect else ''}"
    return True, ""


def fill_signals_query(kks_requested_list: List[str], quality: List[str], date: str,
                       last_value_checked: bool, interval_or_date_checked: bool,
                       interval: int, dimension: str, date_deep_search: str) -> str:
    """
    Функция заполнения запроса срезов сигнала к Clickhouse
    :param kks_requested_list: массив kks напрямую, указанные пользователем
    :param quality: массив кодов качества, указанные пользователем
    :param date: дата, указанная пользователем в запросе
    :param last_value_checked: флаг выдачи в таблицах срезов последних по времени значений
    :param interval_or_date_checked:  флаг формата задачи даты
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :param date_deep_search: дата глубины поиска данных в архивах
    :return: строка запроса срезов сигнала
    """
    # Подготовка к выполнению запроса
    # Формирование списка выбранных кодов качества для sql запроса
    correct_quality_list = list(map(lambda x: constants.QUALITY_SHORT_CODE_DICT[x], quality))

    # Формирование даты
    if interval_or_date_checked:
        argument_datetime_begin_time = parse(date_deep_search).strftime("%Y-%m-%d %H:%M:%S")
    else:
        delta_interval = interval * constants.DELTA_INTERVAL_IN_SECONDS[dimension]
        argument_datetime_begin_time = (parse(date) - datetime.timedelta(seconds=delta_interval)).strftime(
            "%Y-%m-%d %H:%M:%S")

    argument_datetime_end_time = (parse(date)).strftime("%Y-%m-%d %H:%M:%S")

    # Аргументы запроса sql
    arguments_string = f"WITH toDateTime('{argument_datetime_begin_time}', 'UTC') as i_beg, " \
                       f"toDateTime('{argument_datetime_end_time}', 'UTC') as i_end, " \
                       f"{correct_quality_list} AS arr_q, " \
                       f"{kks_requested_list} AS arr_ids, " \
                       f"tt_id AS (SELECT id, item_name FROM archive.static_data where item_name in arr_ids), " \
                       f"tt_q AS (SELECT id, name FROM archive.t_quality_dict where name in arr_q)"

    # Тело запроса sql
    body_of_query = f"SELECT mq1.id id, item_name kks, ts_m timestamp, v_m val, q_m quality, name AS q_name " \
                    f"FROM ( " \
                    f"SELECT id, MAX(timestamp) ts_m, argMax(quality, timestamp) q_m, argMax(val, timestamp) v_m " \
                    f"FROM ( " \
                    f"SELECT *, first_value(val) OVER w1 AS v_f " \
                    f"FROM archive.dynamic_data " \
                    f"WHERE id in ( SELECT id FROM tt_id) AND quality IN ( SELECT id FROM tt_q) AND " \
                    f"timestamp > i_beg AND timestamp <= i_end WINDOW w1 AS " \
                    f"(PARTITION BY id, quality ORDER BY timestamp ASC ROWS BETWEEN 1 PRECEDING AND CURRENT ROW)" \
                    f") dd " \
                    f"WHERE v_f != val " \
                    f"GROUP BY id, quality" \
                    f") mq1 " \
                    f"LEFT ANY JOIN archive.t_quality_dict_ljoin sq ON mq1.q_m = sq.id " \
                    f"LEFT ANY JOIN tt_id sid ON mq1.id = sid.id " \
                    f"ORDER BY id, timestamp"

    if last_value_checked:
        body_of_query += f" DESC LIMIT 1 BY id"

    return arguments_string + body_of_query


def fill_grid_drop_table() -> str:
    """
    Функция заполнения запроса сброса временной таблицы сетки к Clickhouse
    :return: строка запроса сброса временной таблицы сетки
    """
    return f"DROP TEMPORARY TABLE IF EXISTS temp_grid"


def fill_grid_temporary_table(kks: List[str], date_begin: str, date_end: str, interval: int, dimension: str) -> str:
    """
    Функция заполнения запроса временной таблицы сетки к Clickhouse
    :param kks: массив kks
    :param date_begin: начальная дата сетки
    :param date_end: конечная дата сетки
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :return: строка запроса заполнения временной таблицы сетки
    """
    delta_interval = interval * constants.DELTA_INTERVAL_IN_SECONDS[dimension]
    argument_datetime_begin_time = parse(date_begin).strftime("%Y-%m-%d %H:%M:%S")
    argument_datetime_end_time = parse(date_end).strftime("%Y-%m-%d %H:%M:%S")

    temporary_table_string = f"CREATE TEMPORARY TABLE temp_grid AS "
    # Аргументы запроса sql
    arguments_string = f"WITH toDateTime('{argument_datetime_begin_time}', 'UTC') as i_beg, " \
                       f"toDateTime('{argument_datetime_end_time}', 'UTC') as i_end, " \
                       f"{delta_interval} AS i_step_sec, " \
                       f"toIntervalSecond(i_step_sec) AS i_step, " \
                       f"{kks} AS arr_ids, " \
                       f"tt_id AS (SELECT id did, item_name FROM archive.static_data where item_name in arr_ids) "

    arguments_string = temporary_table_string + arguments_string

    # Тело запроса sql
    body_of_query_select = f"SELECT id, val_mt, qua_mt, grid, " \
                           f"(any(val_mt) OVER " \
                           f"(PARTITION BY id ORDER BY grid ASC ROWS BETWEEN " \
                           f"1 FOLLOWING AND 1 FOLLOWING) - val_mt) * i_step_sec " \
                           f"/ (any(grid) OVER " \
                           f"(PARTITION BY id ORDER BY grid ASC ROWS BETWEEN 1 FOLLOWING AND 1 FOLLOWING) - grid) " \
                           f"AS delta_v "

    body_of_query_from_select = f"SELECT id, toDateTime(toStartOfInterval(timestamp, i_step) + i_step) AS grid, " \
                                f"argMax(val, timestamp) AS val_mt, argMax(quality, timestamp) AS qua_mt " \
                                f"FROM archive.dynamic_data " \
                                f"WHERE id IN (SELECT did FROM tt_id) AND timestamp > i_beg AND timestamp <= i_end " \
                                f"GROUP BY id, grid "

    body_of_query_from_union = f"UNION ALL " \
                               f"(SELECT did as id, i_beg as grid, " \
                               f"if(b.id = 0, NULL , b.val) val, " \
                               f"if(b.id = 0, NULL , b.quality) quality " \
                               f"FROM tt_id AS a " \
                               f"LEFT OUTER JOIN " \
                               f"(	SELECT id AS id, argMax(val, timestamp) as val, " \
                               f"argMax(quality, timestamp) as quality " \
                               f"FROM archive.dynamic_data " \
                               f"WHERE id in (SELECT did FROM tt_id) AND timestamp <= i_beg " \
                               f"GROUP BY id) b ON a.did = b.id)"

    body_of_query_from = f"FROM (" \
                         f"{body_of_query_from_select} " \
                         f"{body_of_query_from_union}" \
                         f") ORDER BY toUInt32(id), grid WITH FILL FROM i_beg TO i_end STEP i_step " \
                         f"INTERPOLATE ( id, delta_v, val_mt AS val_mt + delta_v, qua_mt )"

    body_of_query = body_of_query_select + body_of_query_from
    return arguments_string + body_of_query


def fill_grid_queries_value(kks: List[str], date_begin: str, date_end: str,
                            interval: int, dimension: str) -> Tuple[str, str, str, str]:
    """
    Функция заполнения запроса значений сетки к Clickhouse
    :param kks: массив kks
    :param date_begin: начальная дата сетки
    :param date_end: конечная дата сетки
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :return: строка запроса значений сетки
    """
    # Подготовка к выполнению запроса
    grid_item_value = ""
    grid_item_status = ""
    for k in kks:
        grid_item_value += f", sumIf(val_mt, item_name = '{k}') as `{k}`"
        grid_item_status += f", sumIf(qua_mt, item_name = '{k}') as `{k}`"

    query_value = f"WITH {kks} AS arr_ids, " \
                  f"tt_id AS (SELECT id did, item_name FROM archive.static_data where item_name in arr_ids) " \
                  f"SELECT grid " \
                  f"{grid_item_value} " \
                  f"FROM temp_grid SEMI LEFT JOIN tt_id sid ON id = sid.did GROUP BY grid ORDER BY grid"

    query_status = f"WITH {kks} AS arr_ids, " \
                   f"tt_id AS (SELECT id did, item_name FROM archive.static_data where item_name in arr_ids) " \
                   f"SELECT grid " \
                   f"{grid_item_status} " \
                   f"FROM temp_grid SEMI LEFT JOIN tt_id sid ON id = sid.did GROUP BY grid ORDER BY grid"

    return fill_grid_drop_table(), fill_grid_temporary_table(kks, date_begin, date_end, interval, dimension), \
           query_value, query_status


def fill_bounce_query(kks: List[str], date: str, interval: int, dimension: str, top: int) -> str:
    """
    Функция заполнения запроса дребезга к Clickhouse
    :param kks: массив kks
    :param date: дата отсчета дребезга
    :param interval: интервал
    :param dimension: размерность интервала [день, час, минута, секунда]
    :param top: количество показываемых датчиков
    :return: строка запроса дребезга
    """
    delta_interval = interval * constants.DELTA_INTERVAL_IN_SECONDS[dimension]
    argument_datetime_begin_time = (parse(date) - datetime.timedelta(seconds=delta_interval)).strftime(
        "%Y-%m-%d %H:%M:%S")
    argument_datetime_end_time = parse(date).strftime("%Y-%m-%d %H:%M:%S")

    # Аргументы запроса sql
    arguments_string = f"WITH toDateTime('{argument_datetime_begin_time}', 'UTC') as i_beg, " \
                       f"toDateTime('{argument_datetime_end_time}', 'UTC') as i_end, " \
                       f"{kks} AS arr_ids, " \
                       f"{top} as i_n, " \
                       f"tt_id AS (SELECT id, item_name FROM archive.static_data where item_name in arr_ids) "

    # Тело запроса sql
    body_of_query = f"SELECT any(item_name) kks, count(1) count_change " \
                    f"FROM  ( " \
                    f"SELECT id, val, first_value(val) OVER " \
                    f"(PARTITION BY id ORDER BY timestamp ASC ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS v_f " \
                    f"FROM archive.dynamic_data " \
                    f"WHERE id in (SELECT id FROM tt_id) " \
                    f"AND timestamp > i_beg " \
                    f"AND timestamp <= i_end) dd  LEFT ANY JOIN tt_id sid " \
                    f"USING id " \
                    f"WHERE val != v_f " \
                    f"GROUP BY id " \
                    f"ORDER BY count_change DESC " \
                    f"LIMIT i_n"

    return arguments_string + body_of_query


def prepare_for_grid_render(df_report: pd.DataFrame, df_report_slice: pd.DataFrame) -> \
        Tuple[List[dict], List[dict], List[dict], List[dict]]:
    """
    Функция подготовки рендеринга в шаблоне
    :param df_report: pandas фрейм значений сетки
    :param df_report_slice: pandas фрейм статуса сетки
    :return: json объекты под рендеринг в шаблоне и отчете
    """
    # Разделение таблиц по группам по 5 датчикам
    separate_count = 1
    grid_separated_json_list = []
    status_separated_json_list = []

    grid_separated_json_list_single = []
    status_separated_json_list_single = []

    temp_df_slice = df_report[['Метка времени']].copy()
    temp_df_status = df_report_slice[['Метка времени']].copy()

    for kks in df_report.columns.tolist()[1:]:
        temp_df_slice[kks] = df_report[kks]
        temp_df_status[kks] = df_report_slice[kks]

        if (separate_count % constants.SEPARATED_COUNT == 0) \
                or (separate_count == len(df_report.columns.tolist()[1:])):
            temp_json_grid = json.loads(temp_df_slice.to_json(orient='records', date_format='iso'))
            temp_json_status = json.loads(temp_df_status.to_json(orient='records', date_format='iso'))

            grid_separated_json_list.append(temp_json_grid)
            status_separated_json_list.append(temp_json_status)

            for index in temp_df_slice.columns.tolist()[1:]:
                temp_json_grid_single = json.loads(temp_df_slice[['Метка времени', index]].copy()
                                                   .to_json(orient='records', date_format='iso'))
                temp_json_status_single = json.loads(temp_df_status[['Метка времени', index]].copy()
                                                     .to_json(orient='records', date_format='iso'))

                grid_separated_json_list_single.append(temp_json_grid_single)
                status_separated_json_list_single.append(temp_json_status_single)

            temp_df_slice = df_report[['Метка времени']].copy()
            temp_df_status = df_report_slice[['Метка времени']].copy()
        separate_count += 1

    return grid_separated_json_list, status_separated_json_list, grid_separated_json_list_single, \
           status_separated_json_list_single
