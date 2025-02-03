import pandas as pd
import csv

with open('./data/out.csv', mode='r', newline='') as infile:
    reader = csv.reader(infile)
    rows = list(reader)

# Edit first row to have better column names
rows[0] = ["email", "recitation instructor", "recitation time", "tutorial instructor", "tutorial time", "teammate1", "teammate2", "teammate3"]

# Save
with open('./data/out.csv', mode='w', newline='') as outfile:
    writer = csv.writer(outfile)
    writer.writerows(rows)


df = pd.read_csv('./data/out.csv')

df_sorted = df.sort_values(by=['recitation instructor', 'recitation time', 'tutorial time'])

df_sorted.to_csv("./data/out_sorted.csv", index=False)

print("Filtered data saved to out_sorted.csv")
