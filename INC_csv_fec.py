import json
import csv
from api_k import *
import requests
import os
import time 
import fileinput
import MySQLdb
import pandas as pd
import datetime
#disabled warning regarding insecure platform, should import appropriate modules to
#make platform secure
requests.packages.urllib3.disable_warnings()

#initial url used to extract page number/count
#FEC API limit is 100 results per page
URL_BASE = 'https://api.open.fec.gov/v1/candidates/search/?sort=name&api_key=%s&per_page=100' % (key)

response = requests.get(URL_BASE)
data = response.json()

parse = data['pagination']
#using the range of the count as opposed to range of pages because 
#there are inconsistencies with pagination function that the FEC API uses.
#need the range to exceed the number of pages reported in the json. 
#for more information read https://18f.gsa.gov/2015/07/15/openfec-api-update/
p = range(parse['count'])

#p_list and url_list allow you to loop through url by page
p_list = []

for num in p:
	p_list.append(num)

url_list = []

for page in p_list:
	url = 'https://api.open.fec.gov/v1/candidates/search/?sort=name&api_key=%s&per_page=100&page=%s' % (key, page)
	url_list.append(url)

now = datetime.datetime.now()

#committees(), candidates(), filings() extract data  
#from endpoint and transfer the data into a csv file
def committees():
	#if you change the file path csv document name, 
	#make sure you also change for the duplicate function
	file_path = open(PATH + 'fec_com1.csv', 'a')
	
	empty_status = os.stat(PATH + 'fec_com1.csv').st_size == 0

	file_path.seek(0, os.SEEK_END)

	csvwriter = csv.writer(file_path)
	
	count = 0

	#start at 1 becasue otherwise calls page = 0, which doesn't exist
	for u in url_list[1:len(p)]:
		#print u so you know page that loop is on
		print u
		response_2 = requests.get(u)
		data_2 = response_2.json()
		parse_results = data_2['results']

		#must allow loop to continue until the array is empty
		#in order to get the call to stop due to issues with paginiation 
		if parse_results != []:

			for i in parse_results:
				row = i['principal_committees']

				for c in row:
					#must change 'candidate_ids' to 'candidate_id' in order for the JOIN to 
					#work later in the ETL process
					c['candidate_id'] = c['candidate_ids']
					del c['candidate_ids']
					id_1 = c['candidate_id']
					c['candidate_id'] = id_1[0]

					if empty_status == True:
						if count == 0:
							csvwriter.writerow(['committee_id', 'name', 'candidate_id', 'designation', 'timestamp'])
							count += 1
						
					csvwriter.writerow([c['committee_id'], c['name'], c['candidate_id'],
					 					c['designation'], now])

		elif parse_results == []:
			break
		
	file_path.close()

	dupe_csv = pd.read_csv('fec_com1.csv')
	clean = dupe_csv.drop_duplicates(['committee_id', 'name', 'candidate_id', 'designation'])
	clean.to_csv('fec_com1.csv', mode = 'w', index = False)
	time = clean['timestamp'].max()
	print time

	mydb = MySQLdb.connect(host = host_name,
						port = 3306,
						user = user_name,
						passwd = pas, 
						db = data_base,
						unix_socket = 'tmp/mysql.sock') 

	cursor = mydb.cursor()

	csv_data = csv.reader(file('fec_com1.csv'))

	firstline = True
	secondline = True

	cursor.execute('TRUNCATE TABLE fec_committees_inc')

	for row in csv_data:
		#skips importation of first line, which contains column names
		if firstline:
			firstline = False
			continue
		if secondline:
			secondline = False
			continue
		#only imports most recent data from csv based on the timestamp
		if row[4] == time:
			#title() changes committee name to title case
			row_list = [row[0], row[1].title(), row[2], row[3]]

			print row_list
			cursor.execute('INSERT IGNORE INTO fec_committees_inc(\
					fec_id, committee_name, candidate_id, designation)' \
					'VALUES(%s, %s, %s, %s)', row_list)
	
			cursor.execute('INSERT IGNORE INTO fec_committees SELECT * FROM fec_committees_inc')

	mydb.commit()
	cursor.close()

