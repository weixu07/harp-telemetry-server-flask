from flask import Flask
from dynaconf import FlaskDynaconf
from hts import HTS, load_config
from typing import List, Tuple, Dict
from pathlib import Path
import json
import os
import yaml
import logging
import logging.config

def create_app():
    app = Flask(__name__)
    dynaconf = FlaskDynaconf(extensions_list=True)
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
    app.config['UPLOAD_EXTENSIONS'] = ['.txt']

    with app.app_context():

        # initialize plugins
        os.environ["ROOT_PATH_FOR_DYNACONF"] = app.root_path
        dynaconf.init_app(app)

        _configure_logging(app, dynaconf)

        from . import main
        from . import paramset
        from . import udport
        from . import dsn
        from . import translator
        from . import compiler

        app.register_blueprint(main.main_bp)
        app.register_blueprint(paramset.paramset_bp)
        app.register_blueprint(udport.udp_bp)
        app.register_blueprint(dsn.dsn_bp)
        app.register_blueprint(translator.translator_bp)
        app.register_blueprint(compiler.compiler_bp)

        return app

def _configure_logging(app, dynaconf):
    # configure logging
    logging_config_path = Path(app.root_path).parent / "logging_config.yaml"
    with open(logging_config_path, "r") as fh:
        logging_config = yaml.safe_load(fh.read())
        env_logging_level = dynaconf.settings.get("logging_level", "INFO").upper()
        logging_level = logging.INFO if env_logging_level == "INFO" else logging.DEBUG
        logging_config["handlers"]["console"]["level"] = logging_level
        logging_config["loggers"][""]["level"] = logging_level
        logging.config.dictConfig(logging_config)


### HTS UDP server ###

OUTPUT_DIR = './output'
PARAM_DIR = './paramsets'
CONFIG_FILE_NAME = 'hts_config.json'

class UDP():
    """UDP containder for address, port and paramset"""
    global OUTPUT_DIR

    config: json
    """UDP config"""
    ports_servers: Dict[int, HTS]
    """UDP servers mapping at ports"""
    ports_parameters: Dict[int, str]
    """current ports and parameters mapping"""

    def __init__(self, config):
        self.config = config
        self.ports_servers: Dict[int, HTS] = {}
        self.ports_parameters: Dict[int, str] = {}

        self.default_run()

    def default_run(self):
        for obj in self.config.get("UDP_objs"):
            port = int(obj["port"])
            self.ports_parameters[port] = obj["paramset"]
            config, pcrs_hash = load_config(os.path.join(PARAM_DIR, self.ports_parameters[port]))
            self.ports_servers[port] = HTS(config, pcrs_hash, self.config.get("UDP_addr"), port, OUTPUT_DIR)
            self.ports_servers[port].start()
    
    def write_config(self):
        path = os.path.dirname(os.path.realpath(__name__))
        fullname = os.path.join(path, CONFIG_FILE_NAME)
        with open(fullname, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
        

    def reset_config(self, obj_new: Dict[int, str]):
        # looking the sever is running or not
        # if running base port number kill it 
        # change paramset and start upd again
        # overwrite hts_config joson
        port = int(obj_new["port"])
        if port in self.ports_servers and (port, obj_new["paramset"]) not in self.ports_parameters:
            self.ports_servers[port].kill()
            self.ports_servers[port].join()
            self.ports_parameters[port] = obj_new["paramset"]
            for obj in self.config.get("UDP_objs"):
                if int(obj["port"]) == port: obj["paramset"] = obj_new["paramset"]
            
            config, pcrs_hash = load_config(os.path.join(PARAM_DIR, self.ports_parameters[port]))
            self.ports_servers[port] = HTS(config, pcrs_hash, self.config.get("UDP_addr"), port, OUTPUT_DIR)
            self.ports_servers[port].start()
            self.write_config()

    def kill(self):
        for ports_server in self.ports_servers:
            ports_server.kill()
            ports_server.join()

udp: UDP

hts_conf = json.loads(open('hts_config.json', 'r').read())
udp = UDP(hts_conf)