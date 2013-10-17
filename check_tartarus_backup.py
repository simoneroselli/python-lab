#!/usr/bin/env python
#
# Check remote FTP backup
#
# Author ZMo <simoneroselli78@gmail.com>
#
# Nagios plugin for Tartarus. Check if the remote FTP
# backup is older than a given time amount

import sys, time, datetime, os.path
import paramiko as p

# Backup configuration file
backup_cfg_file = '/etc/tartarus/generic.inc'

if not os.path.exists(backup_cfg_file):
    print "REMOTE BACKUP ERROR: Conf file " + backup_cfg_file + " not found!"
    sys.exit(1)

# Import variables from the backup conf file
execfile(backup_cfg_file, globals())

# SFTP configuration
port = 22
try:
    transport = p.Transport((STORAGE_FTP_SERVER, port))
except p.SSHException:
    print "REMOTE BACKUP ERROR: Broken connection with SFTP server"
    sys.exit(1)
transport.connect(username = STORAGE_FTP_USER, password = STORAGE_FTP_PASSWORD)
sftp = p.SFTPClient.from_transport(transport)

# Age check configuration (86400 = 1 day, 604800 = 1 week); basically
# this time is calculated along MAX_AGE_IN_DAYS in the
# '/etc/tartarus/resource.conf' value
ftp_file_list = sftp.listdir(path='.')
max_old_secs = 604800
today_secs = int(time.time())

# Convert seconds amount in days for the output
old = (max_old_secs / 86400)

# Age check
def fileIsOld(max_old_secs, today_secs, file_age_secs):
    secs_diff = (today_secs - file_age_secs)
    if secs_diff > max_old_secs:
        return True

# Main
for f in ftp_file_list:
	if f.startswith('.'):
		continue
	else:
	    file_age_secs = sftp.stat(f).st_mtime
	    file_age_date = datetime.datetime.fromtimestamp(file_age_secs).strftime('%d/%m/%Y')
	    age_check = fileIsOld(max_old_secs, today_secs, file_age_secs)
	
  	    if age_check == True:
	        print "REMOTE BACKUP OUTDATED - File " + '"' + f + '"' + " is older than " + old + "days" + ' (' + file_age_date + ')'
	        sys.exit(1)
	    else:
            print "REMOTE BACKUP AGE OK - " + "Last check: " + datetime.datetime.fromtimestamp(today_secs).strftime('%d/%m/%Y')
	        sys.exit(0)

sftp.close()
transport.close()   
