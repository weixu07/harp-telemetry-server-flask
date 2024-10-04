
from flask import render_template, abort, send_file, redirect, url_for, request, current_app
from werkzeug.utils import secure_filename
from . import translator_bp
from io import BytesIO
from zipfile import ZipFile
import os
import subprocess

TRANS_DIR = './harptrans/'

@translator_bp.route('/translator/')
def translator_file():
    return render_template('translator.html')

@translator_bp.post('/translator/file')
def translator_transfile():
    if request.method == 'POST':
        uploaded_file = request.files['harp_to_rean_Input']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_name = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
                abort(400)
            uploaded_file.save(os.path.join(TRANS_DIR, filename))
    
        trans_exe = os.path.join(TRANS_DIR, 'harptrans.exe') 
        trans_input = os.path.join(TRANS_DIR, filename)
        trans_output = './harpToReanimate_Param.txt'
        trans_log = file_name + '_log.txt'
        trans_log_f = open(trans_log, 'w')
        subprocess.run([trans_exe, '-p', trans_input], stdout=trans_log_f)

        try:
            open(trans_output, 'r').read() and open(trans_log, 'r').read()
        except:
            abort(500)
        
        stream = BytesIO()
        with ZipFile(stream, 'w') as zf:
            zf.write(trans_output, 'harpToReanimate_Param.txt')
            zf.write('./' + trans_log, trans_log)
        stream.seek(0)

        os.remove(trans_input)
        os.remove(trans_output)
        os.remove(trans_log)

        return send_file(stream, as_attachment=True, download_name= file_name +'.zip')
    return redirect(url_for('tranlator_bp.translator_file'))

@translator_bp.post('/translator/config')
def translator_transconfig():
    if request.method == 'POST':
        trans_config = request.form['harp_to_rean_Config']

        trans_exe = os.path.join(TRANS_DIR, 'harptrans.exe')

        ret = subprocess.run([trans_exe, '-c', trans_config], capture_output=True).stdout.decode()
        rean_configs = [item for item in ret.split() if "!cs" in item and "<" not in item]

        return render_template('translator.html', input_config=trans_config, trans_ret=rean_configs)
    return redirect(url_for('tranlator_bp.translator_file'))
