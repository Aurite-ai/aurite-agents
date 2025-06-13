import pandas as pd
import csv

# Read the CSV file into a pandas DataFrame, specifying the quote character
# to handle commas within the comment fields properly.
csv_file = "comparison-sheet.csv"
df = pd.read_csv(csv_file, quotechar='"', quoting=csv.QUOTE_ALL, skipinitialspace=True)

# Write the DataFrame to an Excel file
excel_file = "comparison-sheet.xlsx"
df.to_excel(excel_file, index=False)

print(f"Successfully converted '{csv_file}' to '{excel_file}'")
