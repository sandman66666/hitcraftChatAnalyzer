# HitCraft Chat Analyzer Data Storage Documentation

## Current Storage Implementation

The HitCraft Chat Analyzer uses a file-based storage system for persistence. This approach is simple and works well for development and small-scale deployments, but should be upgraded to a proper database for production environments.

### Storage Locations

Based on the configuration in `config.py`, the application uses these directories:

- **UPLOAD_FOLDER** (`./uploads`): Temporary storage for uploaded files
- **TEMP_FOLDER** (`./temp_chunks`): Stores temporary session data and file chunks
- **RESULTS_FOLDER** (`./analysis_results`): Stores analysis results
- **THREADS_FOLDER** (`./organized_threads`): Stores extracted conversation threads
- **DATA_FOLDER** (`./data`): Stores persistent data like analysis history

### Key Files

The following files contain important persistent data:

1. **Thread Files** (`organized_threads/*.json` and `organized_threads/*.txt`):
   - Individual thread content in JSON or text format
   - Each file is named with a unique thread ID

2. **Analysis History** (`data/analysis_history.json`):
   - Record of which threads have been analyzed
   - Used to track progress and avoid re-analyzing threads
   - Contains metadata about each analysis run

## Production Deployment Options

For a production deployment, you should replace the file-based storage with a proper database. Here are some recommendations:

### 1. MongoDB (Document Database)

MongoDB would be a natural fit since you're already working with JSON data:

```python
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['hitcraft_analyzer']

# Collections
threads_collection = db['threads']
analysis_collection = db['analysis_history']

# Store a thread
def store_thread(thread_data):
    return threads_collection.insert_one(thread_data).inserted_id

# Get a thread
def get_thread(thread_id):
    return threads_collection.find_one({'id': thread_id})

# Store analysis history
def save_analysis_history(analysis_data):
    return analysis_collection.insert_one(analysis_data).inserted_id
```

### 2. PostgreSQL (SQL Database)

For more structured data and advanced querying:

```python
import psycopg2
import json

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="hitcraft",
    user="postgres",
    password="your_password",
    host="localhost"
)

# Create tables (run once)
def create_tables():
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS threads (
                id VARCHAR PRIMARY KEY,
                content JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id SERIAL PRIMARY KEY,
                thread_id VARCHAR REFERENCES threads(id),
                timestamp TIMESTAMP,
                session_id VARCHAR,
                message_count INTEGER
            )
        ''')
    conn.commit()

# Store a thread
def store_thread(thread_id, content):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO threads (id, content) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET content = %s",
            (thread_id, json.dumps(content), json.dumps(content))
        )
    conn.commit()
```

### 3. Cloud-Based Storage (AWS S3, Azure Blob Storage)

For storing thread files as objects:

```python
import boto3

# Connect to S3
s3 = boto3.client('s3',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY'
)
bucket_name = 'hitcraft-analyzer'

# Store a thread
def store_thread_s3(thread_id, content):
    s3.put_object(
        Bucket=bucket_name,
        Key=f'threads/{thread_id}.json',
        Body=json.dumps(content)
    )

# Get a thread
def get_thread_s3(thread_id):
    response = s3.get_object(
        Bucket=bucket_name,
        Key=f'threads/{thread_id}.json'
    )
    return json.loads(response['Body'].read().decode('utf-8'))
```

## Implementation Strategy

To migrate to a production database:

1. **Create a Storage Abstraction Layer**:
   - Define a clear API for thread and analysis storage
   - Implement this API with your current file-based solution
   - Create alternative implementations for your production database

2. **Use Environment Configuration**:
   - Set the storage backend via environment variables
   - Keep file-based storage as a fallback

3. **Migrate Existing Data**:
   - Write a script to move data from files to your production database
   - Validate the migration with checksums or manual verification

4. **Update Deployment Documentation**:
   - Document database requirements
   - Include connection string formats
   - Add security recommendations

The current system is designed in a modular way, primarily through the `thread_storage.py` module, which will make this transition relatively straightforward.
