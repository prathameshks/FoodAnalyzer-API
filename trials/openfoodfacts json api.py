import json

def extract_product_info(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    product = data.get('product', {})

    print(f"Product Name: {product.get('product_name_en', product.get('product_name', 'N/A'))}")
    print(f"Generic Name: {product.get('generic_name_en', product.get('generic_name', 'N/A'))}")
    print(f"Brands: {product.get('brands', 'N/A')}")

    # Extract and print all ingredients
    ingredients_list = product.get('ingredients', [])
    if ingredients_list:
        print("\nIngredients:")
        for ingredient in ingredients_list:
           
            text = ingredient.get('text', 'N/A')
            percent = ingredient.get('percent', ingredient.get('percent_estimate', 'N/A'))
            vegan = ingredient.get('vegan', 'N/A')
            vegetarian = ingredient.get('vegetarian', 'N/A')
            print(f"  - {text} ({percent}%)  Vegan: {vegan}, Vegetarian: {vegetarian}")
            
            sub_ingredients = ingredient.get('ingredients', [])
            if sub_ingredients:
                 for sub_ingredient in sub_ingredients:
                       sub_text = sub_ingredient.get('text', 'N/A')
                       sub_percent = sub_ingredient.get('percent', sub_ingredient.get('percent_estimate', 'N/A'))
                       sub_vegan = sub_ingredient.get('vegan', 'N/A')
                       sub_vegetarian = sub_ingredient.get('vegetarian', 'N/A')

                       print(f"    -- {sub_text} ({sub_percent}%) Vegan: {sub_vegan}, Vegetarian: {sub_vegetarian}")

    ingredients_text = product.get('ingredients_text_en', product.get('ingredients_text', 'N/A'))
    print(f"\nIngredients Text: {ingredients_text}")

    ingredients_analysis = product.get('ingredients_analysis',{})
    if ingredients_analysis:
        print("\nIngredients Analysis:")
        for key, value in ingredients_analysis.items():
            print(f"  - {key} : {value}")
            
    # Extract and print nutriscore data
    nutriscore = product.get('nutriscore', {})
    if nutriscore:
        for year, score_data in nutriscore.items():
           grade = score_data.get('grade', 'N/A')
           if(grade != 'N/A'):
              print(f"\nNutriscore ({year}): Grade: {grade}")
              data = score_data.get('data',{})
              if(data):
                print(" Nutriscore Data: ")
                for key, value in data.items():
                    print(f"    - {key} : {value}")

    # Extract and print nutrient levels
    nutrient_levels = product.get('nutrient_levels', {})
    if nutrient_levels:
        print("\nNutrient Levels:")
        for key, value in nutrient_levels.items():
            print(f"  - {key}: {value}")
            

    # Extract and print nutriments data
    nutriments = product.get('nutriments', {})
    if nutriments:
         print("\nNutriments:")
         for key, value in nutriments.items():
               if "_100g" in key:
                  print(f"   - {key} : {value}")

    # Extract and print data quality warnings
    data_quality_warnings = product.get('data_quality_warnings_tags', [])
    if data_quality_warnings:
        print("\nData Quality Warnings:")
        for warning in data_quality_warnings:
            print(f"  - {warning}")

# Example usage:
file_paths = ["Balaji Wheels.txt", "Dairy Milk.txt", "Kisan Jam.txt", "Kisan Tamato Ketchup.txt", "Maggie.txt"] # Add all your file paths here
for file_path in file_paths:
    print(f"\n--- Processing: {file_path} ---")
    extract_product_info("v2/txt/" + file_path)