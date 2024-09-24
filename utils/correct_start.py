import os
import errno

from loguru import logger

import utils.constants_and_paths as constants


def check_correct_application_structure():
    """
    Процедура проверяет создание директорий веб-приложения
    :return: исключение или успешное выполнение процедуры
    """
    logger.info(f"check_correct_application_structure()")

    try:
        os.mkdir(f'{constants.DATA_DIRECTORY}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.REPORTS_DIRECTORY}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.REPORTS_CUSTOM}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.WEB_DIR}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.CLIENT_DIR}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA_TEMPLATE}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA_TEMPLATE_SOURCE}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA_TEMPLATE_SLICE}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA_TEMPLATE_GRID}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA_TEMPLATE_BOUNCE}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    try:
        os.mkdir(f'{constants.JINJA_PYLIB}')
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error(e)

    if not os.path.isfile(constants.CLIENT_SERVER_CONF):
        with open(constants.CLIENT_SERVER_CONF, "w") as writefile:
            writefile.write("")
