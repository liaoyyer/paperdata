#!/usr/bin/python
# -*- coding: utf-8 -*-
# Add files to paper

from __future__ import print_function
import sys
import os
from paper.data import dbi as pdbi
import paper.convert as convert
import aipy as A

### Script to calculate uv data on any/other hosts
### output uv_data in csv format: 

### Author: Immanuel Washington
### Date: 5-06-15
def five_round(num):
	'''
	rounds number to five significant figures

	Args:
		num (float): number

	Returns:
		float(5): number
	'''
	return round(num, 5)

def jdpol2obsnum(jd, pol, djd):
	'''
	calculates unique observation number for observations

	Args:
		jd (float): julian date float
		pol (str): polarization
		length (float): length of obs in fraction of julian date

	Returns:
		int: a unique integer index for observation
	'''
	dublinjd = jd - 2415020  #use Dublin Julian Date
	obsint = int(dublinjd/djd)  #divide up by length of obs
	polnum = A.miriad.str2pol[pol]+10
	assert(obsint < 2**31)

	return int(obsint + polnum*(2**32))

def get_lst(julian_date):
	'''
	calculates local sidereal hours for any julian date

	Args:
		julian_date (float): julian date

	Returns:
		float(1): lst hours rounded to one decimal place
	'''
	gmst = convert.juliandate_to_gmst(julian_date)
	lst = convert.gmst_to_lst(gmst, longitude=25)

	return round(lst, 1)

def julian_era(julian_date):
	'''
	indicates julian day and set of data

	Args:
		julian_date (float): julian date
	Returns:
		tuple:
			int: era of julian date
			int: julian day
	'''
	if julian_date < 2456100:
		era = 32
	elif julian_date < 2456400:
		era = 64
	else:
		era = 128

	julian_day = int(julian_date)

	return era, julian_day

def is_edge(prev_obs, next_obs):
	'''
	checks if observation is on the edge of each day's observation cycle

	Args:
		prev_obs (database object): previous observation
		next_obs (database object): next observation

	Returns:
		bool: on the edge of a julian day
	'''
	if (prev_obs, next_obs) == (None, None):
		edge = None
	else:
		edge = (None in (prev_obs, next_obs))

	return edge

def obs_pn(obsnum, s):
	'''
	gets the previous and next observations for any obsnum

	Args:
		obsnum (int): observation number
		s (session object): session object

	Returns:
		tuple:
			object: previous observation object if available, None otherwise
			object: next observation object if available, None otherwise
	'''
	table = getattr(pdbi, 'Observation')
	PREV_OBS = s.query(table).filter(getattr(table, 'obsnum') == obsnum - 1).one()
	if PREV_OBS is not None:
		prev_obs = getattr(PREV_OBS, 'obsnum')
	else:
		prev_obs = None
	NEXT_OBS = s.query(table).filter(getattr(table, 'obsnum') == obsnum + 1).one()
	if NEXT_OBS is not None:
		next_obs = getattr(NEXT_OBS, 'obsnum')
	else:
		next_obs = None

	return prev_obs, next_obs

def obs_edge(obsnum, sess=None):
	'''
	checks for previous and next observations, and if obsnum is on edge of julain day

	Args:
		obsnum (int): observation number
		sess (session object): session object if available
	Returns:
		tuple:
			object: previous observation object if available, None otherwise
			object: next observation object if available, None otherwise
			bool: on the edge of julian day
	'''
	if obsnum == None:
		prev_obs = None
		next_obs = None
		edge = None
	else:
		if sess is None:
			dbi = pdbi.DataBaseInterface()
			with dbi.session_scope() as s:
				prev_obs, next_obs = obs_pn(obsnum, s)
		else:
			prev_obs, next_obs = obs_pn(obsnum, s)
		edge = is_edge(prev_obs, next_obs)

	return prev_obs, next_obs, edge

def calc_times(uv):
	'''
	takes in uv file and calculates time based information

	Args:
		uv (file object): uv file object

	Returns:
		tuple:
			float(5): time start
			float(5): time end
			float(5): delta time
			float(5): length of uv file object
	'''
	time_start = 0
	time_end = 0
	n_times = 0
	c_time = 0

	try:
		for (uvw, t, (i,j)),d in uv.all():
			if time_start == 0 or t < time_start:
				time_start = t
			if time_end == 0 or t > time_end:
				time_end = t
			if c_time != t:
				c_time = t
				n_times += 1
	except:
		return None

	if n_times > 1:
		delta_time = -(time_start - time_end)/(n_times - 1)
	else:
		delta_time = -(time_start - time_end)/(n_times)

		length = five_round(n_times * delta_time)
		time_start = five_round(time_start)
		time_end = five_round(time_end)
		delta_time = five_round(delta_time)

	return time_start, time_end, delta_time, length

def calc_uv_data(host, full_path, mode=None):
	'''
	takes in uv* files and pulls data about observation

	Args:
		host (str): host of system
		full_path (str): full_path of uv* file
		mode (Optional[str]): mode of data to get time from --defaults to None

	Returns:
		tuple:
			float(5): time start
			float(5): time end
			float(5): delta time
			float(5): julian date
			str: polarization
			float(5): length
			int: obsnum of uv file object
	'''
	filetype = full_path.split('.')[-1]
	#allows uv access
	if filetype in ('uv', 'uvcRRE'):
		try:
			uv = A.miriad.UV(full_path)
		except:
			return None

		#indicates julian date
		julian_date = round(uv['time'], 5)

		#assign letters to each polarization
		if uv['npol'] == 1:
			polarization = pol_dict[uv['pol']]
		elif uv['npol'] == 4:
			polarization = 'all'

		time_start, time_end, delta_time, length = calc_times(uv)
		if mode == 'time':
			return time_start, time_end, delta_time, length

		#gives each file unique id
		if length > 0:
			obsnum = jdpol2obsnum(julian_date, polarization, length)
		else:
			obsnum = None

		return time_start, time_end, delta_time, julian_date, polarization, length, obsnum
	else:
		return None

if __name__ == '__main__':
	input_host = sys.argv[1]
	input_path = sys.argv[2]
	mode = None
	if len(sys.argv) == 4:
		mode = sys.argv[3]

	uv_data = calc_uv_data(input_host, input_path, mode)
	if uv_data is None:
		sys.exit()
	output_string = ','.join(uv_data)
	print(output_string)
