import pandas as pd
df = pd.read_csv("data/processed/master_citizens.csv")
names = df['canonical_name'].dropna()
sana_names = names[names.str.contains("صنا|ثنا|ملک|sana|malik", case=False, na=False)]
print("Found names:", sana_names.unique()[:20])
