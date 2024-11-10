# Importing modules
import pandas as pd
import yadisk
from tqdm import tqdm
import re
import os
import shutil
import some_functions
from importlib import reload
from datetime import datetime, timedelta, timezone
from IPython.display import display, HTML
from IPython.core.display import HTML
import warnings; warnings.filterwarnings(action = 'ignore')
import sqlite3 as sl

# Align tables to the left in markdown cells
table_css = 'table {align:left;display:block} '
HTML('<style>{}</style>'.format(table_css))

# Set the text output length
pd.set_option('display.max_seq_items', 350)

# Set column width
pd.set_option('display.max_colwidth', 100)

# Display all columns
pd.set_option('display.max_columns', None)

# Wrapping headers
pd.set_option('expand_frame_repr', False)

# Loading environment variables for Yandex Disk
app_id = ''
secret_id = ''
ya_token = ''

# Connecting to Yandex Disk
y = yadisk.YaDisk(app_id, secret_id, ya_token)

# Checking the connection by validating the token
if y.check_token():
    print('Disk token correct')
    
print()

# Creating a file with functions
## Defining the current working directory
current_dir = os.getcwd()

### Path to the file some_functions.py
file_path = os.path.join(current_dir, 'some_functions.py')

#### Check if the file exists
if not os.path.exists(file_path):
    ##### Create a file with the function if it doesn't exist
    with open(file_path, 'w') as file:
        func_code = '''
   '''
        file.write(func_code)
    print(f'File "some_functions.py" was created in: {file_path}')
else:
    print(f'File "some_functions.py" already exists at: {file_path}')
    
###### Reload the module after changes
reload(some_functions)

print()

# Read files from the disk, check for their presence in the local directory, and download them if they are not present
list_of_files, load_path, files_with_dates = some_functions.create_file_list_and_load_path(y)

print()

# Check for new files, and if they exist, download them. Also check if old files need to be updated (by upload date).
# If the upload date in the local directory is earlier than on the disk, update the files, and move the outdated files to the archive.
some_functions.check_and_update_files(list_of_files, load_path)

print()

# Read files
dobro_files, other_files, dobro_dataframes, other_dataframes = some_functions.read_and_sort_files(load_path)

print()

# Concatenate 'dobro' files into customers
customers = pd.concat(dobro_dataframes, ignore_index=True)

# Check for the presence of the file named 'Заказы' in the folder and read it
#orders = pd.read_csv(os.path.join(load_path, other_files[0]), sep=';') if other_files else pd.DataFrame()
orders_file = next((f for f in other_files if 'Заказы' in f), None)
if orders_file:
    orders = pd.read_csv(os.path.join(load_path, orders_file), sep=';')
else:
    print("File 'Заказы' not found in folder.")
    orders = pd.DataFrame()

# Create copies of the datasets before transformations to monitor the percentage of data deletion
temp1 = customers.copy()
display('Number of rows in customers before changes:', len(temp1))
temp2 = orders.copy()
display('Number of rows in orders before changes:', len(temp2))

print()

# DATA PREPROCESSING IN CUSTOMERS
print('DATA PREPROCESSING IN CUSTOMERS:') 

## Displaying main information about the customers dataset
some_functions.display_dataset_info(customers)

print()

### Removing columns from the customers dataset
### Columns to be removed
columns_to_drop = ['CustomerActionActionTemplateIdsSystemName', 'CustomerActionBrandIdsSystemName',
                   'CustomerActionChannelIdsSystemName']

### Removing specified columns from the customers dataset
customers = customers.drop(columns=columns_to_drop, errors='ignore')

### Removing columns with 100% missing values
some_functions.remove_empty_columns(customers)

### Take a look at the data in the columns CustomerActionChannelIdsExternalId and CustomerActionChannelName
customers[['CustomerActionChannelIdsExternalId', 'CustomerActionChannelName']].sample(5)

### Remove the CustomerActionChannelIdsExternalId column as it duplicates CustomerActionChannelName
customers.drop(columns = ['CustomerActionChannelIdsExternalId'], inplace=True)

### Report on the removal of columns from customers
some_functions.find_removed_columns(temp1, customers)

print()

