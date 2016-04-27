## **About**

This python code is the beginning stage of the extract, transform, and load process applied to the Federal Election Commission’s API.You can find the documentation regarding the FEC’s API at https://api.open.fec.gov/developers/. The data is extracted from the FEC’s API using the requests module and the /candidates and /filings endpoints. The data is then stored in a csv file. Once in the csv format, the data is loaded into a MySQL database using the MySQLdb module. This is my first attempt at a large coding project so I am still working on debugging the code, bettering the entire ETL process, and completing the load process. As it stands the code loads the data into MySQL but does not account for duplicates from future imports nor does it store the information in an incubator table before loading it into a fact table.


## **Purpose**


The purpose of this code is to extract data pertaining to the finances of federal candidate committees (and thus candidates) by retrieving the filed Form 3s and Form 3Ps. The /filings endpoint with parameters ‘form_type=F3&form_type=F3P’ provides quarterly breakdowns of each federally filed candidate committees’ receipts, disbursements, debts owed, and cash on hand. The total raised by a candidate committee can be calculated by adding the total_receipts of the desired cycle and the total spent can be calculated by adding the total_disbursements.   The /financial endpoint was not used because it only allows the retrieval of a candidate committee’s most up-to-date financial information. 

The /candidates endpoint is used to retrieve information that is not provided in the /filings endpoint, specifically the candidate name, district, incumbency indicator, office, state, and party. The information from the /candidates endpoint and the /filings endpoint can be synthesized into one table using the committee_id and candidate_id parameters to JOIN the relevant tables. 


## **URLs**

https://api.open.fec.gov/v1/candidates/search/?sort=name&api_key=DEMO_KEY&per_page=100&page=PAGE_NUM

https://api.open.fec.gov/v1/filings/?form_type=F3&form_type=F3P&api_key=DEMO_KEY&per_page=100&amendment_indicator=N&page=PAGE_NUM&amendment_indicator=N&report_year=now.year


## **Usage**

Worked with Python 2.7 and MySQL.


## **Modules used:**

json

csv

requests

os

datetime

fileinput

MySQLdb

pandas
