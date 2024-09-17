from flask import Flask
from flask_cors import CORS
from flask.helpers import send_file

import argparse

from loguru import logger

import utils.constants_and_paths as constants


VERSION = '1.0.0'

clients = {}

app = Flask(__name__, static_folder="./web", template_folder="./web", static_url_path="")
CORS(app)


@app.route("/", defaults={"path": ""})
@app.route("/<string:path>")
@app.route("/<path:path>")
def catch_all(path):
    return app.send_static_file("index.html")


@app.route("/tags.csv")
def get_tags_csv():
    return send_file(constants.CSV_TAGS)


@app.route("/signals_slice.csv")
def get_signals_slice_csv():
    return send_file(constants.CSV_SIGNALS)


@app.route("/code.csv")
def get_code_csv():
    return send_file(constants.CSV_CODE)


@app.route("/grid.csv")
def get_grid_csv():
    return send_file(constants.CSV_GRID)


@app.route("/bounce.csv")
def get_bounce_csv():
    return send_file(constants.CSV_BOUNCE)


@app.route("/config.json")
def get_config_json():
    return send_file(constants.CONFIG)


@app.route("/signals_slice.pdf")
def get_signals_slice_pdf():
    return send_file(constants.REPORT_SLICE)


@app.route("/grid.zip")
def get_grid_zip():
    return send_file(constants.REPORT_GRID_ZIP)


@app.route("/bounce.pdf")
def get_bounce_pdf():
    return send_file(constants.REPORT_BOUNCE)


def parse_args():
    parser = argparse.ArgumentParser(description="start flask + vue 3 web-application")
    parser.add_argument("-ip", "--host", type=str, help="specify IPv4 address of host", default='localhost')
    parser.add_argument("-p", "--port", type=int, help="specify port")
    parser.add_argument("-v", "--version", action="version", help="print version", version=f'{VERSION}')
    return parser.parse_args()


if __name__ == '__main__':
    try:
        args = parse_args()
    except SystemExit:
        logger.info(f'{VERSION} flask socket io + vue 3 web-application version')
        exit(0)
    logger.info("started")
    app.run(host=args.host, port=args.port, ssl_context=(constants.SSL_CERT, constants.SSL_KEY))
