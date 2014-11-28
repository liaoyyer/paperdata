#!/usr/bin/python
# -*- coding: utf-8 -*-
# Load data into MySQL table 

# import the MySQLdb and sys modules
import MySQLdb
import sys
import getpass
import time
import csv
import base64
import os

### Script to Backup paperdata database
### Finds time and date and writes table into .csv file

### Author: Immanuel Washington
### Date: 8-20-14
def paperbackup(time_date, usrnm, pswd):

	backup_dir = os.path.join('/data4/paper/paperdata_backup', time_date)
	if not os.path.isdir(backup_dir):
		os.mkdir(backup_dir)

	#Create separate files for each directory

	db1 = 'paperdata_backup_%s.csv'%(time_date)
	dbo1 = os.path.join(backup_dir,db1)
        print dbo1
        data_file1 = open(dbo1,'wb')
        wr1 = csv.writer(data_file1, dialect='excel')

	db2 = 'paperjunk_backup_%s.csv'%(time_date)
	dbo2 = os.path.join(backup_dir,db2)
        print dbo2
        data_file2 = open(dbo2,'wb')
        wr2 = csv.writer(data_file2, dialect='excel')

	db3 = 'paperrename_backup_%s.csv'%(time_date)
	dbo1 = os.path.join(backup_dir,db3)
        print dbo3
        data_file3 = open(dbo3,'wb')
        wr3 = csv.writer(data_file3, dialect='excel')

	db4 = 'paperfeed_backup_%s.csv'%(time_date)
	dbo1 = os.path.join(backup_dir,db4)
        print dbo4
        data_file4 = open(dbo4,'wb')
        wr4 = csv.writer(data_file4, dialect='excel')

	#Load data into named database and table
	# open a database connection
	connection = MySQLdb.connect (host = 'shredder', user = usrnm, passwd = pswd, db = 'paperdata', local_infile=True)

	# prepare a cursor object using cursor() method
	cursor = connection.cursor()

	# execute the SQL query using execute() method.
	cursor.execute('SELECT * FROM paperdata order by julian_date asc, raw_location asc, path asc')
	results = cursor.fetchall()

	for item in results:
		wr1.writerow(item)
	data_file1.close()

	cursor.execute('SELECT * FROM paperjunk order by junk_path asc, usb_number asc')
        results = cursor.fetchall()

        for item in results:
                wr2.writerow(item)
	data_file2.close()

	cursor.execute('SELECT * FROM paperrename order by julian_day asc, raw_path asc')
        results = cursor.fetchall()

        for item in results:
                wr3.writerow(item)
	data_file3.close()

	cursor.execute('SELECT * FROM paperfeed order by julian_day asc, raw_path asc')
        results = cursor.fetchall()

        for item in results:
                wr4.writerow(item)
	data_file4.close()

	print time_date
	print 'Table data backup saved'

	# Close the cursor object
	cursor.close()
	connection.close()

def paperbackup():

if __name__ == '__main__':
	usrnm = 'immwa'
	pswd = base64.b64decode('aW1td2EzOTc4')

	time_date = time.strftime("%d-%m-%Y_%H:%M:%S")

	paperbackup(time_date, usrnm, pswd)