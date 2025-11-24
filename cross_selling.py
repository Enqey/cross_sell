# -*- coding: utf-8 -*-
"""
Cross-selling Streamlit App
"""

import pandas as pd
import streamlit as st
from itertools import combinations

# -------------------------------
# Load dataset
# -------------------------------
data_url = 'https://raw.githubusercontent.com/Enqey/Recmodel/main/Sdata.csv'  # GitHub raw link
df = pd.read_csv(data_url, parse_dates=['Order Date', 'Ship Date'])

st.title("🛒 Cross-Selling Product Suggestions")
st.write("""
    **Select a product and see what other products are often bought together!**
""")

# -------------------------------
# Filter orders with at least 3 unique products
# -------------------------------
order_counts = df.groupby('Order ID')['Product ID'].nunique()
orders_with_3plus = order_counts[order_counts >= 3].index
df_filtered = df[df['Order ID'].isin(orders_with_3plus)].copy()
df_filtered['date_'] = df_filtered['Order Date'].dt.date

# -------------------------------
# Generate 3-item combinations
# -------------------------------
records = []

for order_id, group in df_filtered.groupby('Order ID'):
    items = group[['Product ID', 'Product Name']].drop_duplicates().values
    if len(items) < 3:
        continue
    for combo in combinations(items, 3):
        records.append({
            'id_order': order_id,
            'date_': group['date_'].iloc[0],
            'item_product_id1': combo[0][0],
            'item_product_id2': combo[1][0],
            'item_product_id3': combo[2][0],
            'product_name1': combo[0][1],
            'product_name2': combo[1][1],
            'product_name3': combo[2][1]
        })

cross_sell_df = pd.DataFrame(records)

# Count frequency
cross_sell_summary = (
    cross_sell_df
    .groupby(['item_product_id1','item_product_id2','item_product_id3',
              'product_name1','product_name2','product_name3'])
    .size()
    .reset_index(name='frequency')
    .sort_values(by='frequency', ascending=False)
)

# -------------------------------
# Sidebar for product selection
# -------------------------------
product_names = pd.unique(df['Product Name'])
selected_product = st.sidebar.selectbox("Select a product:", product_names)

# -------------------------------
# Show cross-selling suggestions
# -------------------------------
if selected_product:
    st.subheader(f"Products frequently bought with: {selected_product}")

    # Filter all combinations that contain the selected product
    mask = (
        (cross_sell_summary['product_name1'] == selected_product) |
        (cross_sell_summary['product_name2'] == selected_product) |
        (cross_sell_summary['product_name3'] == selected_product)
    )

    suggestions = cross_sell_summary[mask].copy()

    # Extract the other products in the combination
    def get_other_products(row, selected):
        return [p for p in [row['product_name1'], row['product_name2'], row['product_name3']] if p != selected]

    suggestions['cross_sell_products'] = suggestions.apply(lambda row: get_other_products(row, selected_product), axis=1)

    # Aggregate by frequency
    final_suggestions = (
        suggestions.explode('cross_sell_products')
        .groupby('cross_sell_products')['frequency']
        .sum()
        .reset_index()
        .sort_values(by='frequency', ascending=False)
    )

    if not final_suggestions.empty:
        for idx, row in final_suggestions.iterrows():
            st.write(f"{row['cross_sell_products']} (bought together {row['frequency']} times)")
    else:
        st.write("No cross-selling suggestions found.")

st.write("---")
st.write("**Developed by Nana Ekow Okusu**")
