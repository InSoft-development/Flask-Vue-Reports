from flask import Flask, request
from flask_cors import CORS
from flask.helpers import send_file

import argparse

from loguru import logger


VERSION = '1.0.0'

clients = {}

app = Flask(__name__, static_folder="./web", template_folder="./web", static_url_path="")
CORS(app)


@app.route("/", defaults={"path": ""})
@app.route("/<string:path>")
@app.route("/<path:path>")
def catch_all(path):
    return app.send_static_file("index.html")


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
    app.run(host=args.host, port=args.port)
