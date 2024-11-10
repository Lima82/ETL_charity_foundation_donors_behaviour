# Data analysis for the "AiF. Kind Heart" charitable foundation aimed at improving the effectiveness of user engagement.

## Client: charitable foundation (non-profit organization).

## Project Outcome

The project output includes the following files:

  - load_script.py: Loads data from disk into a local directory, transforms it, creates a SQLite database, and loads the transformed datasets into the database;
  - some_functions.py: A file containing functions required for analysis;
  - sqls_scripts.py: A file with SQL scripts required for analysis;
  - analysis.ipynb: A notebook with data analysis and visualizations;
  - requirements.txt: Lists the modules needed to run the scripts;
  - dashboard using DataLens BI.

## Dashboard

https://datalens.yandex/zb3dudu6pc74m

## Data

- table customers.csv (information about users):
  - user action identifier;
  - system name of the user action template;
  - name of the user action template;
  - date and time of the user action;
  - creation date and time of the user action;
  - brand name (Dobro AiF);
  - channel ID;
  - channel name;
  - external channel ID;
  - system name of the channel;
  - UTM campaign tag;
  - UTM source;
  - UTM medium;
  - UTM content;
  - UTM term;
  - backend identifier;
  - website identifier;
  - user identifier (foreign key).
- table orders.csv (information about donations):
  - identifier;
  - first action identifier;
  - date and time of the first action;
  - channel ID;
  - external channel ID;
  - location ID;
  - transaction ID;
  - delivery cost;
  - channel name;
  - total order price;
  - backend identifier;
  - website identifier;
  - participation in the "New Year" campaign;
  - next payment date (for subscription);
  - recurrent or not (subscriber);
  - whether the user made a repeat payment;
  - product identifier;
  - product name;
  - number of items;
  - item price;
  - line price;
  - payment status;
  - gift card amount;
  - system name of the gift card status;
  - line number;
  - line ID;
  - backend user identifier;
  - website user identifier;
  - user identifier (foreign key).
    
## Format

The project is executed in an ETL format (Extract, Transform, Load), a process commonly used for data integration where data is extracted from various sources, transformed into a suitable format, and then loaded into a target database or system.

## Research Goal

The objectives are as follows:
  - Analyze user behavior;
  - Calculate metrics: user, marketing, and commercial;
  - Segment users through RFM analysis and describe segments;
  - Conduct cohort analysis (RR, LTV, AC).

## Recommendations for the client
  - Pay attention to the incorrect distribution of data in the OrderLineProductName and OrderLineProductIdsWebsite columns;
  - Monitor unpaid orders; if a user adds a product to their cart but does not complete the payment, consider setting up reminder emails for abandoned carts. It is important to engage with these users, as the amounts of unpaid orders exceed the annual collections;
  - Continue working on New Year promotions to attract additional funds from users. The analysis showed a good response from new users to these promotions;
  - Develop acquisition channels such as yandex-direct, aif_gazeta, and mtsmarketolog. These channels bring in users who donate larger amounts compared to VK;
  - Try to reactivate historical users, as there are many significant donors among them.

## Technical skills
*Python, Pandas, Os, Numpy, Ydata Profiling, Ipywidgets, Yadisk, Importlib, Sys, Tqdm, Re, Shutil, Matplotlib, Seaborn, Datetime, Itertools, IPython, Warnings, Sqlalchemy, SQLite3, DBeaver, PostgreSQL, DataLens*
