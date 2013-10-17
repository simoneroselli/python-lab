#!/usr/bin/env python
# ========================================================================
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Llog - Lookup Logs, parse the access log apache file and lookup for the ip
# addresses
#
# Author ZMo <simoneroselli78@gmail.com>

import os, GeoIP
import urllib2, sys, gzip

geoDatUrl = 'http://lurch.develer.net/GeoLiteCity.dat.gz'
geoDatGzFile = '/tmp/GeoLiteCity.dat.gz'
geoDatFile = '/tmp/GeoLiteCity.dat'

BLOCK_SIZE = 8192

class Who(object):
    def __init__(self, ip=None, date=None, request=None):
        self.ip = ip
        self.date = date
        self.request = request

    def __str__(self):
        return "%s, %s, %s" % (self.ip, self.date, self.request)

    @staticmethod
    def accessLogParser(access_log):
        """ Parse the access log file and retrieve ip, date and
        the requested page """
        intruders_list = []
        
        with open(access_log, "r") as f:
            intruder = Who()
            while True:
                line = f.readline()
                if not line:
                    break
                if len(line) != 0:
                    intruder.ip = line.split()[0] 
                    if intruder.ip.startswith("127.0.") or \
                            intruder.ip == "localhost":
                       continue

                try:
                    intruder.date = line.split()[3].strip("[") 
                    intruder.request = line.split()[6]
                except IndexError:
                    print "Access log format is not valid"
                    print "Please provide a correct access file (ie: IP / DATE / REQUEST)"
                    exit()

                yield intruder
        
    @staticmethod
    def retIntruders(logFile):
        """ Print each set of information and lookup on ip addresses for
        Country, City, Time Zone """
        for i in Who.accessLogParser(logFile):
            print "IP Address:", i.ip
            print "Date:      ", i.date
            print "Request:   ", i.request

            # Special lookups by GeoIP
            g = GeoIP.open(geoDatFile, GeoIP.GEOIP_STANDARD)
            geoip = g.record_by_addr(i.ip)
            if geoip != None:
                print "Country:   ", geoip['country_name']
                print "City:      ", geoip['city']
                print "Region     ", geoip['region']
                print "Time Zone: ", geoip['time_zone']
                print ""
            else:
                # Warn if you can't perform the lookup here
                print "Warn:       cannot perform the Geo lookup!"
                print ""

def ungzip(datgzip, datfile):
    with gzip.open(datgzip, 'rb') as z:
        z_content = z.read()
    with open(datfile, 'w') as f:
        f.write(z_content)
    os.unlink(datgzip)

def getCityDat(url, datfile):
    """ Download GeoIP .dat file if not present """
    site = urllib2.urlopen(url)
    meta = site.info()
    length = meta.getheaders("Content-Length")[0]
    hum_length = int(length) / 1024 / 1024
    with open(datfile, 'wb') as f:
        dwnl = 0
        home = os.getcwd()
        os.chdir('/tmp/')
        while True:
            cnk = site.read(BLOCK_SIZE)
            if len(cnk) == 0:
                break
            dwnl += len(cnk)
            f.write(cnk)
            if dwnl >= (1024**2):
                sys.stdout.write('\b' * 45)
                sys.stdout.write('Downloading GeoCity dat file (%s of %s Mib)' % (dwnl / 1024**2, hum_length))
        f.flush()
        sys.stdout.write('\n')
        os.chdir(home)


if __name__ == '__main__':
    if len(sys.argv)!=2:
        print "Usage: llog <access_file>"
        exit()

    # Ensure you have the "dat" file
    if not os.path.isfile(geoDatFile):
        getCityDat(geoDatUrl, geoDatGzFile)
        ungzip(geoDatGzFile, geoDatFile)
    
    # Parse access_log file
    Who.retIntruders(sys.argv[1])
