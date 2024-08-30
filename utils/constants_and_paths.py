"""
Модуль содержит все использеумые в приложении константы
"""
import os

DATA_DIRECTORY = f'data{os.sep}'
DATA_ANALOG = f'{DATA_DIRECTORY}data_AM.txt'
DATA_DISCRETE = f'{DATA_DIRECTORY}democub_all.csv'
DATA_KKS_ALL = f'{DATA_DIRECTORY}kks_all.csv'
DATA_KKS_ALL_BACK = f'{DATA_DIRECTORY}kks_all_back.csv'
DATA_DEFAULT_FIELDS_CONFIG = f'{DATA_DIRECTORY}default_fields.json'

REPORTS_DIRECTORY = f'reports{os.sep}'
REPORTS_CUSTOM = f'{REPORTS_DIRECTORY}custom{os.sep}'

REPORTS_ANALOG_SLICES = f'{REPORTS_DIRECTORY}analog_slice.pdf'
REPORTS_DISCRETE_SLICES = f'{REPORTS_DIRECTORY}discrete_slice.pdf'
REPORTS_ANALOG_GRID = f'{REPORTS_DIRECTORY}analog_grid.pdf'
REPORTS_DISCRETE_GRID = f'{REPORTS_DIRECTORY}discrete_grid.pdf'
REPORTS_BOUNCE = f'{REPORTS_DIRECTORY}bounce.pdf'

CSV_ANALOG_SLICES = f'{REPORTS_DIRECTORY}analog_slice.csv'
CSV_DISCRETE_SLICES = f'{REPORTS_DIRECTORY}discrete_slice.csv'
CSV_ANALOG_GRID = f'{REPORTS_DIRECTORY}analog_grid.csv'
CSV_DISCRETE_GRID = f'{REPORTS_DIRECTORY}discrete_grid.csv'
CSV_BOUNCE = f'{REPORTS_DIRECTORY}bounce.csv'
CSV_SIGNALS = f'{REPORTS_DIRECTORY}signals_slice.csv'
CSV_GRID = f'{REPORTS_DIRECTORY}grid.csv'
CSV_GRID_STATUS = f'{REPORTS_DIRECTORY}grid_status.csv'
CSV_CODE = f'{REPORTS_DIRECTORY}code.csv'
CSV_TAGS = f'{REPORTS_DIRECTORY}tags.csv'

WEB_DIR = f'web{os.sep}'
WEB_DIR_REPORT = f'{WEB_DIR}report{os.sep}'
WEB_DIR_REPORT_SLICE = f'{WEB_DIR_REPORT}signals_slice.pdf'
WEB_DIR_REPORT_GRID = f'{WEB_DIR_REPORT}grid.pdf'
WEB_DIR_REPORT_GRID_ZIP = f'{WEB_DIR_REPORT}grid.zip'
WEB_DIR_REPORT_BOUNCE = f'{WEB_DIR_REPORT}bounce.pdf'
WEB_DIR_ASSETS = f'{WEB_DIR}assets{os.sep}'
WEB_DIR_ASSETS_INDEX_JS = f'{WEB_DIR_ASSETS}index-DOhmVhGx.js'

CLIENT_DIR = f'client{os.sep}'
CLIENT_BINARY = f'{CLIENT_DIR}client_lesson02.so'
CLIENT_COMMON_DATA = f'{CLIENT_DIR}common_data.sqlite'
CLIENT_COMMON_DATA_TABLE = f'common_data'
CLIENT_DYNAMIC_TABLE = f'dynamic_data'
CLIENT_DATA = f'{CLIENT_DIR}data.sqlite'
CLIENT_KKS = f'{CLIENT_DIR}kks.csv'
CLIENT_SLICES = f'{CLIENT_DIR}slices.csv'
CLIENT_SLICES_STATUS = f'{CLIENT_DIR}slices_status.csv'
CLIENT_SLICER_SCRIPT = f'{CLIENT_DIR}slicer_for_streamlit.py'
CLIENT_SERVER_CONF = f'{CLIENT_DIR}server.conf'
CLIENT_CLICKHOUSE_SERVER_CONF = f'{CLIENT_DIR}serverCH.conf'
CLIENT_CHOOSEN_MODE = f'{CLIENT_DIR}mode.conf'

JINJA = f'jinja{os.sep}'
JINJA_TEMPLATE = f'{JINJA}template{os.sep}'

JINJA_TEMPLATE_SOURCE = f'{JINJA_TEMPLATE}source{os.sep}'
JINJA_TEMPLATE_SOURCE_HEADER = f'{JINJA_TEMPLATE_SOURCE}header.html'
JINJA_TEMPLATE_SOURCE_TEMPLATE = f'{JINJA_TEMPLATE_SOURCE}template.html'
JINJA_TEMPLATE_SOURCE_FOOTER = f'{JINJA_TEMPLATE_SOURCE}footer.html'

