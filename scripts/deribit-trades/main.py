import asyncio
import json
import time
import csv
import keyring
import sys
from interface import deribit_interface
from load_credentials import CLIENT_ID, CLIENT_SECRET
from pymongo import MongoClient
from pathlib import Path

d = Path().resolve().parent

with open(str(d) + '/credentials.txt', 'r') as file:
    credentials = file.read().replace('\n', '')

if CLIENT_ID == '' or CLIENT_SECRET == '':
	sys.exit('Run save_credentials.py first in order to store your credentials on this machine!')

### system value ###
deribit = deribit_interface.Deribit(test=False,
	client_ID=CLIENT_ID,
 	client_secret=CLIENT_SECRET)
logwriter = deribit.logwriter

def construct_instruments(maturitystr, strike):
	# Manually create instrument
	call = 'BTC-' + maturitystr + '-' + str(strike) + '-C'
	put = 'BTC-' + maturitystr + '-'+ str(strike) + '-P'
	return call, put


def create_instruments(_currency, _kind):
	# Get all instruments from a request
	try:
		all_instruments = []
		book_summaries = deribit.get_book_summary_by_currency(_currency, _kind)
		for book in book_summaries:
			all_instruments.append(book['instrument_name'])
		return all_instruments
	except Exception as e:
		print('Error in create_instruments: ', e)

def extract_greeks(instrument, ob):
	return [instrument, ob['greeks']]

def save_dict_to_file(dict, fname):
	# Todo: This must be appended for each dictionary to come
    f = open(fname + '.txt','a')
    f.write(str(dict) + '\n')
    f.close()

def check_memory(_list, max_len = 1000):
	if len(_list) > max_len:
		_list = []
	return _list


client = MongoClient(credentials) # e.g. 'mongodb://localhost:27017'
db = client['cryptocurrency']
orderbooks = db['deribit_orderbooks']
transactions = db['deribit_transactions']


orderbook_file 			= 'orderbooks'
trade_file 				= 'trades'
collected_change_ids 	= []
collected_trades 		= []
while True:
	try:
	# Retrieve all instruments
		all_option_instruments = create_instruments('BTC', 'option')
		assert(len(all_option_instruments) > 0)
		# All orderbooks
		for instrument in all_option_instruments:
			ob = deribit.get_order_book(instrument)
			if ob is not None:
				print(instrument)
				print(ob)
				if ob['change_id'] not in collected_change_ids:
					collected_change_ids.append(ob['change_id'])

					# Save locally
					save_dict_to_file(ob, orderbook_file)
					check_memory(collected_change_ids)

					# Add to db
					res = orderbooks.insert_one(ob)
					print('One orderbook: {0}'.format(res.inserted_id))

					# Retrieve from db
					#test_retrieve = orderbooks.find_one({'instrument_name':})
					#print(test_retrieve)
				else:
					print('already got orderbook')
			time.sleep(0.1)

		# All executed trades
		trades = deribit.get_last_trades_by_currency('BTC', 'option', 100) # TO BE DONE
		if trades is not None:
			for trade in trades['trades']:
				if trade not in collected_trades:
					collected_trades.append(trade)
					
					# Save locally
					save_dict_to_file(trade, trade_file)

					# Add to db
					res_transactions = transactions.insert_one(trade)
					print('One trade: {0}'.format(res_transactions.inserted_id))

		time.sleep(1)
	except Exception as e:
		logwriter('No Instruments! ', e)
		time.sleep(60)


