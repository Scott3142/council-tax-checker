import pandas as pd
import numpy as np
import requests

import warnings
warnings.filterwarnings("ignore")

csv_2002 = "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/pp-2002.csv"
csv_2003 = "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/pp-2003.csv"
csv_2004 = "http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/pp-2004.csv"
header_rows = ["TUID","Price","Date","Postcode","Property Type","Old / New","Duration","PAON","SAON","Street","Locality","Town","District","County","PPD Category","Record Status"]

df_2002 = pd.read_csv(csv_2002,names=header_rows)
df_2003 = pd.read_csv(csv_2003,names=header_rows)
df_2004 = pd.read_csv(csv_2004,names=header_rows)

df = pd.concat([df_2002,df_2003,df_2004],ignore_index=True)
df['Date'] = pd.to_datetime(df['Date'])

start_time = '2002-01-01 00:00:00'
end_time = '2004-12-31 00:00:00'
time_mask = (df['Date'] > start_time) & (df['Date'] < end_time)
df_window = df.loc[time_mask]

allowable_house_types = ['D','S','T','F','O']
allowable_bands = ['A','B','C','D','E','F','G','H','I']
locality = input("What is your locality? ")
while True:
  house_type = input("What is your house type? (D - Detached, S - Semi-detached, T - Terraced, F - Flats, O - Other) ").upper()
  if house_type not in allowable_house_types:
    print("That is not a recognised house type. Please select from the options.")
  else:
    break
bedrooms = input("How many bedrooms does your house have? ")
while True:
  current_band = input("What is your current council tax band? ").upper()
  if current_band not in allowable_bands:
    print("That is not a recognised band. Please select from the options.")
  else:
    break

tax_brackets = {
    "A": 44000,
    "B": 65000,
    "C": 91000,
    "D": 123000,
    "E": 162000,
    "F": 223000,
    "G": 324000,
    "H": 424000
}

band_idx = allowable_bands.index(current_band)
lower_band = allowable_bands[band_idx-2]
goal_band = allowable_bands[band_idx-1]
upper_band = allowable_bands[band_idx]
lower_value = tax_brackets[lower_band]
goal_value = tax_brackets[goal_band]
upper_value = tax_brackets[upper_band]

df_locality = df_window[df_window['Locality'] == locality.upper()]
df_type = df_locality[df_locality['Property Type'] == house_type]
df_value = df_type[(df_type['Price'] > lower_value) & (df_type['Price'] < upper_value)]

query_columns = ["PAON","Street","County","Postcode"]
df_value["Bedrooms"] = np.nan
df_value["Valuation"] = np.nan
for i in range(len(df_value)):
  query_paon = df_value["PAON"].iloc[i]
  query_street = df_value["Street"].iloc[i].lower().replace(" ","-")
  query_county = df_value["County"].iloc[i].lower()
  try:
    query_postcode = df_value["Postcode"].iloc[i].lower().replace(" ","-")
  except:
    query_postcode = "cf15-8hg"
  url_query = f"{query_paon}-{query_street}-{query_county}-{query_postcode}"
  url = f"https://themovemarket.com/tools/propertyprices/{url_query}"
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
  response = requests.get(url, headers=headers)
  html = response.content
  price_partition = html.partition(b"valuation of ")
  price_partition = price_partition[2].decode("utf-8")
  try:
    current_value = int(price_partition[1:8].replace(",",""))
  except:
    current_value = np.nan
  df_value["Valuation"].iloc[i] = current_value
  if b"bedrooms" in html:
    bedrooms_partition = html.partition(b"bedrooms")
    bedrooms_partition = bedrooms_partition[0].decode("utf-8")
    number_of_bedrooms = bedrooms_partition[-2]
    df_value["Bedrooms"].iloc[i] = number_of_bedrooms

house_types = {
    'D' : "detached houses",
    'S' : "semi-detached houses",
    'T' : "terraced houses",
    'F' : "flats",
    'O' : "other properties"
}
house_type_long = house_types[house_type]

df_bedrooms = df_value[df_value['Bedrooms'] == bedrooms]
bracket_idx = 0
for value in tax_brackets.values():
  if df_bedrooms['Price'].mean() < value:
    break
  bracket_idx += 1
estimated_band = list(tax_brackets.keys())[bracket_idx]
df_bedrooms_under_threshold = df_bedrooms[df_bedrooms['Price'] < goal_value]
band_statuses = ['correct','incorrect']
band_idx = 1
if estimated_band == current_band:
  band_idx = 0

print()
print(f"The mean sale price of {house_type_long} with {bedrooms} bedrooms in {locality} between 01/01/2002 and 31/12/2004 was £{df_bedrooms['Price'].mean():.0f}.")
print(f"Of {len(df_bedrooms)} houses sold in your area in the timeframe, {len(df_bedrooms_under_threshold)} ({len(df_bedrooms_under_threshold)/len(df_bedrooms)*100:.0f}%) were sold in the lower council tax bracket.")
print(f"This estimates your tax bracket as {estimated_band}. Your banding is therefore {band_statuses[band_idx]}.")