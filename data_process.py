import pandas as pd

df = pd.read_csv("./data/raw_data.csv")

df.columns = df.columns.str.strip()

df = df.dropna(subset=["Your Kerberos", "Timestamp"])

# Clean kerberos
df['Your Kerberos'] = df['Your Kerberos'].str.replace('@mit.edu', '', regex=False)

# Add email to sheet
df['Email Address'] = df['Your Kerberos'] + '@mit.edu'

# Reorganize column ordering
new_order = ["Timestamp", "Email Address", "Your Kerberos", "Name", "Times That You Are Available For Recitations", 
             "1st Preference for Recitation Times", "2nd Preference for Recitation Times", 
             "Times That You Are Available for Tutorials", "1st Preference for Tutorial Time", 
             "Team Member 1 MIT Kerberos", "Team Member 1 Name", "Team Member 2 MIT Kerberos", "Team Member 2 Name"
]
df = df[new_order]


# Take most recent submission
df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%m/%d/%Y %H:%M:%S", errors="coerce")
df = df.dropna(subset=["Timestamp"])
df_filtered = df.loc[df.groupby("Your Kerberos")["Timestamp"].idxmax()]

# Save
df_filtered.to_csv("./data/filtered_data.csv", index=False)

print("Filtered data saved to filtered_data.csv")
