from enum import Enum

from loguru import logger

from gevent import Greenlet
from pandas import DataFrame
from typing import List, Dict, Union


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
    client_mode: Union[None, str]
    kks_all: Union[None, DataFrame]
    kks_all_back: Union[None, DataFrame]
    report_df: Union[None, DataFrame]
    report_status: Union[None, DataFrame]

    def __init__(self):
        self.__client_mode = None
        self.__kks_all = None
        self.__kks_all_back = None
        self.__report_df = None
        self.__report_status = None

    @property
    def client_mode(self):
        return self.__client_mode

    @client_mode.setter
    def client_mode(self, mode: str):
        self.__client_mode = mode

    @property
    def kks_all(self):
        return self.__kks_all

    @kks_all.setter
    def kks_all(self, kks_frame: DataFrame):
        self.__kks_all = kks_frame

    @property
    def kks_all_back(self):
        return self.__kks_all_back

    @kks_all_back.setter
    def kks_all_back(self, kks_back_frame: DataFrame):
        self.__kks_all_back = kks_back_frame

    @property
    def report_df(self):
        return self.__report_df

    @report_df.setter
    def report_df(self, report: DataFrame):
        self.__report_df = report

    @property
    def report_status(self):
        return self.__report_status

    @report_status.setter
    def report_status(self, status: DataFrame):
        self.__report_status = status
