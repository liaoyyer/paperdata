#!/usr/bin/python
# -*- coding: utf-8 -*-
# Load data into MySQL table 

# import the MySQLdb and sys modules
import MySQLdb
import sys
import getpass
import os
import csv
import glob
import socket
import time
import subprocess
import smtplib
import rename_uv
import load_paperrename
import load_paperfeed

### Script to load paperfeed with files from the paperrename table
### Checks /data4 for space, moves entire days of data, renames them the correct names, then loads into paperfeed

### Author: Immanuel Washington
### Date: 11-23-14


def calculate_free_space(dir):
	#Calculates the free space left on input dir
	folio = subprocess.check_output(['df', dir], shell=True)
	#/data4 should be filesystem
	#Amount of available bytes should be free_space

	for output in folio.split('\n'):
	        filesystem = output.split(' ')[-1]
	        if filesystem == '/data4':
			free_space = int(output.split(' ')[-4])
	return free_space

def move_files(infile_list, outfile, move_data, usrnm, pswd):
	host = socket.gethostname()

        #Directory of the infiles
        infile_dir = infile_list[0].split('z')[0]

        #create file to log movement data       
        dbo = os.path.join('/data4/paper/file_renaming_test', move_data)
        dbr = open(dbo,'wb')
        dbr.close()

        o_dict = {}
        for file in infile_list:
                zen = file.split('/')[-1]
                out = host + ':' + os.path.join(outfile,zen)
                o_dict.update({file:out})

        #Load data into named database and table
        connection = MySQLdb.connect (host = 'shredder', user = usrnm, passwd = pswd, db = 'paperdata', local_infile=True)
        cursor = connection.cursor()

        #Load into db
        for infile in infile_list:
                if infile.split('.')[-1] != 'uv':
                        print 'Invalid file type'
                        sys.exit()

                outfile = o_dict[infile]

                #Opens file to append to
                dbr = open(dbo, 'a')
                wr = csv.writer(dbr, dialect='excel')

                #"moves" file
                try:
			#scp infile, outfile
			inner = 'obs@' + infile
			os.popen('''scp -r %s %s''' %(inner, outfile))
                        wr.writerow([infile,outfile])
                        print infile, outfile
                        dbr.close()
                except:
                        dbr.close()
                        continue
                # execute the SQL query using execute() method, updates new location
                infile_path = infile
                outfile_path = o_dict[infile]
                cursor.execute('''UPDATE paperjunk set folio_path = '%s' where junk_path = '%s' '''%(outfile_path, infile_path))

        print 'File(s) moved and updated'

        #Close database and save changes
        cursor.close()
        connection.commit()
        connection.close()

        return o_dict

def check_paperjunk(usb):
	#Load data into named database and table
        connection = MySQLdb.connect (host = 'shredder', user = usrnm, passwd = pswd, db = 'paperdata', local_infile=True)
        cursor = connection.cursor()

	cursor.execute('''SELECT junk_path from paperjunk where usb_number = %d and folio_path == 'NULL' ''' %(usb))
	results = cursor.fetchall()

	junk_list = []

	for item in results:
		junk_list.append(item[0])

	return junk_list

def paperjunk(auto):
	#Create output file
        time_date = time.strftime("%d-%m-%Y_%H:%M:%S")
        move_data = 'moved_data_%s.csv'%(time_date)

        #Credentials
	if auto != 'y':
        	usrnm = raw_input('Username: ')
        	pswd = getpass.getpass('Password: ')

	else:
		usrnm = 'immwa'
		pswd = 'immwa3978'

        #Files to temporarily store information about renamed files
        dbo = '/data2/home/immwa/scripts/paper_output/paperjunk_out.csv'

        outfile = '/data4/paper/file_renaming_test'

        #Checks all filesystems
        dir = '/*'
        free_space = calculate_free_space(dir)

        #Amount of free space needed -- ~4.1TB
        required_space = 4402341478

        #Move if there is enough free space
        if free_space > required_space:
                #Try to find usb to move
                for usb in range(8):
                        infile_list = check_paperjunk(usb)
                        if len(infile_list) > 0:
                                break
                #COPY FILES FROM 1 USB INTO FOLIO
                outfile_dict move_files(infile_list, outfile, move_data, usrnm, pswd)

	return None

if __name__ == '__main__':
	auto = 'n'
	paperjunk(auto)
