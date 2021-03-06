from flask import render_template, request, g, make_response, jsonify
import os
import re
from paper.site.flask_app import search_app as app, search_db as db
from paper.site.search import models
from paper.site import db_utils

@app.route('/get_tables', methods = ['POST'])
def get_tables():
	'''
	get all tables
	'''
	if g.user is not None and g.user.is_authenticated():
		hostname = request.form['hostname']
		database = request.form['database']

		table_tuples = db_utils.get_table_names(database)

		return render_template('table_list.html', table_tuples=table_tuples)
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/get_columns', methods = ['POST'])
def get_columns():
	'''
	get all columns
	'''
	if g.user is not None and g.user.is_authenticated():
		hostname = request.form['hostname']
		database = request.form['database']
		table = request.form['table']

		column_tuples = db_utils.get_column_names(database, table)

		return render_template('column_list.html', column_tuples=column_tuples)
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/get_users_data_sources')
def get_users_data_sources():
	'''
	get all of current user's data sources

	Returns:
		html: data sources
	'''
	if g.user is not None and g.user.is_authenticated():
		active_data_sources = g.user.active_data_sources
		subscribed_but_inactive_data_sources =\
			list(set(g.user.subscribed_data_sources) - set(active_data_sources))

		return render_template('data_sources.html',
								subscribed_but_inactive_data_sources=subscribed_but_inactive_data_sources,
								active_data_sources=g.user.active_data_sources)
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/get_unsubscribed_data_sources')
def get_unsubscribed_data_sources():
	'''
	get all data sources user is not subscribed to

	Returns:
		html: unsubscribed data sources
	'''
	if g.user is not None and g.user.is_authenticated():
		all_data_sources = db_utils.query(database='search', table='graph_data_source')

		subscribed_data_sources = g.user.subscribed_data_sources

		unsubscribed_data_sources = list(set(all_data_sources) -\
			set(subscribed_data_sources))

		return render_template('unsubscribed_data_sources.html',
			unsubscribed_data_sources=unsubscribed_data_sources)
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/update_active_data_sources', methods = ['POST'])
def update_active_data_sources():
	'''
	update user by adding/removing data sources
	'''
	if g.user is not None and g.user.is_authenticated():
		request_content = request.get_json()
		new_active_data_sources_names = request_content['activeDataSources']

		new_active_data_sources = db_utils.query(database='search', table='graph_data_source',
																field_tuples=(('name', 'in', new_active_data_sources_names),))

		current_active_data_sources = g.user.active_data_sources
		active_to_remove = list(set(current_active_data_sources) -\
			set(new_active_data_sources))
		active_to_add = list(set(new_active_data_sources) -\
			set(current_active_data_sources))

		for active_data_source in active_to_remove:
			g.user.active_data_sources.remove(active_data_source)

		for active_data_source in active_to_add:
			g.user.active_data_sources.append(active_data_source)

		db.session.add(g.user)
		db.session.commit()
		return 'Success'
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/subscribe_to_data_source', methods = ['POST'])
def subscribe_to_data_source():
	'''
	add data source to user
	'''
	if g.user is not None and g.user.is_authenticated():
		data_source_name = request.form['dataSource']

		data_source = db_utils.query(database='search', table='graph_data_source', field_tuples=(('name', '==', data_source_name),))[0]

		g.user.subscribed_data_sources.append(data_source)
		db.session.add(g.user)
		db.session.commit()
		return 'Success'
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/unsubscribe_from_data_source', methods = ['POST'])
def unsubscribe_from_data_source():
	'''
	remove data source from user
	'''
	if g.user is not None and g.user.is_authenticated():
		data_source_name = request.form['dataSource']

		data_source = db_utils.query(database='search', table='graph_data_source', field_tuples=(('name', '==', data_source_name),))[0]

		g.user.subscribed_data_sources.remove(data_source)
		try:
			g.user.active_data_sources.remove(data_source)
		except ValueError as e:
			#The user didn't have this as an active data source.
			print('Tried to remove an inactive data source')
		db.session.add(g.user)
		db.session.commit()
		return 'Success'
	else:
		return make_response('You must be logged in to use this feature.', 401)

@app.route('/get_graph_types')
def get_graph_types():
	'''
	get all graph types
	'''
	graph_types = db_utils.query(database='search', table='graph_type', field_tuples=(('name', '!=', 'Obs_File'),))

	return render_template('graph_type_list.html', graph_types=graph_types)

