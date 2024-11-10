# Importing modules
import matplotlib.pyplot as plt
import seaborn as sns
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
import pandas as pd
import os
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
import sqlite3 as sl
from IPython.display import display, HTML


# Define a function that returns a list of removed columns after preprocessing
def find_removed_columns(original_df, modified_df):
    """
    Compares the columns of the original and modified datasets and returns the names of removed columns.
    
    :param original_df: Original dataset
    :param modified_df: Modified dataset
    :return: List of removed columns
    """
    original_columns = set(original_df.columns)
    modified_columns = set(modified_df.columns)
    
    # Determine removed columns
    removed_columns = list(original_columns - modified_columns)
    if removed_columns:
        print('Removed columns:', removed_columns)
    else:
        print('All columns remained unchanged')
    # Return the list of removed columns
    return removed_columns


# Define a function to output columns where the data type has changed after preprocessing
def find_changed_data_types(original_df, modified_df):
    """
    Compares the data types of columns in the original and modified datasets and returns the names of columns
    where the data type has changed, ignoring NaN.
    
    :param original_df: Original dataset
    :param modified_df: Modified dataset
    :return: List of columns with changed data types
    """
    original_types = original_df.dtypes
    modified_types = modified_df.dtypes
    
    # Determine columns where data types have changed
    changed_columns = []
    for col in original_types.index:
        if col in modified_types.index:
            original_type = original_types[col]
            modified_type = modified_types[col]
            
            # Check if the data type has changed
            if original_type != modified_type:
                changed_columns.append(col)
            # Also add columns if they have NaN, if the type has changed
            elif modified_type == 'object' and pd.api.types.is_numeric_dtype(original_type):
                changed_columns.append(col)

    if changed_columns:
        print('Changed data types in columns:', changed_columns)
    else:
        print('No changes in data types')
    
    # Return the list of columns with changed data types
    return changed_columns


