from flask import render_template, abort, send_file, redirect, url_for, request, current_app
from werkzeug.utils import secure_filename
from . import paramset_bp
from typing import List, Tuple, Dict
from app import udp
from logging import getLogger
import os

logger = getLogger(__file__)

PARAM_DIR = './paramsets/'

@paramset_bp.route('/params/')
def param_list():
    global PARAM_DIR

    rows: List[str] = []

    for param in os.listdir(PARAM_DIR):
        ports = []
        portstr = ''
        for udp_obj in udp.config.get("UDP_objs"):
            if param == udp_obj["paramset"]:
                ports.append(udp_obj["port"])
                portstr = ' '.join(str(x) for x in ports)

        parampath = os.path.join(PARAM_DIR, param)
        if not os.path.isfile(parampath) or not parampath.endswith('.txt'):
            continue
        row = [param, portstr]
        rows.append(row)
    logger.debug("rendering paramset page")
    return render_template('param_list.html', params=rows)

@paramset_bp.get('/params/<param_name>/')
def param_view(param_name):
    global PARAM_DIR

    # /params/<param_name>
    fullpath = os.path.join(PARAM_DIR, param_name)

    if not os.path.isfile(fullpath):
        abort(404)
    
    param_lines = open(fullpath, 'r').read()
    return render_template('param_content.html', PARAM_NAME=param_name, PARAM_CONTENT=param_lines)

@paramset_bp.get('/params/download/<param_name>/')
def param_download(param_name):
    global PARAM_DIR
    
    fullpath = os.path.join(PARAM_DIR, param_name)

    print(f'Look for param {param_name}')

    if not os.path.isfile(fullpath):
        abort(404)
    
    try:
        open(fullpath, 'r').read()
    except:
        abort(500)
    
    return send_file(os.path.abspath(fullpath), as_attachment=True)

@paramset_bp.post('/params/upload/')
def param_upload():
    if request.method == 'POST':
        uploaded_file = request.files['ParamsetInput']
        filename = secure_filename(uploaded_file.filename)
        print(filename)
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
                abort(400)
            uploaded_file.save(os.path.join(PARAM_DIR, filename))
    return redirect(url_for('paramset_bp.param_list'))
