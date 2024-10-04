
from flask import render_template, abort, render_template_string
from . import dsn_bp
from typing import List, Tuple, Dict
from app import udp
import os
import time

from hts_plotter import HtsPlotter


OUTPUT_DIR = './output/'

@dsn_bp.route('/dsns/')
def dsn_list():
    global OUTPUT_DIR

    rows: List[str] = []

    for dsn_dir in os.listdir(OUTPUT_DIR):
        if not os.path.isdir(os.path.join(OUTPUT_DIR, dsn_dir)):
            continue
        rows.append(dsn_dir)
    
    return render_template('device_list.html', dsns=rows)

@dsn_bp.get('/dsns/<dsn>')
def dsn_page(dsn):
    global OUTPUT_DIR

    rows: List[Tuple[str, str, float]] = []

    if dsn not in os.listdir(OUTPUT_DIR):
        abort(404)
    
    dsn_dir = os.path.join(OUTPUT_DIR, dsn)

    for file in os.listdir(dsn_dir):
        filepath = os.path.join(dsn_dir, file)
        if not os.path.isfile(filepath) or not filepath.endswith('.csv'):
            continue
        file_dispname = file.replace(dsn + "_", "").replace(".csv", "")

        ftime = os.path.getmtime(filepath)
        ftime_str = time.strftime('%H:%M:%S %m/%d/%Y %Z', time.localtime(ftime))
        row = [dsn, file_dispname, file, ftime_str]
        rows.append(row)

        #sort by modify time
        rows = list(sorted(rows, key=lambda row: row[2], reverse=True))
    
    return render_template('device.html', dsn_name=dsn, dsn_Array=rows)

@dsn_bp.get('/dsns/<dsn>/<log>/plot')
def dsn_log_plot(dsn, log):
    global OUTPUT_DIR

    print(f'Look for {dsn} - {log}')

    dsn_dir = os.path.join(OUTPUT_DIR, dsn)
    if not os.path.isdir(dsn_dir):
        abort(404)

    csv_path = os.path.join(dsn_dir, f'{dsn}_{log}.csv')
    html_path = os.path.join(dsn_dir, f'{dsn}_{log}.html')
    if not os.path.isfile(csv_path):
        abort(404)
    
    need_generate = True

    if os.path.isfile(html_path):
        csv_time = os.path.getmtime(csv_path)
        html_time = os.path.getmtime(html_path)
        if csv_time <= html_time:
            need_generate = False
    
    if need_generate:
        hts_plotter = HtsPlotter(csv_path)
        print('Generating plot...')
        try:
            hts_plotter.plot_csv_file(csv_path, html_path)
        except Exception as e:
            print(e)
            return WebAppResponse(500)
    
    if not os.path.isfile(html_path):
        abort(500, 'Failed to generate plot')
    
    body = open(html_path, 'r').read()
    return render_template_string(body)




