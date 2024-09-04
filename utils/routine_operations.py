"""
Модуль содержит функции рутинных операций (чтение конфигов из файлов, запись конфигов в файлы)
"""

import os
import clickhouse_connect
from clickhouse_connect.driver import exceptions as clickhouse_exceptions

from loguru import logger

import datetime
from dateutil.parser import parse

import json

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


def fill_signals_query(kks_requested_list, quality, date, last_value_checked, interval_or_date_checked,
                       interval, dimension, date_deep_search):
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


def fill_grid_drop_table():
    return f"DROP TEMPORARY TABLE IF EXISTS temp_grid"


def fill_grid_temporary_table(kks, date_begin, date_end, interval, dimension):
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


def fill_grid_queries_value(kks, date_begin, date_end, interval, dimension):
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


def fill_bounce_query(kks, date, interval, dimension, top):
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


def prepare_for_grid_render(df_report, df_report_slice):
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
            temp_json_grid = json.loads(temp_df_slice.to_json(orient='records'))
            temp_json_status = json.loads(temp_df_status.to_json(orient='records'))

            grid_separated_json_list.append(temp_json_grid)
            status_separated_json_list.append(temp_json_status)

            for index in temp_df_slice.columns.tolist()[1:]:
                temp_json_grid_single = json.loads(temp_df_slice[['Метка времени', index]].copy()
                                                   .to_json(orient='records'))
                temp_json_status_single = json.loads(temp_df_status[['Метка времени', index]].copy()
                                                     .to_json(orient='records'))

                grid_separated_json_list_single.append(temp_json_grid_single)
                status_separated_json_list_single.append(temp_json_status_single)

            temp_df_slice = df_report[['Метка времени']].copy()
            temp_df_status = df_report_slice[['Метка времени']].copy()
        separate_count += 1

    return grid_separated_json_list, status_separated_json_list, grid_separated_json_list_single, \
           status_separated_json_list_single