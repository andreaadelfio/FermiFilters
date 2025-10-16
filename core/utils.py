import os
import matplotlib
import matplotlib.pyplot as plt
from astropy.io import fits
import numpy as np
import requests
from .config import TMP_DIR
import logging
import xml.etree.ElementTree as ET
import re

class Plotter:
    matplotlib.use('Agg')

    def plot_ft_data(self, ft_file_list, x, y, plot_filename):
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
        for i, (ax, ft_file) in enumerate(zip(axs, ft_file_list)):
            with fits.open(ft_file) as hdul:
                ft_data = hdul[1].data
                ax.plot(ft_data[x], ft_data[y], ',')
                if i == len(ft_file_list) - 1:
                    ax.set_xlabel(f'{x} [{hdul[1].columns[x].unit}]')
                ax.set_ylabel(f'{y} [{hdul[1].columns[x].unit}]')
                ax.set_title(os.path.basename(ft_file))
                ax.set_xlim(0, 360)
                ax.set_ylim(-90, 90)
                ax.grid()
        plt.tight_layout()
        plt.savefig(plot_filename)
        plt.close()


class FitsReader:

    def read_info_from_ft2(self, ft_file) -> dict:
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

    def read_info_from_ft1(self, ft_file) -> dict:
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


class FilesHandler:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def download_from_url(self, files_dict):
        '''
        Downloads a file from the given URL.

        Parameters:
        ----------
            files_dict: dict containing URLs of the files to download.

        Returns:
        -------
            True if the download was successful, False otherwise.
        '''
        files_list = {'photon': [], 'spacecraft': []}
        for week, week_dict in files_dict.items():
            for file_name, url in week_dict.items():
                try:
                    output_file_path = os.path.join(TMP_DIR, file_name)
                    self.logger.info(f" Starting download from {url} to {output_file_path}")
                    response = requests.get(url)
                    response.raise_for_status()
                    with open(output_file_path, 'wb') as f:
                        f.write(response.content)
                    self.logger.info(f" Download completed: {output_file_path}")
                    ft_type = 'photon' if 'photon' in file_name else 'spacecraft'
                    files_list[ft_type].append(output_file_path)
                except Exception as e:
                    self.logger.error(f" Error downloading file from {url}: {e}")
        return files_list
        
if __name__ == "__main__":
    files_dict = {'fermi_photon__lat_photon_weekly_w009_p305_v001.fits':
        "https://minio.131.154.99.174.myip.cloud.infn.it/spoke3/spoke3/fermi_photon__lat_photon_weekly_w009_p305_v001__0?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=icsc%2F20250611%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20250611T141520Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=8228d184dbe91fbf7d23e988b7008e6b8f785a26ad9b4b6b7b1fa32783422a15"
    }
    files_list = []
    for file_name, url in files_dict.items():
        output_file_path = FilesHandler().download_from_url(url, file_name)
        files_list.append(output_file_path)
    print(f"Downloaded files: {files_list}")    

class VOHandler:
    def get_files_dict(self, vo_text):
        '''
        Converts the input vo_file to a format suitable for downloading.

        Parameters:
        ----------
            vo_file: vo xml containing the files to download.

        Returns:
        -------
            Dictionary containing the files to download.
        '''

        vo_xml = ET.fromstring(vo_text)
        ns = {'vot': 'http://www.ivoa.net/xml/VOTable/v1.3'}

        files_dict = {}

        for table in vo_xml.findall('.//vot:TABLE', ns):
            fields = [field.attrib['name'] for field in table.findall('vot:FIELD', ns)]
            did_idx = fields.index('did_name')
            url_idx = fields.index('access_url')
            week_idx = fields.index('week')

            for tr in table.findall('.//vot:TR', ns):
                tds = tr.findall('vot:TD', ns)
                did_name = tds[did_idx].text
                access_url = tds[url_idx].text
                week = tds[week_idx].text
                if not did_name.endswith('.fits'):
                    file_name = did_name + '.fits'

                if week not in files_dict:
                    files_dict[week] = {}
                files_dict[week][file_name] = access_url
        print(files_dict)
        return files_dict