# Define a function to create a database, connect to it, and load datasets into it
def create_and_load_datasets(customers, orders):
    """
    Creates a connection to the database and loads the datasets.

    :param customers: Dataset of customers
    :param orders: Dataset of orders
    """
    # Создаем соединение с базой данных
    db_path= 'aif.sql'
    '''
    conn = sl.connect(db_path)

    # Добавляем датасеты в базу данных
    customers.to_sql('customers', conn, if_exists='replace', index=False)
    orders.to_sql('orders', conn, if_exists='replace', index=False)

    # Закрываем соединение
    conn.close()
    '''
    try:
        # Create a connection to the database
        conn = sl.connect(db_path)

        # Add datasets to the database
        customers.to_sql('customers', conn, if_exists='replace', index=False)
        orders.to_sql('orders', conn, if_exists='replace', index=False)

        # Report
        print("Database created and datasets loaded successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the connection if it was opened
        if 'conn' in locals():
            conn.close()
            

# Define a function to execute SQL queries and output results as a table
def execute_query(sql):
    """
    Executes an SQL query and returns the results as a DataFrame.
    
    :param sql: SQL query to be executed
    :return: DataFrame with the query results
    """
    # Path to the database
    db_path = 'aif.sql'
    
    # Create a connection to the database
    conn = sl.connect(db_path)
    
    try:
        # Execute the query and save the result in a DataFrame
        df = pd.read_sql_query(sql, conn)
        return df  
    except Exception as e:
        print(f"Error executing query: {e}")
        return None
    finally:
        # Close the connection
        conn.close()


# Define a function to create lists of files on disk and in the local folder
def create_file_list_and_load_path(y):
    """
    Creates a list of files for download from the specified path and outputs information about files in the local folder.

    :param y: Object used to get the list of files (e.g., Yandex Disk API)
    :return: list_of_files, load_path, files_with_dates
    """

    print('Creating list of files')
    list_of_files = []
    for el in tqdm(y.listdir('aif_etl')):
        if el['path'].endswith(('.csv', '.pkl', 'txt')):
            # Add the path and upload date (last modified) of the file
            file_info = {
                'path': el['path'],
                'upload_date': el['modified']  # Get the last modified date
            }
            list_of_files.append(file_info)

    # Check the contents of the file list
    print('Files from disk:')
    for file in list_of_files:
        print(f"File: {file['path']}, Date: {file['upload_date']}")
    print()
    
    # Create a folder for loading data
    current_directory = os.getcwd()
    load_path = os.path.join(current_directory, 'aif_etl')

    if not os.path.exists(load_path):  # If such a directory does not exist, create it
        os.mkdir(load_path) 

    os.chdir(load_path)
    
    # Get the list of files in the local folder
    local_files = os.listdir(load_path)

    # Check if files need to be downloaded (if they exist in the folder or not)
    if len(local_files) < len(list_of_files):
        print("Local directory is missing some files. Downloading...")
        for file_info in list_of_files:
            file_name = os.path.basename(file_info['path'])
            local_file_path = os.path.join(load_path, file_name)
            
            # Download only the missing files
            if not os.path.exists(local_file_path):
                try:
                    y.download(file_info['path'], local_file_path)
                    print(f"Downloaded '{file_name}'")
                except Exception as e:
                    print(f"Error downloading file '{file_name}': {e}")

    # Update the list of local files after downloading
    local_files = os.listdir(load_path)

    # Create a list to store files and their upload dates
    files_with_dates = []
    for file in local_files:
        file_path = os.path.join(load_path, file)
        upload_date = datetime.fromtimestamp(os.path.getmtime(file_path))  # Get the file's modification date
        files_with_dates.append((file, upload_date))  # Save the file name and date in the list
    
    # Output files and their upload dates
    print('Files from local directory:')
    for file, upload_date in files_with_dates:
        print(f"File: {file}, Upload Date: {upload_date}")

    return list_of_files, load_path, files_with_dates


# Define a function to check for new files and update old ones
def check_and_update_files(list_of_files, load_path):
    """
    Checks and updates files in the local directory, moving old versions to an archive
    and downloading new versions from disk.

    :param list_of_files: List of files to check and update
    :param load_path: Path to the local directory for downloading files
    """
    # Path to the local directory and archive
    archive_path = os.path.join(load_path, 'archive')

    # Create the archive subdirectory if it does not exist
    os.makedirs(archive_path, exist_ok=True)

    # Get the list of files in the local folder
    local_files = os.listdir(load_path)

    new_files = []  

    # Check and update files
    for file_info in tqdm(list_of_files):
        file_name = os.path.basename(file_info['path'])

        # Check for the 'upload_date' key
        if 'upload_date' in file_info:
            upload_date = file_info['upload_date']

            # Check the type of upload_date
            if isinstance(upload_date, str):
                # Convert the string to a datetime object
                upload_date = datetime.strptime(upload_date, '%Y-%m-%d')
            elif not isinstance(upload_date, datetime):
                print(f"Upload date for file '{file_name}' is of an unexpected type: {type(upload_date)}. Skipping...")
                continue  # Skip this file if the type is unexpected
        else:
            print(f"Upload date not found for file '{file_name}'. Skipping...")
            continue  # Skip this file if there is no date

        # If upload_date has a timezone, use that
        if upload_date.tzinfo is None:
            upload_date = upload_date.replace(tzinfo=timezone.utc)

        local_file_path = os.path.join(load_path, file_name)
        local_mod_time = datetime.fromtimestamp(os.path.getmtime(local_file_path), tz=timezone.utc)

        if upload_date > local_mod_time:
            # If the file on disk is newer, move the old file to the archive
            shutil.move(local_file_path, os.path.join(archive_path, file_name))
            print(f"File '{file_name}' has been updated.")
            try:
                download_path = file_info['path']  # Path to the file on disk
                new_file_path = os.path.join(load_path, file_name)
                # Download the file from disk
                y.download(download_path, new_file_path)  
                print(f"File '{file_name}' has been downloaded.")
            except Exception as e:
                print(f"Error downloading file '{file_name}': {e}")
        else:
            print(f"File '{file_name}' does not require updating.")

        # Add the file to the list of new ones if it is not in the local files
        if file_name not in local_files:
            new_files.append(file_name)

    # Output the list of new files
    if new_files:
        print("Downloading new files:")
        for file in tqdm(new_files):
            # Downloading the file
            y.download(file_info['path'], file)  
            print(f'File {file} uploaded.')
    else:
        print('There are no new files.')

        
# Define a function for reading files
def read_and_sort_files(load_path):
    """
    Reads CSV files from the specified directory, sorts them, and categorizes them
    into 'dobro' and 'other' based on the presence of the keyword 'dobro' in the filename.

    Args:
        load_path (str): The path to the directory containing the files to be read.

    Returns:
        tuple: Four lists containing:
            - dobro_files (list): Filenames that contain 'dobro'.
            - other_files (list): Filenames that do not contain 'dobro'.
            - dobro_dataframes (list): DataFrames corresponding to 'dobro' files.
            - other_dataframes (list): DataFrames corresponding to 'other' files.
    """
    # Get the list of files in the local folder
    local_files = os.listdir(load_path)
    local_files.sort()  # Sort files in alphabetical order

    # Counters for file namesв
    file_count_dobro = 1
    file_count_other = 1

    # Lists to store files and dataframes
    dobro_files = []
    other_files = []
    dobro_dataframes = []  # List for 'dobro dataframes
    other_dataframes = []  # List for 'other' dataframes

    # Read files and create dataframes
    for file in local_files:
        if file.endswith('.csv'):  # Read only CSV files
            try:
                file_path = os.path.join(load_path, file)
                df = pd.read_csv(file_path, sep=';')

                if "dobro" in file.lower():  # If the file contains 'dobro' in any case
                    dobro_files.append(file)  # Add file to the 'dobro' list
                    dobro_dataframes.append(df)  # Add dataframe to the list
                    print(f"File '{file}' has been read as 'file_{file_count_dobro}'.")
                    file_count_dobro += 1  # Increment the counter
                else:
                    other_files.append(file)  # Add file to the 'other' list
                    other_dataframes.append(df)  # Add dataframe to the list
                    print(f"File '{file}' has been read as 'other_file_{file_count_other}'.")
                    file_count_other += 1  # Increment the counter

            except Exception as e:
                print(f"Error reading file '{file}': {e}")

    return dobro_files, other_files, dobro_dataframes, other_dataframes


# Define a function to remove columns with 100% missing values
def remove_empty_columns(df):

    # Find columns with 100% missing values
    empty_columns = df.columns[df.isna().sum() == len(df)]
    
    # Remove columns with 100% missing values
    df.drop(columns=empty_columns, inplace=True)


# Define function to load data into PostgreSQL through a buffer table with a check for table existence
def write_to_sql_in_chunks(df: pd.core.frame.DataFrame, 
                           table_name: str, 
                           engine: sa.engine.base.Engine, 
                           chunk_size: int=4000) -> None:
    """
    Function to write data to the database in chunks with a check for table existence.
    Args:
        df (pd.core.frame.DataFrame): the name of the DataFrame to write
        table_name (str): the name of the DB table where the data will be written
        engine (sa.engine.base.Engine): database connection
        chunk_size (int): size of the chunks being written
    Returns:
        None: the DataFrame data has been written to the database table
    """
    # Check for the existence of the table in the database
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        for start in range(0, len(df), chunk_size):
            end = start + chunk_size
            df[start:end].to_sql(table_name, con=engine, if_exists='append', index=False)
            print(f'{end} rows out of {len(df)} have been written.')
        print(f'Table {table_name} has been successfully written')
    else:
        print(f'Table {table_name} already exists, writing skipped.')


# Define a function to plot histograms for datasets
def histograms(dataset, name, color, exclude_cols):
    """
    Generates histograms for numerical columns in the provided dataset.

    Args:
        dataset (pd.DataFrame): The DataFrame containing the data for analysis.
        name (str): The name of the dataset, used for the main title.
        color (str): The color of the histograms.
        exclude_cols (list): A list of column names to exclude from the analysis.

    Returns:
        None: Displays histograms for numerical features in the dataset.
    """
    # Select columns that are not bool, object and do not contain only one unique value
    selected_features = [feature for feature in dataset.columns 
                         if feature not in exclude_cols and dataset[feature].dtype not in [bool, object] 
                         and dataset[feature].nunique() > 1]

    # Determine the number of rows and columns dynamically based on the number of selected features
    num_features = len(selected_features)
    num_cols = 2  # two plots per row
    num_rows = (num_features + num_cols - 1) // num_cols  # round up to fit all plots

    # Create a figure with a dynamically determined number of rows
    fig, axes = plt.subplots(nrows=num_rows, ncols=num_cols, figsize=(20, 5 * num_rows))
    
    # Flatten axes to an array, even if there's only one row or column
    axes = axes.flatten() if num_features > 1 else [axes]

    # Visualize data for the selected columns
    for i, feature in enumerate(selected_features):
        ax = axes[i]
        bins_value = min(20, len(dataset[feature].unique()))  # auto-calculate number of bins

        # Plot histogram
        dataset[feature].hist(bins=bins_value, ax=ax, color=color)
        
        # Add median and mean lines
        ax.axvline(dataset[feature].median(), color='r', linestyle='dashed', linewidth=2, label='Медиана')
        ax.axvline(dataset[feature].mean(), color='black', linestyle='solid', linewidth=2, label='Среднее')
        
        # Set title and labels
        ax.set_title(f'Distribution for "{feature}"')
        ax.set_xlabel(feature)
        ax.set_ylabel(f'Frequency for "{feature}"')
        ax.legend()

    # Remove unused axes (if there are more than needed)
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])

    # Overall title and finalize formatting
    plt.suptitle(f'Analysis of dataset "{name}"', y=1.02, fontsize=16)
    sns.despine()
    plt.tight_layout()
    plt.show()


