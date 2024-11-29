import json

from enum import Enum

from loguru import logger

from gevent import Greenlet
from pandas import DataFrame
from typing import List, Dict, Tuple, Union, Callable


class Task(Enum):
    update = 'update'
    change_update = 'change update'
    signals = 'signals report'
    grid = 'grid report'
    bounce = 'bounce report'


class AppControl:
    """
    Класс управления гринлетов и сокетных соединений

    Поля:
        __clients: словарь идентификаторов текущих сеансов сокетных соединений клиентов
        __sid_proc: идентификатор сокета (sid), вызывающего процесс
        __active_greenlet: активный гринлет
        __active_task: выполняемая задача активного гринлета (__active_greenlet)
    """
    __clients: Union[None, Dict[int, int]]
    __sid_proc: Union[None, int]
    __active_greenlet: Union[None, Greenlet]
    __active_task: Union[None, str]

    def __init__(self):
        """
        Конструктор класса AppControl
        """
        self.__clients = dict()
        self.__sid_proc = None
        self.__active_greenlet = None
        self.__active_task = None

    @property
    def clients(self):
        """
        Геттер поля __clients
        :return:
        """
        return self.__clients

    def set_clients(self, sid: int, remove: bool = False):
        """
        Сеттер поля __clients
        :param sid: идентификатор сокетного соединения клиента
        :param remove: флаг на удаление сокетного соединения клиента из словаря __clients
        :return:
        """
        if remove:
            del self.__clients[sid]
            logger.warning(f"disconnect: {sid}")
        else:
            self.__clients[sid] = sid
            logger.warning(f"connect: {sid}")

    @property
    def sid_proc(self):
        """
        Геттер поля __sid_proc
        :return:
        """
        return self.__sid_proc

    @sid_proc.setter
    def sid_proc(self, sid):
        """
        Сеттер поля __sid_proc
        :param sid: идентификатор сокетного соединения клиента
        :return:
        """
        self.__sid_proc = sid

    @property
    def active_greenlet(self):
        """
        Геттер поля __active_greenlet
        :return:
        """
        return self.__active_greenlet

    @active_greenlet.setter
    def active_greenlet(self, greenlet: Greenlet):
        """
        Сеттер поля __active_greenlet
        :param greenlet: объект гринлет
        :return:
        """
        self.__active_greenlet = greenlet

    @property
    def active_task(self):
        """
        Геттер поля __active_task
        :return:
        """
        return self.__active_task

    @active_task.setter
    def active_task(self, task_name: str):
        """
        Сеттер поля __active_task
        :param task_name: наименование задачи из перечисления Task
        :return:
        """
        self.__active_task = task_name


