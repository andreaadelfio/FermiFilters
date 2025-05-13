import json
import os
import logging
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template, request, url_for, jsonify
from astropy.io import fits
from astropy.coordinates import SkyCoord
from scipy.interpolate import interp1d
import astropy.units as u
import gt_apps

matplotlib.use('Agg')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


app = Flask(__name__)

def gtselect(select_dict, ft1_file, output_file) -> bool:
    '''
    Selects events from the input FT1 file based on the input selection criteria.

    Parameters:
    ----------
        select_dict: Dictionary containing the selection criteria.
        ft1_file: Input FT1 file.
        output_file: Output FT1 file.
    
    Returns:
    -------
        True if the selection was successful, False otherwise.
    '''
    logging.info(" gtselect: %s", select_dict)
    gt_apps.filter['infile'] = ft1_file
    gt_apps.filter['evclass'] = 128
    gt_apps.filter['evtable'] = "EVENTS"
    gt_apps.filter['evtype'] = 3
    gt_apps.filter['outfile'] = output_file
    gt_apps.filter['zmax'] = select_dict['zenith_angle'][1] if 'zenith_angle' in select_dict else 180
    gt_apps.filter['zmin'] = select_dict['zenith_angle'][0] if 'zenith_angle' in select_dict else 0
    gt_apps.filter['emin'] = select_dict['energy'][0] if 'energy' in select_dict else 30
    gt_apps.filter['emax'] = select_dict['energy'][1] if 'energy' in select_dict else 300000
    gt_apps.filter['ra'] = select_dict['ra'] if 'ra' in select_dict else 'INDEF'
    gt_apps.filter['dec'] = select_dict['dec'] if 'dec' in select_dict else 'INDEF'
    gt_apps.filter['rad'] = select_dict['radius'] if 'radius' in select_dict else 'INDEF'
    logging.info(" gtselect: running with following parameters \n - infile: %s\n - outfile: %s\n - zmax: %s\n - zmin: %s\n - emin: %s\n - emax: %s\n - ra: %s\n - dec: %s\n - rad: %s", gt_apps.filter['infile'], gt_apps.filter['outfile'], gt_apps.filter['zmax'], gt_apps.filter['zmin'], gt_apps.filter['emin'], gt_apps.filter['emax'], gt_apps.filter['ra'], gt_apps.filter['dec'], gt_apps.filter['rad'])
    try:
        gt_apps.filter.run(print_command=False)
    except Exception as e:
        logging.error("Error during gtselect: %s", e)
        return False
    return True

def gtmktime(maketime_dict, ft1_file, ft2_file, output_file) -> bool:
    '''
    Creates a GTI extension for the input FT1 file based on the input maketime criteria.

    Parameters:
    ----------
        maketime_dict: Dictionary containing the maketime criteria.
        ft1_file: Input FT1 file.
        ft2_file: Input FT2 file.
        output_file: Output FT1 file.

    Returns:
    -------
        True if the maketime was successful, False otherwise.
    '''
    logging.info(" gtmktime: %s", maketime_dict)
    gt_apps.maketime['scfile'] = ft2_file
    gt_apps.maketime['sctable'] = "SC_DATA"
    gt_apps.maketime['filter'] = maketime_dict['filter_expr'] if 'filter_expr' in maketime_dict else ''
    gt_apps.maketime['roicut'] = maketime_dict['roicut'] if 'roicut' in maketime_dict else False
    gt_apps.maketime['evfile'] = ft1_file
    gt_apps.maketime['evtable'] = "EVENTS"
    gt_apps.maketime['outfile'] = output_file
    gt_apps.maketime['apply_filter'] = "yes"
    gt_apps.maketime['overwrite'] = "no"
    gt_apps.maketime['header_obstimes'] = "yes"
    gt_apps.maketime['tstart'] = 0.0
    gt_apps.maketime['tstop'] = 0.0
    gt_apps.maketime['gtifile'] = "default"
    gt_apps.maketime['chatter'] = 2
    gt_apps.maketime['clobber'] = "yes"
    gt_apps.maketime['debug'] = "no"
    gt_apps.maketime['gui'] = "no"
    gt_apps.maketime['mode'] = "ql"
    logging.info(" gtmktime: running with following parameters \n - scfile: %s\n - evfile: %s\n - outfile: %s\n - filter: %s", gt_apps.maketime['scfile'], gt_apps.maketime['evfile'], gt_apps.maketime['outfile'], gt_apps.maketime['filter'])
    try:
        gt_apps.maketime.run(print_command=False)
    except Exception as e:
        logging.error("Error during gtmktime: %s", e)
        return False
    return True

