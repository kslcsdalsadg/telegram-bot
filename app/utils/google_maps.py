from enum import Enum

import subprocess
import re

class GetLocationResultType(Enum):
    NO_ERROR = 0,
    CANT_DECODE_URL = 1,
    UNSUPPORTED_URL_FORMAT = 2

class GoogleMapsUtils():
    @staticmethod
    def get_location(url):
        if url.startswith('https://maps.app.goo.gl/'):
            stdout, error = subprocess.Popen([ 'curl', '-Ls', '-o', '/dev/null', '-w', '%{url_effective}', url ], stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()
            if stdout is None:
                return GetLocationResultType.CANT_DECODE_URL, None
            else:
                url = stdout.decode()
        if url.startswith('https://www.google.com/maps/dir//'):
            match = re.search("\/dir\/\/[^,]+,[^\/]+/", url)
            if match is not None:
                location = match.group(0)
                return GetLocationResultType.NO_ERROR, location[6:len(location) - 1]
        if url.startswith('https://www.google.com/maps/'):
            match = re.search("@[^,]+,[^,]+,", url)
            if match is not None:
                location = match.group(0)
                return GetLocationResultType.NO_ERROR, location[1:len(location) - 1]
            match = re.search("ll=[^,]+,[^,]+,", url)
            if match is not None:
                location = match.group(0)
                return GetLocationResultType.NO_ERROR, location[3:len(location) - 1]
        return GetLocationResultType.UNSUPPORTED_URL_FORMAT, None