class DataControl:
    """
    Класс управления данными веб-приложения

    Поля:
        __client_mode: текущий режим клиента {'OPC', 'CH'}
        __kks_all: pandas фрейм файла тегов kks_all.csv
        __kks_all_back: pandas фрейм резервного файла тегов kks_all_back.csv
        __report_df: pandas фрейм данных отчета для выполнения фильтрации, сортировки и lazy загрузки данных
        __report_status: pandas фрейм статусов кодов качеств на значениях
        __filter_operations: cловарь действий и функций для фильтрации __report_df и __report_status
         для выполнения фильтрации, сортировки и lazy загрузки данных
    """
    client_mode: Union[None, str]
    kks_all: Union[None, DataFrame]
    kks_all_back: Union[None, DataFrame]
    report_df: Union[None, DataFrame]
    report_status: Union[None, DataFrame]
    filter_operations: Dict[str, Callable[[str, str], None]]

    def __init__(self):
        """
        Конструктор класса DataControl
        """
        self.__client_mode = None
        self.__kks_all = None
        self.__kks_all_back = None
        self.__report_df = None
        self.__report_status = None
        self.__filter_operations = {
            "startsWith": self.starts_with,
            "contains": self.contains,
            "notContains": self.not_contains,
            "endsWith": self.ends_with,
            "equals": self.equals,
            "notEquals": self.not_equals,
            "noFilter": self.no_filter
        }

    @property
    def client_mode(self):
        """
        Геттер поля __client_mode
        :return:
        """
        return self.__client_mode

    @client_mode.setter
    def client_mode(self, mode: str):
        """
        Сеттер поля __client_mode
        :param mode: режим клиента
        :return:
        """
        self.__client_mode = mode

    @property
    def kks_all(self):
        """
        Геттер поля __kks_all
        :return:
        """
        return self.__kks_all

    @kks_all.setter
    def kks_all(self, kks_frame: DataFrame):
        """
        Сеттер поля __kks_all
        :param kks_frame: новый pandas фрейм под kks_all.csv
        :return:
        """
        self.__kks_all = kks_frame

    @property
    def kks_all_back(self):
        """
        Геттер поля __kks_all_back
        :return:
        """
        return self.__kks_all_back

    @kks_all_back.setter
    def kks_all_back(self, kks_back_frame: DataFrame):
        """
        Сеттер поля __kks_all_back
        :param kks_back_frame: новый pandas фрейм под резервный kks_all_back.csv
        :return:
        """
        self.__kks_all_back = kks_back_frame

    @property
    def report_df(self):
        """
        Геттер поля __report_df
        :return:
        """
        return self.__report_df

    @report_df.setter
    def report_df(self, report: DataFrame):
        """
        Сеттер поля __report_df
        :param report: pandas фрейм данных отчета
        :return:
        """
        self.__report_df = report

    @property
    def report_status(self):
        """
        Геттер поля __report_status
        :return:
        """
        return self.__report_status

    @report_status.setter
    def report_status(self, status: DataFrame):
        """
        Сеттер поля __report_status
        :param status: pandas фрейм данных статусов кодов качеств на значениях
        :return:
        """
        self.__report_status = status

    def get_part_data(self, first: int, last: int) -> Tuple[dict, dict]:
        """
        Функция выгрузки части данных
        :param first: индекс начальной строки выгрузки скроллера
        :param last: индекс конечной строки выгрузки скроллера
        :return: json объекты для заполнения таблицы
        """
        return json.loads(self.__report_df.iloc[first:last].to_json(orient='records')), \
               json.loads(self.__report_status.iloc[first:last].to_json(orient='records'))

    def get_sorted_and_filtered_data(self, params: dict, first: int, last: int) -> Tuple[dict, dict, int]:
        """
        Функция фильтрации по столбцам таблицы сетки
        :param params: объект сортировки и фильтра таблицы сетки в виде json строки
        :param first: индекс начальной строки выгрузки скроллера
        :param last: индекс конечной строки выгрузки скроллера
        :return: json объекты для заполнения осортированной таблицы сетки и размер получившегося датафрейма
        """
        self.apply_filters(params["filters"])

        if (params["sortField"] is not None) and (params["sortOrder"] is not None):
            self.__report_df.sort_values(by=[params["sortField"]],
                                         ascending=[False if params["sortOrder"] == -1 else True],
                                         inplace=True)
            self.__report_status = self.__report_status.reindex(self.__report_df.index)

        return json.loads(self.__report_df.iloc[first:last].to_json(orient='records')), \
               json.loads(self.__report_status.iloc[first:last].to_json(orient='records')), \
               len(self.__report_df)

    def apply_filters(self, filters: dict) -> None:
        """
        Процедура применения фильтров по столбцов
        :param filters: объект фильтра таблицы сетки
        :return:
        """
        for key, value in filters.items():
            if value["value"] is None:
                continue

            if value["value"].isspace():
                continue

            self.__filter_operations[value["matchMode"]](col=key, val=value["value"])

    def starts_with(self, col: str, val: str) -> None:
        """
        Процедура фильтрации колонки датафрейма по началу значения
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"starts_with({col}, {val})")

        self.__report_df[col] = self.__report_df[col].astype(str)

        self.__report_df = self.__report_df.loc[self.__report_df[col].str.startswith(val, na=False)]
        self.__report_status = self.__report_status.loc[self.__report_status['Метка времени'].isin(
            self.__report_df['Метка времени'])]

        if col != 'Метка времени':
            self.__report_df[col] = self.__report_df[col].astype(float)

    def contains(self, col: str, val: str) -> None:
        """
        Процедура фильтрации колонки датафрейма по содержимому значения
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"contains({col}, {val})")

        self.__report_df[col] = self.__report_df[col].astype(str)

        self.__report_df = self.__report_df.loc[self.__report_df[col].str.contains(val, na=False, regex=True)]
        self.__report_status = self.__report_status.loc[self.__report_status['Метка времени'].isin(
            self.__report_df['Метка времени'])]

        if col != 'Метка времени':
            self.__report_df[col] = self.__report_df[col].astype(float)

    def not_contains(self, col: str, val: str) -> None:
        """
        Процедура фильтрации колонки датафрейма по отсутсвию содержания значения
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"not_contains({col}, {val})")

        self.__report_df[col] = self.__report_df[col].astype(str)

        self.__report_df = self.__report_df.loc[~self.__report_df[col].str.contains(val, na=False, regex=True)]
        self.__report_status = self.__report_status.loc[self.__report_status['Метка времени'].isin(
            self.__report_df['Метка времени'])]

        if col != 'Метка времени':
            self.__report_df[col] = self.__report_df[col].astype(float)

    def ends_with(self, col: str, val: str) -> None:
        """
        Процедура фильтрации колонки датафрейма по окончанию значения
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"ends_with({col}, {val})")

        self.__report_df[col] = self.__report_df[col].astype(str)

        self.__report_df = self.__report_df.loc[self.__report_df[col].str.endswith(val, na=False)]
        self.__report_status = self.__report_status.loc[self.__report_status['Метка времени'].isin(
            self.__report_df['Метка времени'])]

        if col != 'Метка времени':
            self.__report_df[col] = self.__report_df[col].astype(float)

    def equals(self, col: str, val: str) -> None:
        """
        Процедура фильтрации колонки датафрейма по равенству значения
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"equals({col}, {val})")

        self.__report_df[col] = self.__report_df[col].astype(str)

        self.__report_df = self.__report_df.loc[self.__report_df[col] == val]
        self.__report_status = self.__report_status.loc[self.__report_status['Метка времени'].isin(
            self.__report_df['Метка времени'])]

        if col != 'Метка времени':
            self.__report_df[col] = self.__report_df[col].astype(float)

    def not_equals(self, col: str, val: str) -> None:
        """
        Процедура фильтрации колонки датафрейма по не равенству значения
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"not_equals({col}, {val})")

        self.__report_df[col] = self.__report_df[col].astype(str)

        self.__report_df = self.__report_df.loc[self.__report_df[col] != val]
        self.__report_status = self.__report_status.loc[self.__report_status['Метка времени'].isin(
            self.__report_df['Метка времени'])]

        if col != 'Метка времени':
            self.__report_df[col] = self.__report_df[col].astype(float)

    def no_filter(self, col: str, val: str) -> None:
        """
        Процедура сброса фильтра
        :param col: наименование колонки
        :param val: значение поля фильтрации
        :return:
        """
        logger.info(f"no_filter({col}, {val})")
