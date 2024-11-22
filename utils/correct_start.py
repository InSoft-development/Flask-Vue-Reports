"""
Модуль содержит функции подготовки к развертывания и запуску веб-приложения
"""
import os
import errno

import utils.constants_and_paths as constants

from loguru import logger

from typing import Dict, List, Tuple, Union


def check_correct_application_structure() -> None:
    """
    Процедура проверяет создание директорий веб-приложения
    :return: исключение или успешное выполнение процедуры
    """
    logger.info(f"check_correct_application_structure()")

    directories_list = [constants.DATA_DIRECTORY, constants.REPORTS_DIRECTORY, constants.REPORTS_CUSTOM,
                        constants.WEB_DIR, constants.CLIENT_DIR, constants.JINJA, constants.JINJA_TEMPLATE,
                        constants.JINJA_TEMPLATE_SOURCE, constants.JINJA_TEMPLATE_SLICE, constants.JINJA_TEMPLATE_GRID,
                        constants.JINJA_TEMPLATE_BOUNCE, constants.JINJA_PYLIB]

    for directory in directories_list:
        try:
            os.mkdir(f'{directory}')
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.error(e)

    if not os.path.isfile(constants.CLIENT_SERVER_CONF):
        with open(constants.CLIENT_SERVER_CONF, "w") as writefile:
            writefile.write("")