#### Change the data type of CustomerActionDateTimeUtc and CustomerActionCreationDateTimeUtc to datetime
cols_to_change = ['CustomerActionDateTimeUtc', 'CustomerActionCreationDateTimeUtc']
for col in cols_to_change:
    customers[col] = pd.to_datetime(customers[col], errors='coerce')
#### Change the data type to integer in CustomerActionChannelIdsMindboxId
cols_to_change = ['CustomerActionChannelIdsMindboxId']
for col in cols_to_change:
    customers[col] = pd.to_numeric(customers[col], errors='coerce').astype('int')

#### Report on data type changes in customers
some_functions.find_changed_data_types(temp1, customers) 

print()   

##### Calculate the proportion of missing data in the columns
print('Proportion of missing values in customers:')
print(pd.DataFrame(round(customers.isna().mean() * 100, 5)).sort_values(by = 0))

print()

# DATA PREPROCESSING IN ORDERS
print('DATA PREPROCESSING IN ORDERS:') 

## Displaying main information about the orders dataset
some_functions.display_dataset_info(orders)

print()

### Remove columns from the orders dataset that have 100% missing values
some_functions.remove_empty_columns(orders)

### The data in the columns OrderLinePriceOfLine and OrderLineBasePricePerItem are likely identical. 
### We will check this information, and if it is true, we will remove the OrderLineBasePricePerItem column.
### First, we will remove missing values from OrderLineBasePricePerItem.
orders_cleaned = orders.dropna(subset=['OrderLineBasePricePerItem'])
orders_cleaned['OrderLineBasePricePerItem'] = orders_cleaned['OrderLineBasePricePerItem'].astype(int)
if orders_cleaned['OrderLinePriceOfLine'].equals(orders_cleaned['OrderLineBasePricePerItem']):
    print('Data in columns OrderLinePriceOfLine and OrderLineBasePricePerItem is the same.')
    ### Removing the column OrderLineBasePricePerItem
    orders.drop(columns=['OrderLineBasePricePerItem'], inplace=True)
else:
    print('Data in columns OrderLinePriceOfLine and OrderLineBasePricePerItem is different.')
### Checking the OrderDeliveryCost column for unique values
display(orders['OrderDeliveryCost'].unique())
print()
display(orders['OrderDeliveryCost'].value_counts())

### Removing the OrderDeliveryCost column
orders.drop(columns = ['OrderDeliveryCost'], inplace=True)

### Check the columns OrderLineNumber for unique values
display(orders['OrderLineNumber'].unique())
print()
display(orders['OrderLineLineNumber'].unique())

### Remove these columns, as this is likely part of a boxed solution and this information is not needed
orders.drop(columns = ['OrderLineNumber', 'OrderLineLineNumber'], inplace=True)

### Take a look at the data in the columns OrderFirstActionChannelIdsExternalId and OrderFirstActionChannelName
orders[['OrderFirstActionChannelIdsExternalId', 'OrderFirstActionChannelName']].sample(5)

### Remove the column OrderFirstActionChannelIdsExternalId as it duplicates OrderFirstActionChannelName
orders.drop(columns = ['OrderFirstActionChannelIdsExternalId'], inplace=True)

print()

### Report on the removal of columns from orders
some_functions.find_removed_columns(temp2, orders)

print()

#### Change the data type in OrderFirstActionDateTimeUtc
orders['OrderFirstActionDateTimeUtc'] = pd.to_datetime(orders['OrderFirstActionDateTimeUtc'], errors='coerce')

#### Report on changes in data types in orders
some_functions.find_changed_data_types(temp2, orders)

print()

##### Calculate the proportion of missing data in the columns
print('Proportion of missing values in orders:')
print(pd.DataFrame(round(orders.isna().mean() * 100, 5)).sort_values(by = 0))

print()

# Compare our data by the number of rows at the end of data processing in the datasets
a1, b1 = len(temp1), len(customers)
print('Rows in customers before::', len(temp1), ', after:', len(customers), ', deleted in %:',
      round((a1 - b1) / a1 * 100, 2))

a2, b2 = len(temp2), len(orders)
print('Rows in customers before::', len(temp2), ', after:', len(orders), ', deleted in %:',
      round((a2 - b2) / a2 * 100, 2))
print()

# Create a database, connect to it, and upload the datasets to it
some_functions.create_and_load_datasets(customers, orders)




