from flask import render_template, abort, send_file, redirect, url_for, request, current_app
from . import udp_bp
from typing import List, Tuple, Dict
import os
from app import udp
import json

PARAM_DIR = './paramsets/'

@udp_bp.route('/udp_ports/')
def udp_ports():
    global PARAM_DIR
    
    rows = []
    ports = []
    for udp_obj in udp.config.get("UDP_objs"):
        port = int(udp_obj["port"])
        ports.append(port)
        paramConfig = udp_obj["paramset"]
        paramConfigpath = os.path.join(PARAM_DIR, paramConfig)
        row = []
        params = []
        if not os.path.isfile(paramConfigpath) or not paramConfig.endswith('.txt'):
            continue

        for param in os.listdir(PARAM_DIR):
            
            if param == paramConfig:
                continue
            else:
                params.append(param)

        row = [port, paramConfig, params]
        rows.append(row)

    return render_template('udp_ports.html', udps=rows, port_Array=ports)


@udp_bp.post('/udp_ports/new_paramset')
def udp_run():
    if request.method != 'POST':
        abort(400)
    
    try:
        obj = request.get_json()
    except:
        abort(400)
    
    port = obj.get('port')
    if port is None:
        return abort(400)
    
    paramset = obj.get('paramset')
    if paramset is None:
        return abort(400)
    
    # reset config and restart
    udp.reset_config(obj)

    return render_template('udp_ports.html')





