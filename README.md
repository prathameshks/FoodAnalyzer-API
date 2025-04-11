# FoodAnalyzer-API

## Installation and Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/prathameshks/FoodAnalyzer-API.git
   ```

2. **Navigate to the project directory**:
   ```bash
   cd FoodAnalyzer-API
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

6. **Set up environment variables**:
   Copy the `.env.example` file to `.env` and fill in the required values, including API keys for Hugging Face Transformers.

7. **Run the application**:
   ```bash
   uvicorn main:app --reload
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register`: Register a new user.
- `POST /api/auth/login`: Login and obtain an access token.
- `GET /api/auth/user`: Get the current user's information.

### Ingredient Analysis
- `POST /api/analyze/analyze_ingredients`: Analyze a list of ingredients.
- `GET /api/analyze/personalized_recommendations`: Get personalized ingredient recommendations.

### Scan History
- `POST /api/history/scan`: Record a new scan.
- `GET /api/history/scan/{user_id}`: Retrieve the scan history for a user.

<!-- ### Product Data
- `GET /api/extract_product_info`: Extract product information from a barcode.
- `POST /api/fetch_product_data`: Fetch product data for a list of barcodes. -->


## Alembic migrations

### To create a new migration, run the following command:
```bash
alembic init migrations
```

### To generate a new migration file, run:
```bash
alembic revision --autogenerate -m "Message"
```

### To apply the migration, run:
```bash
alembic upgrade head
```

### To downgrade the migration, run:
```bash
alembic downgrade -1
```

### To view the current migration version, run:
```bash
alembic current
```