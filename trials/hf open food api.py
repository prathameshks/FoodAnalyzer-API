import duckdb

# jamescalam/world-cities-geo/train.jsonl
# /datasets/
# # to start an in-memory database
# con = duckdb.connect(database = "hf://datasets/openfoodfacts/product-database")

# create a table
rel = duckdb.sql("SELECT * FROM 'hf://datasets/openfoodfacts/product-database/food.parquet' limit 2;")
rel.show()
# ('hammer', Decimal('42.20'), 2)
# print(con.fetchone()) # This closes the transaction. Any subsequent calls to .fetchone will return None
# None