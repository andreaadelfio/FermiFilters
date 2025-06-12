import json
import os
import logging
import zipfile
import io
from flask import Flask, render_template, request, jsonify, session, send_file
from core.engine import FiltersEngine
from core.utils import Plotter, FitsReader, FilesHandler, VOHandler
from core.config import TMP_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


app = Flask(__name__)
app.secret_key = '1234'

@app.route('/')
def index():
    vo_file = os.path.join(TMP_DIR, 'fermi_vo.xml')
    files_dict = VOHandler().get_files_dict(vo_file)
    fts_list = FilesHandler().download_from_url(files_dict)
    weeks_list = files_dict.keys()
    ft1_list = fts_list['photon']
    ft2_list = fts_list['spacecraft']
    if len(ft1_list) > 1:
        ft1_output_filepath = os.path.join(TMP_DIR, f"merged_photon_{'_'.join(weeks_list)}.fits")
        FiltersEngine().gtmerge(ft1_list, ft1_output_filepath)
        ft1_file = ft1_output_filepath
        ft2_output_filepath = os.path.join(TMP_DIR, f"merged_spacecraft_{'_'.join(weeks_list)}.fits")
        FiltersEngine().ft2_merge(ft2_list, ft2_output_filepath)
        ft2_file = ft2_output_filepath
    else:
        ft1_file = ft1_list[0]
        ft2_file = ft2_list[0]
    plot_filename = os.path.join(TMP_DIR, "plot.png")
    Plotter().plot_ft_data([ft1_file], x='RA', y='DEC', plot_filename=plot_filename)
    info_dict_ft1 = FitsReader().read_info_from_ft1(ft1_file)
    info_dict_ft2 = FitsReader().read_info_from_ft2(ft2_file)
    plot_url = None
    if os.path.exists(plot_filename):
        plot_url = plot_filename
    session['ft1_file_name'] = ft1_file
    session['ft2_file_name'] = ft2_file
    session['plot_url'] = plot_url
    return render_template('template.html',
                            info_dict_ft1=info_dict_ft1,
                            info_dict_ft2=info_dict_ft2,
                            ft1_file_name=ft1_file,
                            ft2_file_name=ft2_file,
                            plot_url=plot_url)

@app.route('/apply_filters', methods=['POST'])
def apply_filters():
    plot_filename = session.get('plot_url')
    ft1_filepath = session.get('ft1_file_name')
    ft2_filepath = session.get('ft2_file_name')
    ft1_filename = os.path.basename(ft1_filepath)
    select_dict = json.loads(request.form.get('select_dict', None))
    maketime_dict = json.loads(request.form.get('maketime_dict', None))
    ecliptic_cut_dict = json.loads(request.form.get('ecliptic_cut_dict', None))
    update_plot = request.form.get('update_plot', 'off') == 'on'
    select_output_filepath = os.path.join(TMP_DIR, f"select_{ft1_filename}")
    mktime_output_filepath = os.path.join(TMP_DIR, f"mktime_{ft1_filename}")
    ecliptic_cut_output_filepath = os.path.join(TMP_DIR, f"ecliptic_cut_{ft1_filename}")
    if not select_dict and not maketime_dict and not ecliptic_cut_dict:
        return jsonify({"plot_url": None})
    plots_list = [ft1_filepath]
    if select_dict:
        if not FiltersEngine().gtselect(select_dict, ft1_filepath, select_output_filepath):
            return jsonify({"error": "Error during gtselect on FT1."})
        if update_plot:
            plots_list.append(select_output_filepath)
        ft1_filepath = select_output_filepath
    if maketime_dict:
        if not FiltersEngine().gtmktime(maketime_dict, ft1_filepath, ft2_filepath, mktime_output_filepath):
            return jsonify({"error": "Error during gtmktime."})
        if update_plot:
            plots_list.append(mktime_output_filepath)
        ft1_filepath = mktime_output_filepath
    if ecliptic_cut_dict:
        if not FiltersEngine().ecliptic_cut(ecliptic_cut_dict, ft1_filepath, ft2_filepath, ecliptic_cut_output_filepath):
            return jsonify({"error": "Error during ecliptic cut."})
        if update_plot:
            plots_list.append(ecliptic_cut_output_filepath)
    if update_plot:
        Plotter().plot_ft_data(plots_list, x='RA', y='DEC', plot_filename=plot_filename)
    return jsonify({"plot_url": plot_filename})


@app.route('/download_all')
def download_all():
    files_to_zip = []
    for fname in os.listdir(TMP_DIR):
        if fname.endswith('.fits') or fname.endswith('.png'):
            files_to_zip.append(os.path.join(TMP_DIR, fname))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for file_path in files_to_zip:
            print(file_path, os.path.basename(file_path))
            zipf.write(file_path, arcname=os.path.basename(file_path))
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='fermi_results.zip')

if __name__ == '__main__':

    app.run(debug=True)