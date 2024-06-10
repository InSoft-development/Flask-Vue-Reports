import os
import errno

from loguru import logger

import constants_and_paths as constants

logger.info(f"start utils{os.sep}prepare_structure.py")


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
    os.mkdir(f'{constants.WEB_DIR_REPORT}')
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

logger.info(f"script finished")
