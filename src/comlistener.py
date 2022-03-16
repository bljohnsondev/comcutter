#!/usr/bin/env python

import json
import logging
from flask import Flask, request, jsonify
from waitress import serve

from configurator import Configurator
from comskipper import CommercialSkipper

api = Flask(__name__)

config = Configurator()
if config is None or config.is_ready() == False:
    quit()
    
logging_filepath = "comcutter.log"

log_level = logging.DEBUG
log_level_config = config.get("api", "log_level") or "debug"
if log_level_config == "info":
    log_level = logging.INFO
elif log_level_config == "warning":
    log_level = logging.WARNING
elif log_level_config == "error":
    log_level = logging.ERROR

log_dir = config.get("api", "log_dir")
if log_dir is not None and log_dir != "":
    logging_filepath = log_dir + "/comcutter.log"

if log_dir is None:
    print("writing logs to console")
    logging.basicConfig(
        format='%(asctime)s - %(levelname)-8s: %(message)s',
        datefmt='%m-%d-%Y %I:%M:%S %p',
        level=log_level
    )
else:
    print("writing logs to: " + logging_filepath)
    logging.basicConfig(
        filename=logging_filepath,
        format='%(asctime)s - %(levelname)-8s: %(message)s',
        datefmt='%m-%d-%Y %I:%M:%S %p',
        level=log_level
    )

comskipper = CommercialSkipper(logging, config)

apikey = config.get("api", "apikey")
port = config.get("api", "port") or 8080

if apikey is None or apikey == "":
    print("could not find api:apikey in config file")
    quit()

def prefixlogmsg(request, msg):
    return "[%s] %s" % (request.remote_addr, msg)

@api.route('/comskip', methods=['POST'])
def index():
    data = json.loads(request.data)

    if "api" not in data:
        logging.warning(prefixlogmsg(request, "unauthorized: no api key"))
        return jsonify({ "error": "unauthorized" }), 401
    
    if data["api"] is None or data["api"] != apikey:
        logging.warning(prefixlogmsg(request, "unauthorized: incorrect api key"))
        return jsonify({ "error": "unauthorized" }), 401

    if "file" not in data or data["file"] == "":
        logging.debug(prefixlogmsg(request, "file not specified"))
        return jsonify({ "error": "file not specified" }), 400

    success, msg = comskipper.skip(request.remote_addr, data["file"])

    return jsonify(
        {
            'success': success,
            'msg': msg,
            'file': data["file"],
        }
    )

if __name__ == '__main__':
    print("listening on port " + str(port))
    serve(api, host="0.0.0.0", port=port)
