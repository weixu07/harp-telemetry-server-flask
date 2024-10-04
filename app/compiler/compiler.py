from flask import render_template, abort, send_file, redirect, url_for, request, current_app
from werkzeug.utils import secure_filename
from . import compiler_bp
from io import BytesIO
from zipfile import ZipFile
import os
import subprocess

COMP_DIR = './interp_lang_compiler/'

@compiler_bp.route('/compiler/')
def compiler_file():
    return render_template('compiler.html')

@compiler_bp.post('/compiler/rean_script')
def compiler_compfile():
    if request.method == 'POST':
        uploaded_file = request.files['rean_script_Input']
        filename = secure_filename(uploaded_file.filename)
        if filename != '':
            file_name = os.path.splitext(filename)[0]
            file_ext = os.path.splitext(filename)[1]
            if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
                abort(400)
            uploaded_file.save(os.path.join(COMP_DIR, filename))
        print(filename)

        comp_exe = os.path.join(COMP_DIR, 'ilc.exe')
        comp_input = os.path.join(COMP_DIR, filename)
        comp_output = os.path.join(COMP_DIR, file_name) + '.bin'
        comp_log = os.path.join(COMP_DIR, file_name) + '_log.txt'
        comp_log_f = open(comp_log, 'w')
        subprocess.run([comp_exe, comp_input], stdout=comp_log_f)

        if not os.path.isfile(comp_output):
            abort(404, {'message': 'compiling script failed...'})
        
        stream = BytesIO()
        with ZipFile(stream, 'w') as zf:
            zf.write(comp_output, file_name + '.bin')
            zf.write(comp_log, file_name + '_log.txt')
        stream.seek(0)

        os.remove(comp_input)
        os.remove(comp_output)
        os.remove(comp_log)

        return send_file(stream, as_attachment=True, download_name= file_name +'.zip')
    
    return redirect(url_for('compiler_bp.compiler_file'))