def candidates():
	#if you change the file path csv document name 
	#make sure you also change the file in the duplicate function
	file_path = open(PATH + 'fec_cand1.csv', 'a')
	
	empty_status = os.stat(PATH + 'fec_cand1.csv').st_size == 0

	file_path.seek(0, os.SEEK_END)

	csvwriter = csv.writer(file_path)
	
	count = 0

	#start at 1 becasue otherwise calls page = 0, which doesn't exist
	for u in url_list[1:len(p)]:
		#print u so you know page that loop is on
		print u
		response_2 = requests.get(u)
		data_2 = response_2.json()
		parse_results = data_2['results']

		#must allow loop to continue until the array is empty
		#in order to get the call to stop due to issues with paginiation 
		if parse_results != []:
			for row in parse_results:
				if empty_status == True:
					if count == 0:
						csvwriter.writerow(['district', 'incumbent_challenge', 'name', 'office', 
										'state', 'party', 'candidate_id', 'timestamp'])
						count += 1
				#must convert district column to string, otherwise is loaded as float
				csvwriter.writerow([str(row['district']), row['incumbent_challenge'], row['name'], 
									row['office'], row['state'], row['party'], row['candidate_id'], now])
		elif parse_results == []:
			break
	
	file_path.close()

	dupe_csv = pd.read_csv('fec_cand1.csv')
	clean = dupe_csv.drop_duplicates(['candidate_id'])
	clean.to_csv('fec_cand1.csv', mode = 'w',  index = False)
	time = clean['timestamp'].max()
	print time

	mydb = MySQLdb.connect(host = host_name,
						port = 3306,
						user = user_name,
						passwd = pas, 
						db = data_base,
						unix_socket = 'tmp/mysql.sock') 

	cursor = mydb.cursor()

	csv_data = csv.reader(file('fec_cand1.csv'))

	firstline = True
	secondline = True

	for row in csv_data:
		#skips importation of first line, which contains column names
		if firstline:
			firstline = False
			continue
		if secondline:
			secondline = False
			continue
		#the following if statements accomodate for errors in the formatting of candidate names
		#and format the names into three columns by first, middle, and last name
		if row[7] == time:
			if ', ' in row[2]:
				row_17 = row[2].title().split(', ')
				first_mid = row_17[1]
				last = row_17[0]
			
				if ' ' in first_mid:
					mid = first_mid.split(' ')
					first = mid[0]
					mid = mid[1]

					row_list_1 = [row[0], row[1], row[3], row[4], row[5], row[6], first, mid, last]
					print row_list_1

					cursor.execute('INSERT IGNORE INTO fec_candidates(\
						district, incumbent_challenge, office, state, party, candidate_id, first_name, middle_name, last_name)' \
						'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list_1)

				else:
					first = first_mid
					mid = ''
					
					row_list_2 = [row[0], row[1], row[3], row[4], row[5], row[6], first, mid, last]
					print row_list_2
		
					cursor.execute('INSERT INTO fec_candidates(\
						district, incumbent_challenge, office, state, party, candidate_id, first_name, middle_name, last_name)' \
						'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list_2)
			
			elif ',' in row[2]:
				row_17 = row[2].title().split(',')
				first_mid = row_17[1]
				last = row_17[0]
			
				if ' ' in first_mid:
					mid = first_mid.split(' ')
					first = mid[0]
					mid = mid[1]

					row_list_1 = [row[0], row[1], row[3], row[4], row[5], row[6], first, mid, last]
					print row_list_1

					cursor.execute('INSERT INTO fec_candidates(\
						district, incumbent_challenge, office, state, party, candidate_id, first_name, middle_name, last_name)' \
						'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list_1)
				else:
					first = first_mid
					mid = ''
					
					row_list_2 = [row[0], row[1], row[3], row[4], row[5], row[6], first, mid, last]
					print row_list_2

					cursor.execute('INSERT INTO fec_candidates(\
						district, incumbent_challenge, office, state, party, candidate_id, first_name, middle_name, last_name)' \
						'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list_2)
			elif ' ' in row[2]:
				row_17 = row[2].title().split(' ')
				first_mid = row_17[1]
				last = row_17[0]
			
				if ' ' in first_mid:
					mid = first_mid.split(' ')
					first = mid[0]
					mid = mid[1]

					row_list_1 = [row[0], row[1], row[3], row[4], row[5], row[6], first, mid, last]
					print row_list_1

					cursor.execute('INSERT INTO fec_candidates(\
						district, incumbent_challenge, office, state, party, candidate_id, first_name, middle_name, last_name)' \
						'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list_1)

				else:
					first = first_mid
					mid = ''
					
					row_list_2 = [row[0], row[1], row[3], row[4], row[5], row[6], first, mid, last]
					print row_list_2

					cursor.execute('INSERT INTO fec_candidates(\
						district, incumbent_challenge, office, state, party, candidate_id, first_name, middle_name, last_name)' \
						'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list_2)
		
	mydb.commit()
	cursor.close()

def filings():

	#must mannually change report_year if you want to retrieve past data
	url_base_f = 'https://api.open.fec.gov/v1/filings/?form_type=F3&form_type=F3P&api_key=%s&per_page=100&report_year=%s'\
				 % (key, now.year)

	response_f = requests.get(url_base_f)
	data_f = response_f.json()

	parse_f = data_f['pagination']
	#using the range of the count as opposed to range of pages because 
	#there are inconsistencies with pagination function that the FEC API uses.
	#need the range to exceed the number of pages reported in the json. 
	p_f = range(parse_f['count'])

	#p_list and url_list allow you to loop through url by page
	p_list_f = []
	url_list_f = []

	for num_f in p_f:
		p_list_f.append(num_f)

	for page_f in p_list_f:
		#must mannually change report_year if you want to retrieve past data
		url_f = 'https://api.open.fec.gov/v1/filings/?form_type=F3&form_type=F3P&api_key=%s&per_page=100&amendment_indicator=N\
				&page=%s&amendment_indicator=N&report_year=%s' % (key, page_f, now.year)
		url_list_f.append(url_f)
		
	#if you change the file path csv document name, 
	#make sure you also change the file in the duplicate function
	file_path = open(PATH + 'fec_file1.csv', 'a')
	#this allows for appending document without overwriting previous information
	file_path.seek(0, os.SEEK_END)

	empty_status = os.stat(PATH + 'fec_file1.csv').st_size == 0

	csvwriter = csv.writer(file_path)

	count = 0

	#start at 1 becasue otherwise calls page = 0, which doesn't exist
	for u in url_list_f[1:len(p_f)]:
		#print u so you know page that loop is on
		print u
		response_2 = requests.get(u)
		data_2 = response_2.json()
	
		parse_results = data_2['results']
		parse_page = data_2['pagination']

		#must allow loop to continue until the array is empty
		#in order to get the call to stop due to issues with paginiation 
		if parse_results != []:
			for row_f in parse_results:
				if empty_status == True:
					if count == 0:
						csvwriter.writerow(['report_type', 'total_receipts', 'committee_id',
										'debts_owed_by_committee', 'cycle', 'cash_on_hand_end_period', 
										'form_type','total_disbursements','receipt_date', 'timestamp'])
						count += 1

				csvwriter.writerow([row_f['report_type'], row_f['total_receipts'], row_f['committee_id'], 
									row_f['debts_owed_by_committee'], row_f['cycle'],
					 				row_f['cash_on_hand_end_period'], row_f['form_type'], 
					 				row_f['total_disbursements'], row_f['receipt_date'], now])
		elif parse_results == []:
			break
		
	file_path.close()

	dupe_csv = pd.read_csv('fec_file1.csv')
	clean = dupe_csv.drop_duplicates(['report_type', 'committee_id', 'receipt_date'])
	clean.to_csv('fec_file1.csv', mode = 'w', index = False)
	time = clean['timestamp'].max()
	print time

	mydb = MySQLdb.connect(host = host_name,
						port = 3306,
						user = user_name,
						passwd = pas, 
						db = data_base,
						unix_socket = 'tmp/mysql.sock') 

	cursor = mydb.cursor()

	csv_data = csv.reader(file('fec_file1.csv'))

	firstline = True
	secondline = True

	cursor.execute('TRUNCATE TABLE fec_filings_inc')

	for row in csv_data:
		#skips importation of first line, which contains column names
		if firstline:
			firstline = False
			continue
		if secondline:
			secondline = False
			continue
		if row[9] == time:
		
			row_list = [row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]]
			print row_list

			cursor.execute('INSERT IGNORE INTO fec_filings_inc(\
					report_type, total_receipts, committee_id, debts_owed_by_committee, cycle, cash_on_hand_end_period,\
					form_type, total_disbursements, receipt_date)' \
					'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)', row_list)

			cursor.execute('INSERT IGNORE INTO fec_filings SELECT * FROM fec_filings_inc')

	mydb.commit()
	cursor.close()


#committees()
#candidates()
#filings()