def ecliptic_cut(ecliptic_cut_dict, ft1_file, ft2_file, output_file) -> bool:
    '''
    Applies an ecliptic cut to the input FT1 file based on the input FT2 file.

    Parameters:
    ----------
        ecliptic_cut_dict: Dictionary containing the ecliptic cut criteria.
        ft1_file: Input FT1 file.
        ft2_file: Input FT2 file.
        output_file: Output FT1 file.
    '''
    with fits.open(ft1_file) as hdul:
        ft1_events = hdul['EVENTS'].data
        ft1_header_events = hdul['EVENTS'].header
        ft1_header_primary = hdul['PRIMARY'].header
        ft1_gti = hdul['GTI'].copy()

        evt_time = ft1_events['TIME']
        evt_ra = ft1_events['RA']
        evt_dec = ft1_events['DEC']

    with fits.open(ft2_file) as hdul2:
        sc_data = hdul2[1].data
        sc_time = sc_data['START']
        sc_ra_sun = sc_data['RA_SUN']
        sc_dec_sun = sc_data['DEC_SUN']

    interp_ra = interp1d(sc_time, sc_ra_sun, kind='linear', fill_value='extrapolate')
    interp_dec = interp1d(sc_time, sc_dec_sun, kind='linear', fill_value='extrapolate')

    sun_ra_evt = interp_ra(evt_time)
    sun_dec_evt = interp_dec(evt_time)

    evt_coords = SkyCoord(evt_ra * u.deg, evt_dec * u.deg, frame='icrs')
    sun_coords_evt = SkyCoord(sun_ra_evt * u.deg, sun_dec_evt * u.deg, frame='icrs')
    sep = evt_coords.separation(sun_coords_evt)
    degree_sep = float(ecliptic_cut_dict['eclipticradius']) if 'eclipticradius' in ecliptic_cut_dict else 0
    operator = ecliptic_cut_dict['eclipticoperator'] if 'eclipticoperator' in ecliptic_cut_dict else '>'
    if operator == 'lt':
        mask = sep < degree_sep * u.deg
    elif operator == 'gt':
        mask = sep > degree_sep * u.deg
    elif operator == 'lte':
        mask = sep <= degree_sep * u.deg
    elif operator == 'gte':
        mask = sep >= degree_sep * u.deg
    filtered_events = ft1_events[mask]

    primary_hdu = fits.PrimaryHDU(header=ft1_header_primary)
    events_hdu = fits.BinTableHDU(data=filtered_events, header=ft1_header_events, name='EVENTS')
    gti_hdu = ft1_gti
    hdul_out = fits.HDUList([primary_hdu, events_hdu, gti_hdu])
    logging.info(" ecliptic_cut: running with following parameters \n - ft1: %s\n - ft2: %s\n - radius: %s\n - operator: %s", ft1_file, ft2_file, degree_sep, operator)
    try:
        hdul_out.writeto(output_file, overwrite=True)
    except Exception as e:
        logging.error("Error during ecliptic_cut: %s", e)
        return False
    if operator in ['lt', 'lte']:
        sun_ra_mean, sun_dec_mean = np.mean(sun_ra_evt), np.mean(sun_dec_evt)
        sun_coords_mean = SkyCoord(sun_ra_mean * u.deg, sun_dec_mean * u.deg, frame='icrs')
        evt_coords = SkyCoord(filtered_events['RA'] * u.deg, filtered_events['DEC'] * u.deg, frame='icrs')
        sep_mean = evt_coords.separation(sun_coords_mean)
        degree_sep_mean = float(np.ceil(max(sep_mean.deg)))
        select_dict = {'ra': sun_ra_mean, 'dec': sun_dec_mean, 'radius': degree_sep_mean}
        gtselect(select_dict, output_file, f'select_{output_file}')
    return True

def plot_ft_data(ft_file_list, x, y, plot_filename):
    '''
    Plots the input FT data.

    Parameters:
    ----------
        ft_file_list: List of FT files.
        x: X-axis column name.
        y: Y-axis column name.
        plot_filename: Output plot filename.
    '''
    _, axs = plt.subplots(len(ft_file_list), 1, sharex=True, figsize=(12, 9))
    if len(ft_file_list) == 1:
        axs = [axs]
    for ax, ft_file in zip(axs, ft_file_list):
        with fits.open(ft_file) as hdul:
            ft_data = hdul[1].data
            ax.plot(ft_data[x], ft_data[y], ',')
            ax.set_xlabel(f'{x} [{hdul[1].columns[x].unit}]')
            ax.set_ylabel(f'{y} [{hdul[1].columns[x].unit}]')
            ax.set_title(ft_file)
            ax.set_xlim(0, 360)
            ax.set_ylim(-90, 90)
            ax.grid()
    plt.tight_layout()
    plt.savefig(plot_filename)
    plt.close()

