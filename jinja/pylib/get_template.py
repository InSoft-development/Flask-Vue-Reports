from jinja2 import Environment, FileSystemLoader, BaseLoader
import pdfkit
import os
import json
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

import utils.constants_and_paths as constants

from loguru import logger


def get_unfilled_html_from_source(content_for_render):
    logger.info(f"get_unfilled_html_from_source()")
    file_loader = FileSystemLoader(searchpath=constants.JINJA_TEMPLATE_SOURCE)
    env = Environment(loader=file_loader)
    tm = env.get_template('template.html')
    default_html = tm.render(content=content_for_render)
    return default_html


def render_slice(json_slice_table):
    logger.info(f"render_slice(json_slice_table)")
    # Рендерим header, content, footer
    with open(constants.JINJA_TEMPLATE_SLICE_TABLE, 'r') as slice_table_template_html:
        html_template = get_unfilled_html_from_source(slice_table_template_html.read())

    # Рендерим html
    string_loader = BaseLoader()
    env = Environment(loader=string_loader).from_string(html_template)
    html = env.render(rows=json_slice_table)
    pdfkit.from_string(html, constants.REPORT_SLICE, options=constants.PDF_OPTIONS)


def render_grid(json_code_table, json_grid_table_list, json_grid_status_table_list,
                json_grid_table_list_single, json_grid_status_table_list_single, parameters_of_request):
    logger.info(f"render_grid(json_code_table, json_grid_table_list, json_grid_status_table_list,"
                f"json_grid_table_list_single, json_grid_status_table_list_single, parameters_of_request)")

    # Рендерим таблицу обозначений сигналов - шаблон table_code.html
    file_loader = FileSystemLoader(searchpath=constants.JINJA_TEMPLATE_GRID)
    env = Environment(loader=file_loader)
    tm = env.get_template('table_code.html')
    table_render_html = tm.render(rows=json_code_table)

    # Рендерим сетку - шаблон table_grid.html
    tm = env.get_template('table_grid.html')

    for (json_grid_table, json_grid_status_table) in zip(json_grid_table_list, json_grid_status_table_list):
        table_grid_html = tm.render(rows=json_grid_table, status=json_grid_status_table)
        table_render_html += table_grid_html

    # Рендерим отчеты по каждому датчику
    tm = env.get_template('sensor.html')
    sensor_html_list = [tm.render(rows=sensor_table, status=sensor_status_table,
                                  data_x=[row["Метка времени"] for row in sensor_table],
                                  data_y=[row[list(row)[-1]] if row[list(row)[-1]] != "NaN" else 0 for row in sensor_table],
                                  parameters=parameters_of_request,
                                  sensor_title=json_code_table[index]["Обозначение сигнала"]
                                  ) for index, (sensor_table, sensor_status_table)
                        in enumerate(zip(json_grid_table_list_single, json_grid_status_table_list_single))]

    # Рендерим header, content, footer
    html = get_unfilled_html_from_source(table_render_html)

    # Рендерим header, content, footer для отчета по каждому датчику
    sensor_html_list = [get_unfilled_html_from_source(sensor) for sensor in sensor_html_list]

    # Рендерим общий html
    pdfkit.from_string(html, constants.REPORT_GRID, options=constants.PDF_OPTIONS)
    logger.info(f"Общий html срендерен")

    # Сохраняем архив
    with ZipFile(constants.REPORT_GRID_ZIP, 'w', compression=ZIP_DEFLATED) as zip_file:
        zip_file.write(constants.REPORT_GRID, arcname="grid.pdf")
        # Добавляем в архив отчет по каждому датчику
        for index, sensor in enumerate(sensor_html_list):
            zip_file.writestr(data=sensor, zinfo_or_arcname=f"{index}.html")
            logger.info(f"{index}.html добавлен в архив")

        # # Добавляем стили и js скрипты в архив
        # for file_path, file_name in constants.DOWNLOADED_STYLES_AND_JS_PATH.items():
        #     zip_file.write(file_path, arcname=file_name)
        #     logger.info(f"{file_name} добавлен в архив")


def render_bounce(json_bounce_table, parameters_of_request):
    logger.info(f"render_slice(json_bounce_table, parameters_of_request)")
    # Рендерим header, content, footer
    with open(constants.JINJA_TEMPLATE_BOUNCE_TABLE, 'r') as bounce_table_template_html:
        html_template = get_unfilled_html_from_source(bounce_table_template_html.read())

    # Рендерим html
    string_loader = BaseLoader()
    env = Environment(loader=string_loader).from_string(html_template)
    html = env.render(rows=json_bounce_table, parameters=parameters_of_request)
    pdfkit.from_string(html, constants.REPORT_BOUNCE, options=constants.PDF_OPTIONS)