@app.route('/create_data_source', methods = ['POST'])
def create_data_source():
	'''
	create new data source and add to user
	'''
	if g.user is not None and g.user.is_authenticated():
		request_content = request.get_json()

		graph_type = request_content['graph_type']
		host = request_content['host']
		database = request_content['database']
		table = request_content['table']
		columns = request_content['columns']
		obs_column = request_content['obs_column']
		data_source_name = request_content['data_source_name']
		include_width_slider = request_content['include_width_slider']

		if not graph_type or not host or not database or not table or not columns\
			or not obs_column or not data_source_name:
			return jsonify(error=True, message='You need to fill out all the fields.')

		data_source_name = data_source_name.strip()
		if len(data_source_name) == 0:
			return jsonify(error=True, message='Name cannot be empty.')

		# The data source name (with spaces replaced by ಠ_ಠ) is used as
		# a JavaScript variable name and as an ID in HTML, so it needs
		# to obey the rules for those identifiers, minus a few
		# options such as $ since they would need to be escaped in
		# the HTML IDs.
		if not re.match(r'^[a-zA-Z_][0-9a-zA-Z_ ]*$', data_source_name):
			return jsonify(error=True, message='''Your data source name must
				start with a letter or _ that is followed by digits,
				letters, _, or spaces.''')

		#Is the data source name unique?
		data_source = db_utils.query(database='search', table='graph_data_source', field_tuples=(('name', '==', data_source_name),))[0]
		if data_source is not None:
			return jsonify(error=True, message='The data source name must be unique.')

		table_tuples = db_utils.get_table_names(database)
		if table not in table_tuples:
			return jsonify(error=True, message='The table {table} does not exist.'.format(table=table))

		column_response = db_utils.get_column_names(database, table)

		#check for existence of obs column along with others
		columns_with_obs_column = column_response + (obs_column,)

		missing_columns = tuple(column for column in columns_with_obs_column if column not in column_response)
		if missing_columns:
			return jsonify(error=True,
				message='The column {column} does not exist in that table or is not a numeric column.'.format(column=missing_columns[0]))
		
		graph_data_source = getattr(models, 'Graph_Data_Source')()
		setattr(graph_data_source, 'name', data_source_name)
		setattr(graph_data_source, 'graph_type', graph_type)
		setattr(graph_data_source, 'host', host)
		setattr(graph_data_source, 'database', database)
		setattr(graph_data_source, 'table', table)
		setattr(graph_data_source, 'obs_column', obs_column)
		setattr(graph_data_source, 'width_slider', include_width_slider)

		db.session.add(graph_data_source)
		db.session.flush()

		for column in columns:
			graph_data_source_column = getattr(models, 'Graph_Data_Source_Column')()
			setattr(graph_data_source_column, 'name', column)
			setattr(graph_data_source_column, 'graph_data_source', data_source_name)

			db.session.add(graph_data_source_column)

		g.user.subscribed_data_sources.append(graph_data_source)
		db.session.add(g.user)

		db.session.commit()

		return jsonify(error=False)
	else:
		return make_response('You must be logged in to use this feature.', 401)

def get_graph_data(data_source_str, start_utc, end_utc, the_set):
	'''
	get graph data from data source sets

	Args:
		data_source_str (str): data source string
		start_utc (int): start time in utc
		end_utc (int): end time in utc
		the_set (object): set object

	Returns:
		dict: lists of times, count, and obsnums for graph
	'''
	data_source = db_utils.query(database='search', table='graph_data_source', field_tuples=(('name', '==', data_source_str),))[0]

	pol_strs, era_type_strs, host_strs, filetype_strs = db.utils.get_set_strings()
	data = {pol_str: {era_type: {'obs_count': 0, 'obs_hours': 0} for era_type_str in era_type_strs} for pol_str in pol_strs}

	if the_set is not None:
		polarization = getattr(the_set, 'polarization')
		era_type = getattr(the_set, 'era_type')
		host = getattr(the_set, 'host')
		filetype = getattr(the_set, 'filetype')

		results = db_utils.query(data_source=data_source,
									field_tuples=(('time_start', '>=', start_utc), ('time_end', '<=', end_utc),
									('polarization', None if polarization == 'all' else '==', polarization),
									('era_type', None if era_type == 'all' else '==', era_type)),
									sort_tuples=(('time_start', 'asc'),))

		for obs in results:
			obs_time = getattr(obs, 'time_start')
			obsnum = getattr(obs, 'obsnum')
			obs_dict = {'obs_time': obs_time, 'obsnum': obsnum, 'obs_count': 1}
			data[polarization][era_type].append(obs_dict)


	else: #No set, so we need to separate the data into sets for low/high and EOR0/EOR1
		data = separate_data_into_sets(data, data_source, start_utc, end_utc)

	return data

def which_data_set(the_set):
	'''
	selects filters from set object

	Args:
		the_set (object): set object

	Returns:
		list: filter values
	'''
	polarization = getattr(the_set, 'polarization')
	era =  getattr(the_set, 'era')
	era_type = getattr(the_set, 'era_type')
	host = getattr(the_set, 'host')
	filetype =  getattr(the_set, 'filetype')

	which_data = (polarization, era, era_type, host, filetype)

	return which_data

def separate_data_into_sets(data, data_source, start_utc, end_utc):
	'''
	get graph data from data source sets

	Args:
		data (dict): data dictionary
		data_source (object): data source object
		start_utc (int): start time in utc
		end_utc (int): end time in utc

	Returns:
		dict: lists of times, count, and obsnums for graph
	'''
	obsid_results = db_utils.query(data_source=data_source,
									field_tuples=(('time_start', '>=', start_utc), ('time_end', '<=', end_utc)),
									sort_tuples=(('time_start', 'asc'),))

	for obs in obsid_results:
		polarization = getattr(obs, 'polarization')
		era_type = getattr(obs, 'era_type')

		# Actual UTC time of the obs (for the graph)
		obs_time = getattr(obs, 'time_start')
		obsnum = getattr(obs, 'obsnum')

		obs_dict = {'obs_time': obs_time, 'obsnum': obsnum, 'obs_count': 1}
		data[polarization][era_type].append(obs_dict)

	return data
