import pandas as pd

df = pd.read_csv('./data/out.csv', usecols=range(8))

df_sorted = df.sort_values(by=['recitation instructor', 'recitation time', 'tutorial time'])

df_sorted.to_csv("./data/out_sorted.csv", index=False)

print("Filtered data saved to out_sorted.csv")
