# api_cross_sell.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
from itertools import combinations

# -------------------------------
# Load dataset safely
# -------------------------------
data_url = 'https://raw.githubusercontent.com/Enqey/cross_sell/main/Sdata.csv'

try:
    df = pd.read_csv(data_url, parse_dates=['Order Date', 'Ship Date'])
except Exception as e:
    print("ERROR LOADING CSV:", e)
    df = pd.DataFrame()  # empty fallback

cross_sell_summary = pd.DataFrame()  # predefine

if not df.empty:
    # Filter orders with at least 3 unique products
    order_counts = df.groupby('Order ID')['Product ID'].nunique()
    orders_with_3plus = order_counts[order_counts >= 3].index
    df_filtered = df[df['Order ID'].isin(orders_with_3plus)].copy()
    df_filtered['date_'] = df_filtered['Order Date'].dt.date

    # Generate 3-item combinations
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

    if not cross_sell_df.empty:
        cross_sell_summary = (
            cross_sell_df
            .groupby(['item_product_id1', 'item_product_id2', 'item_product_id3',
                      'product_name1', 'product_name2', 'product_name3'])
            .size()
            .reset_index(name='frequency')
            .sort_values(by='frequency', ascending=False)
        )

# -------------------------------
# FastAPI app
# -------------------------------
app = FastAPI(title="Cross-Selling API")

class ProductRequest(BaseModel):
    product_name: str

def get_cross_sell_suggestions(selected_product: str):
    if cross_sell_summary.empty:
        return []

    mask = (
        (cross_sell_summary['product_name1'] == selected_product) |
        (cross_sell_summary['product_name2'] == selected_product) |
        (cross_sell_summary['product_name3'] == selected_product)
    )

    suggestions = cross_sell_summary[mask].copy()
    if suggestions.empty:
        return []

    def get_other_products(row):
        return [p for p in [row['product_name1'], row['product_name2'], row['product_name3']]
                if p != selected_product]

    suggestions['cross_sell_products'] = suggestions.apply(get_other_products, axis=1)
    
    final_suggestions = (
        suggestions.explode('cross_sell_products')
        .groupby('cross_sell_products')['frequency']
        .sum()
        .reset_index()
        .sort_values(by='frequency', ascending=False)
    )
    
    return final_suggestions.to_dict(orient='records')

@app.get("/")
def root():
    return {"message": "Welcome to Cross-Selling API. Use /suggest endpoint."}

@app.post("/suggest")
def suggest(request: ProductRequest):
    suggestions = get_cross_sell_suggestions(request.product_name)
    if not suggestions:
        raise HTTPException(status_code=404, detail="No cross-selling suggestions found for this product")
    return {"product": request.product_name, "suggestions": suggestions}
