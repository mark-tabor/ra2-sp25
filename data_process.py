import pandas as pd

df = pd.read_csv("./data/raw_data.csv")

df.columns = df.columns.str.strip()

df = df.dropna(subset=["Your Kerberos", "Timestamp"])

# Fix kerbs given as emails
df['Email Address'] = df['Email Address'].str.replace('@mit.edu', '', regex=False)

# Take most recent submission
df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%m/%d/%Y %H:%M:%S", errors="coerce")
df = df.dropna(subset=["Timestamp"])
df_filtered = df.loc[df.groupby("Your Kerberos")["Timestamp"].idxmax()]

df_filtered.to_csv("./data/filtered_data.csv", index=False)

print("Filtered data saved to filtered_data.csv")
