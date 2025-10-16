import os
import subprocess
import logging
from astropy.io import fits
from astropy.coordinates import SkyCoord
from scipy.interpolate import interp1d
import astropy.units as u
import numpy as np
import gt_apps
from astropy.table import Table, vstack


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')


class FiltersEngine:

    def ft2_merge(self, ft2_file_list, output_file):
        """
        Merges multiple FT2 (spacecraft) files into a single sorted FT2 file using Astropy.

        Parameters
        ----------
        ft2_file_list : list of str
            List of paths to FT2 files to be merged.
        output_file : str
            Path to the output merged FT2 file.

        Returns
        -------
        bool
            True if the merge and sort succeeded, False otherwise.
        """
        try:
            all_tables = []

            for ft2_file in ft2_file_list:
                with fits.open(ft2_file) as hdul:
                    sc_data = Table(hdul['SC_DATA'].data)
                    all_tables.append(sc_data)

            # Merge and sort the tables
            merged_table = vstack(all_tables)
            merged_table.sort('START')

            # Create output HDU list
            primary_hdu = fits.PrimaryHDU()
            sc_data_hdu = fits.BinTableHDU(merged_table, name='SC_DATA')
            hdul_out = fits.HDUList([primary_hdu, sc_data_hdu])

            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            hdul_out.writeto(output_file, overwrite=True)

            logging.info("Successfully merged FT2 files into %s", output_file)
            return True

        except Exception as e:
            logging.error("Error during pure Python spacecraft merge: %s", e)
            return False

    def gtmerge(self, ft1_file_list, output_file) -> bool:
        '''
        Merges multiple FT1 files into a single FT1 file.

        Parameters:
        ----------
            ft1_file_list: List of FT1 files to be merged.
            output_file: Output FT1 file.
        
        Returns:
        -------
            True if the merge was successful, False otherwise.
        '''
        with open('static/andrea-adelfio_tmp/ft1_to_be_merged.txt', 'w') as f:
            for ft1_file in ft1_file_list:
                f.write(ft1_file + '\n')
        logging.info(" gtmerge: %s", ft1_file_list)
        gt_apps.filter['infile'] = 'static/andrea-adelfio_tmp/ft1_to_be_merged.txt'
        gt_apps.filter['evclass'] = 128
        gt_apps.filter['evtable'] = "EVENTS"
        gt_apps.filter['evtype'] = 3
        gt_apps.filter['outfile'] = output_file
        gt_apps.filter['zmax'] = '180'
        gt_apps.filter['zmin'] = '0'
        gt_apps.filter['emin'] = '30'
        gt_apps.filter['emax'] = '300000'
        gt_apps.filter['ra'] = '0'
        gt_apps.filter['dec'] = '0'
        gt_apps.filter['rad'] = '180'
        logging.info(" gtmerge: running with following parameters \n - infile: %s\n - outfile: %s", gt_apps.filter['infile'], gt_apps.filter['outfile'])
        try:
            gt_apps.filter.run(print_command=False)
            os.remove('gtselect.par')
        except Exception as e:
            logging.error("Error during gtmerge: %s", e)
            return False
        return True

    def gtselect(self, select_dict, ft1_file, output_file) -> bool:
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
            os.remove('gtselect.par')
        except Exception as e:
            logging.error("Error during gtselect: %s", e)
            return False
        return True

    def gtmktime(self, maketime_dict, ft1_file, ft2_file, output_file) -> bool:
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
            os.remove('gtmktime.par')
        except Exception as e:
            logging.error("Error during gtmktime: %s", e)
            return False
        return True

    def ecliptic_cut(self, ecliptic_cut_dict, ft1_file, ft2_file, output_file) -> bool:
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
            self.gtselect(select_dict, output_file, f'select_{output_file}')
        return True
    
if __name__ == "__main__":
    from utils import FilesHandler
    
    files_dict = {'lat_photon_weekly_w009_p305_v001.fits':
        "https://heasarc.gsfc.nasa.gov/FTP/fermi/data/lat/weekly/photon/lat_photon_weekly_w009_p305_v001.fits",
            'lat_photon_weekly_w010_p305_v001.fits':
        'https://heasarc.gsfc.nasa.gov/FTP/fermi/data/lat/weekly/photon/lat_photon_weekly_w010_p305_v001.fits'
    }
    files_list = []
    for file_name, url in files_dict.items():
        output_file_path = FilesHandler().download_from_url(url, file_name)
        if not output_file_path:
            logging.error("Failed to download file from %s", url)
        else:
            files_list.append(output_file_path)
            logging.info("File downloaded successfully: %s", output_file_path)
    # Example usage
    engine = FiltersEngine()
    ft1_files = ['ft1_file1.fits', 'ft1_file2.fits']
    output_file = 'merged_ft1.fits'
    if engine.gtmerge(ft1_files, output_file):
        logging.info("FT1 files merged successfully.")
    else:
        logging.error("Failed to merge FT1 files.")