JINJA_TEMPLATE_SLICE = f'{JINJA_TEMPLATE}slice{os.sep}'
JINJA_TEMPLATE_SLICE_TABLE = f'{JINJA_TEMPLATE_SLICE}table.html'

JINJA_TEMPLATE_GRID = f'{JINJA_TEMPLATE}grid{os.sep}'
JINJA_TEMPLATE_GRID_TABLE_CODE = f'{JINJA_TEMPLATE_GRID}table_code.html'
JINJA_TEMPLATE_GRID_TABLE_GRID = f'{JINJA_TEMPLATE_GRID}table_grid.html'
JINJA_TEMPLATE_GRID_SENSOR = f'{JINJA_TEMPLATE_GRID}sensor.html'

JINJA_TEMPLATE_BOUNCE = f'{JINJA_TEMPLATE}bounce{os.sep}'
JINJA_TEMPLATE_BOUNCE_TABLE = f'{JINJA_TEMPLATE_BOUNCE}table.html'

JINJA_PYLIB = f'{JINJA}pylib{os.sep}'


QUALITY = [
    "8 - (BNC) - ОТКАЗ СВЯЗИ (TIMEOUT)",
    "16 - (BSF) - ОТКАЗ ПАРАМ",
    "24 - (BCF) - ОТКАЗ СВЯЗИ",
    "28 - (BOS) - ОТКАЗ ОБСЛУЖ",
    "88 - (BLC) - ОТКАЗ РАСЧЕТ",
    "192 - (GOD) – ХОРОШ",
    "200 - (GLC) - ХОРОШ РАСЧЕТ",
    "216 - (GFO) - ХОРОШ ИМИТИР",
    "224 - (GLT) - ХОРОШ ЛОКАЛ ВРЕМ"
]

QUALITY_DICT = {
    'BadNoCommunication': 8,
    'BadSensorFailure': 16,
    'BadCommunicationFailure': 24,
    'BadDeviceFailure': 28,
    'UncertainLastUsableValue': 88,
    'Good': 192,
    'GoodХОРОШ РАСЧЕТ': 200,
    'GoodХОРОШ ИМИТИР': 216,
    'GoodLocalTime': 224,
}

QUALITY_CODE_DICT = {
    '8 - (BNC) - ОТКАЗ СВЯЗИ (TIMEOUT)': 'BadNoCommunication',
    '16 - (BSF) - ОТКАЗ ПАРАМ': 'BadSensorFailure',
    '24 - (BCF) - ОТКАЗ СВЯЗИ': 'BadCommunicationFailure',
    '28 - (BOS) - ОТКАЗ ОБСЛУЖ': 'BadDeviceFailure',
    '88 - (BLC) - ОТКАЗ РАСЧЕТ': 'UncertainLastUsableValue',
    '192 - (GOD) – ХОРОШ': 'Good',
    '200 - (GLC) - ХОРОШ РАСЧЕТ': 'GoodХОРОШ РАСЧЕТ',
    '216 - (GFO) - ХОРОШ ИМИТИР': 'GoodХОРОШ ИМИТИР',
    '224 - (GLT) - ХОРОШ ЛОКАЛ ВРЕМ': 'GoodLocalTime'
}

BAD_CODE_LIST = ['BadNoCommunication', 'BadSensorFailure', 'BadCommunicationFailure',
                 'BadDeviceFailure', 'UncertainLastUsableValue']
BAD_NUMERIC_CODE_LIST = [8, 16, 24, 28, 88]

DELTA_INTERVAL_IN_SECONDS = {
    'day': 86400,
    'hour': 3600,
    'minute': 60,
    'second': 1
}

INTERVAL_TO_LOCALE = {
    'day': 'день',
    'hour': 'час',
    'minute': 'минута',
    'second': 'секунда'
}

BACK_SEARCH_TIME_IN_HOUR = 8760  # Предельное время поиска в глубину в часах
STEP_OF_BACK_SEARCH = 720  # Глубина поиска в архивах

COUNT_OF_RETURNED_KKS = 10000  # Число возвращаемых тегов kks при фильтрации

PDF_OPTIONS = {
    'page-size': 'A4',
    'orientation': 'Landscape',
    'margin-top': '0.35in',
    'margin-right': '0.75in',
    'margin-bottom': '0.75in',
    'margin-left': '0.75in',
    'encoding': "UTF-8",
    'no-outline': None,
    'enable-local-file-access': None
}

SEPARATED_COUNT = 5

FIRST = 0
LAST = 30