# Define a function to display basic information about the dataset
def display_dataset_info(df):
    """
    Function to output basic information about the dataset, including a sample,
    overall information, and the number of missing values sorted in ascending order.

    Args:
        df (pd.DataFrame): The dataset for analysis.
    """
    # Print overall information about the dataset
    print('Dataset info:')
    display(df.info())
    print()
    
    # Count of missing values
    print('Number of missing values:')
    display(df.isna().sum().sort_values())


# Define a function to determine the segment.
def make_segments(cell: str) -> str:
    'Assigning a client type based on the RFM segment'
    new_cell = ''
    if cell in ['123', '133', '143', '223', '233', '243', '323', '333', '343']:
        new_cell = 'Key clients'
    elif cell in ['112', '122', '113', '213', '214', '232', '312']:
        new_cell = 'Prospective clients'
    elif cell in ['111', '112', '121', '131', '211', '221', '311']:
        new_cell = 'One-time donors'
    elif cell in ['141', '142', '144', '241', '242', '244', '341', '342', '344', '444']:
        new_cell = 'Rarely active'
    elif cell in ['114', '124', '132', '213', '222', '224', '234', '324']:
        new_cell = 'Moderately active'
    elif cell in ['213', '222', '231', '312', '323']:
        new_cell = 'Growth potential clients'
    elif cell in ['221', '311', '321', '322', '331']:
        new_cell = 'Highly active'
    else:
        new_cell = 'Lost clients'
    return new_cell


def rearrange_columns(df):
    """
    Rearranges the columns of a DataFrame by keeping the first two columns in place
    and reversing the order of the remaining columns.

    Parameters:
    df (pd.DataFrame): The DataFrame to be rearranged.

    Returns:
    pd.DataFrame: The modified DataFrame with the first two columns in place and the remaining columns reversed.
    """
    # Selecting the first two columns
    first_two_columns = df.iloc[:, :2]
    
    # Reversing the remaining columns, starting from the third
    reversed_columns = df.iloc[:, 2:].iloc[:, ::-1]
    
    # Merging the first two columns and the reversed columns
    rearranged_df = pd.concat([first_two_columns, reversed_columns], axis=1)
    
    return rearranged_df