def read_info_from_ft2(ft_file) -> dict:
    '''
    Reads the information from the input FT2 file.

    Parameters:
    ----------
        ft_file: Input FT2 file.

    Returns:
    -------
        Dictionary containing the information.
    '''
    EXCLUDED_COLUMNS = ['SC_VELOCITY', 'SC_POSITION']
    DEFAULT_COLUMNS = ['START', 'DATA_QUAL', 'ROCK_ANGLE', 'LAT_CONFIG']
    ACCEPTED_DTYPES = (np.float64, np.float32, np.uint8, np.int16, np.int32)
    with fits.open(ft_file) as file:
        data = file[1].data
        info_dict = {}
        for col in data.columns:
            col_name = col.name
            if col_name in EXCLUDED_COLUMNS:
                continue
            col_data = data[col_name]
            col_type = col.dtype
            if col_type in ACCEPTED_DTYPES:
                info_dict[col_name] = {
                    'max': col_data.max().item(),
                    'min': col_data.min().item(),
                    'dtype': str(col_type),
                    'unit': col.unit if col.unit else "N.A.",
                    'disabled': int(col_data.max() != col_data.min()),
                    'default': int(col_name in DEFAULT_COLUMNS)
                }
        return info_dict

def read_info_from_ft1(ft_file) -> dict:
    '''
    Mock function!
    Reads the information from the input FT1 file.

    Parameters:
    ----------
        ft_file: Input FT1 file.

    Returns:
    -------
        Dictionary containing the information.
    '''
    info_dict = {}
    info_dict['zenith_angle'] = {
        'name': 'Zenith Angle',
        'max': 180,
        'min': 0,
        'dtype': 'int16',
        'unit': 'deg',
        'disabled': 1,
        'default': 1
    }
    info_dict['energy'] = {
        'name': 'Energy',
        'max': 300000,
        'min': 30,
        'dtype': 'int16',
        'unit': 'MeV',
        'disabled': 1,
        'default': 1
    }
    return info_dict

@app.route('/')
def index():
    info_dict_ft1 = read_info_from_ft1(ft1_file)
    info_dict_ft2 = read_info_from_ft2(ft2_file)
    plot_url = None
    if os.path.exists("static/plot.png"):
        plot_url = url_for('static', filename='plot.png')
    return render_template('template.html',
                            info_dict_ft1=info_dict_ft1,
                            info_dict_ft2=info_dict_ft2,
                            ft1_file_name=ft1_file,
                            ft2_file_name=ft2_file,
                            plot_url=plot_url)

@app.route('/apply_filters', methods=['POST'])
def apply_filters():
    ft1_file = "lat_photon_weekly_w018_p305_v001.fits"
    ft2_file = "lat_spacecraft_weekly_w018_p310_v001.fits"
    select_dict = json.loads(request.form.get('select_dict', None))
    maketime_dict = json.loads(request.form.get('maketime_dict', None))
    ecliptic_cut_dict = json.loads(request.form.get('ecliptic_cut_dict', None))
    update_plot = request.form.get('update_plot', 'off') == 'on'
    select_output_file = f"select_{ft1_file}"
    mktime_output_file = f"mktime_{ft1_file}"
    ecliptic_cut_output_file = f"ecliptic_cut_{ft1_file}"
    plot_filename = "static/plot.png"
    if not select_dict and not maketime_dict and not ecliptic_cut_dict:
        return jsonify({"plot_url": None})
    plots_list = [ft1_file]
    if select_dict:
        if not gtselect(select_dict, ft1_file, select_output_file):
            return jsonify({"error": "Error during gtselect on FT1."})
        if update_plot:
            plots_list.append(select_output_file)
        ft1_file = select_output_file
    if maketime_dict:
        if not gtmktime(maketime_dict, ft1_file, ft2_file, mktime_output_file):
            return jsonify({"error": "Error during gtmktime."})
        if update_plot:
            plots_list.append(mktime_output_file)
        ft1_file = mktime_output_file
    if ecliptic_cut_dict:
        if not ecliptic_cut(ecliptic_cut_dict, ft1_file, ft2_file, ecliptic_cut_output_file):
            return jsonify({"error": "Error during ecliptic cut."})
        if update_plot:
            plots_list.append(ecliptic_cut_output_file)
    if update_plot:
        plot_ft_data(plots_list, x='RA', y='DEC', plot_filename=plot_filename)
    return jsonify({"plot_url": url_for('static', filename='plot.png')})

if __name__ == '__main__':
    DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(DIR)

    ft1_file = "lat_photon_weekly_w018_p305_v001.fits"
    ft2_file = "lat_spacecraft_weekly_w018_p310_v001.fits"
    app.run(debug=True)