import sys
from typing import List, Optional
import gmplot

import hts
from pcr_fields import PacketMetadata, PacketRecipe

API_KEY = 'AIzaSyCbL_W8yie7RKhlJXJJQT2LiI6jO0rReYU'

class HtsPlotPoint():
    marker_number: int
    '''Point number for tracking purposes'''
    latitude: int
    '''Point latitude in millionths of degrees'''
    longitude: int
    '''Point longitude in millionths of degrees'''
    popup_text: str
    '''Text in marker popup'''

    def __init__(self, marker_number: int, latitude: int, longitude: int) -> None:
        self.marker_number = marker_number
        self.latitude = latitude
        self.longitude = longitude
        self.popup_text = ''

    def add_packet_text(self, header: str, text: str):
        def htmlify(text: str) -> str:
            return text.replace('\r', '').replace('\n', '<br />')
        self.popup_text += f'<h3>{htmlify(header)}</h3><tt>{htmlify(text)}</tt>'

    def add_to_plot(self, map: gmplot.GoogleMapPlotter):
        map.marker(
            self.latitude / 1000000,
            self.longitude / 1000000,
            color='red',
            title=f'Marker #{self.marker_number}',
            info_window=self.popup_text
        )



class HtsPlotter():
    '''Class to handle Harp Data plotting'''
    config: List[PacketRecipe]

    def __init__(self, paramset_file: str):
        self.config, _ = hts.load_config(paramset_file)

    def plot_csv_file(self, csv_file: str, out_html: str) -> None:
        '''Plot a CSV file, placing the resulting HTML in the specified location'''

        map_obj: Optional[gmplot.GoogleMapPlotter] = None
        cur_pnt: Optional[HtsPlotPoint] = None
        marker_num = 1

        f = open(csv_file, 'r')
        # read past CSV header
        while True:
            line = f.readline()
            if line.startswith('timestamp,ip,data') or line == '':
                break

        while True:
            line = f.readline()
            if line == '':
                break
            line = line.strip()

            cols = line.split(',')
            if len(cols) < 3:
                continue

            try:
                data = bytes.fromhex(cols[2])
            except:
                continue

            pcr: Optional[PacketRecipe] = None
            for cfg in self.config:
                if cfg.packet_is_this(data):
                    pcr = cfg
                    break

            if pcr is None:
                continue

            packet_info = pcr.validate_packet(data, print_me=False)
            if (
                not packet_info.validated or
                packet_info.latitude is None or
                packet_info.longitude is None or
                packet_info.latitude == 0 or
                packet_info.longitude == 0
            ):
                continue

            if (
                cur_pnt is None or
                packet_info.latitude != cur_pnt.latitude or
                packet_info.longitude != cur_pnt.longitude
            ):
                prev_pnt = cur_pnt
                cur_pnt = HtsPlotPoint(marker_num, packet_info.latitude, packet_info.longitude)
                marker_num += 1

                if map_obj is None:
                    map_obj = gmplot.GoogleMapPlotter(
                        cur_pnt.latitude / 1000000,
                        cur_pnt.longitude / 1000000,
                        zoom=15,
                        apikey=API_KEY
                    )

                # we want to group identical GPS coordinates together, so we only
                # plot when we create a new point
                if prev_pnt is not None:
                    prev_pnt.add_to_plot(map_obj)

            cur_pnt.add_packet_text(
                f'Packet {packet_info.packet_id}, Reason {packet_info.reason_code}',
                packet_info.human_readable
            )

        # get last point and output
        if cur_pnt is not None:
            cur_pnt.add_to_plot(map_obj)
            map_obj.draw(out_html)



def main():
    if len(sys.argv) != 4:
        print('Usage: hts_plotter.py <paramset> <CSV file> <HTML output>')
        sys.exit(0)

    plotter = HtsPlotter(sys.argv[1])
    plotter.plot_csv_file(sys.argv[2], sys.argv[3])

if __name__ == '__main__':
    main()
