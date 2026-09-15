"""
This is like the other script ('cleaning_ecommerce_data.py") but modular - that way functions can be called from quarto as opposed to big chunks of code.

----- Changes: -----
1. Renamed the dataframe so that the code is easier to read
2. More clarity in the code explanation
3. Code has been turned into functions 

"""

# Import scripts
import numpy as np
import pandas as pd


# Read in the data, convert to parquet and read the parquet file as smaller size
#online_retail = pd.read_csv("data/data.csv", sep=",", encoding="ISO-8859-1", header=0)
#online_retail = online_retail.to_parquet("data/OnlineRetail.parquet", compression="snappy")
online_retail = pd.read_parquet("../data_dcp/OnlineRetail.parquet")
# Check data
#print(online_retail.head())

# Get basic information on the dataframe
def dataframe_info():
    # Get the shape of the dataframe - the number of rows and columns, respectively
    print(f"The dataset has {online_retail.shape[0]} rows and {online_retail.shape[1]} columns.")

    # Get the information on the columns of the dataframe
    print("Columns of the dataframe and associated data types:")
    print(online_retail.info())

    # Get the basic statistics
    print("\nBasic statistics of the data frame:")
    print(online_retail.describe())

# Call the function with the basic information
#dataframe_info()


# Start cleaning - define a function to clean the data

def clean_data(online_retail: pd.DataFrame) -> pd.DataFrame:
    
    # Drop all the rows that contain empty values
    online_retail = online_retail.dropna().copy()
    #print(online_retail.shape)

    # Format date strings into datetime UTC
    online_retail["InvoiceDate"] = pd.to_datetime(
        online_retail["InvoiceDate"], 
        format="mixed", 
        errors="coerce"
    )
    online_retail = online_retail[online_retail["InvoiceDate"].notna()].copy()
    print('Format date strings into datetime')
    online_retail.info()

    # Remove the whitespace:
    str_cols = ["InvoiceNo", "StockCode", "Description", "Country"]
    for col in str_cols:
        if col in online_retail.columns:
            online_retail.loc[:,col] = online_retail[col].astype(str).str.strip()


    return online_retail

# Pass the result of the function back as step 1 - Further steps will contain further cleaning
df_step_1 = clean_data(online_retail)
#print(df_step_1.shape)

# Function to remove rows with cancelled transactions (InvoiceNo starting with 'C')
def cancelled_transactions(df_step_1):
    df_step_1["IsCancelled"] = df_step_1["InvoiceNo"].str.startswith("C", na=False)
    df_step_1 = df_step_1[~df_step_1["IsCancelled"]].drop(columns=["IsCancelled"])
    print(f"After dropping cancellations: {len(df_step_1):,} rows")
    return df_step_1

# So any function from here on has cancelled invoices removed.
df_step_2 = cancelled_transactions(df_step_1)


# Retail items in the UK typically have 5 digits - so look for codes that don't start with a digit, ie are non-numeric
# After the codes and occurences are found, remove from the dataframe
def clean_StockCode(df_step_2):
    stock_codes_non_numeric_mask = df_step_2['StockCode'].astype(str).str[0].str.isdigit() == False
    #df_step_2 = stock_codes_non_numeric_mask

    # create a summary of the non-numeric stock codes:
    non_numeric_stock_codes = (df_step_2[stock_codes_non_numeric_mask]
    .groupby(['StockCode', 'Description'])
    .size()
    .reset_index(name='OccurrenceCount')
    .sort_values(by='OccurrenceCount', ascending=False))

    # NB - Should print as a table - check the render in Quarto
    print(non_numeric_stock_codes)

    # Now remove non-numeric stock codes as this could artificially inflate sales counts 
    # or skew market basket analysis
    # convert to list
    non_numeric_stock_codes_list = non_numeric_stock_codes['StockCode'].tolist()
    print(non_numeric_stock_codes_list)

    # Remove by using 'NOT' logic
    df_step_2 = df_step_2[~df_step_2["StockCode"].isin(non_numeric_stock_codes_list)]

    print(f"After removing the non-numeric stock codes: {len(df_step_2):,} rows")
    return (df_step_2)

df_step_3 = clean_StockCode(df_step_2)

def clean_quantities_and_prices(df_step_3):
    # Remove out non-positive quantities and prices
    # Checks every row in the 'Quantity' column and returns True if count > 0 and False if 0 or negative
    # Checks every row in the 'UnitPrice' column and returns True if the price > 0 and False if 0 or negative
    # Using the AND operator to only get True values
    df_step_3 = df_step_3[(df_step_3["Quantity"] > 0) & (df_step_3["UnitPrice"] > 0.0)]
    print(f"After removing non-positive quantities and prices: {len(df_step_3):,} rows")

    return(df_step_3)

df_step_4 = clean_quantities_and_prices(df_step_3)

# One of the final steps is to export the cleaned version to parquet 
df_step_4 = df_step_4.to_parquet("../data_dcp/clean_online_retail.parquet")

cleaned_retail = pd.read_parquet("../data_dcp/clean_online_retail.parquet")

# Next step is to compare starting and finishing data in a tabular format
# 1. read in clean data --
# 2. start generating the function for the table
# 3. Call the function to test

def generate_data_audit(online_retail, cleaned_retail):
    audit_data =[
        {
            "Metric": "Total Rows",
            "Raw State": f"{len(online_retail):,}",
            "Cleaned State": f"{len(cleaned_retail):,}",
            "Impact": f"-{len(online_retail) - len(cleaned_retail):,} rows removed"
        },
        {
            "Metric": "Unique Stock Codes",
            "Raw State": f"{online_retail['StockCode'].nunique():,}",
            "Cleaned State": f"{cleaned_retail['StockCode'].nunique():,}",
            "Impact": "Non-inventory stock codes removed (POST, D, etc.)"
        },
        {
            "Metric": "Cancelled Invoices ('C')",
            "Raw State": f"{online_retail['InvoiceNo'].str.startswith('C', na=False).sum():,}",
            "Cleaned State": f"{cleaned_retail['InvoiceNo'].str.startswith('C', na=False).sum():,}",
            "Impact": "Isolated to prevent negative revenue distortion"
        },
        {
            "Metric": "Zero / Negative Unit Prices",
            "Raw State": f"{(online_retail['UnitPrice'] <= 0).sum():,}",
            "Cleaned State": f"{(cleaned_retail['UnitPrice'] <= 0).sum():,}",
            "Impact": "Price anomalies and bad entries removed"
        }

    ]
    return (audit_data)

audit_table = generate_data_audit(online_retail, cleaned_retail)
print(audit_table)