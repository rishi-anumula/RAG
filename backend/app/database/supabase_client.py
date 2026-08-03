import os
import uuid
import json
import sqlite3
from datetime import datetime
from app.core.config import settings
from app.core.logging_config import get_logger
from supabase import create_client, Client

logger = get_logger(__name__)

def init_local_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        created_at TEXT
    )
    """)
    
    # Create documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        name TEXT,
        size INTEGER,
        status TEXT,
        storage_path TEXT,
        error_message TEXT,
        chunk_count INTEGER,
        created_at TEXT
    )
    """)
    
    # Create conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    
    # Create messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        user_id TEXT,
        role TEXT,
        content TEXT,
        citations TEXT,
        sources TEXT,
        feedback TEXT,
        created_at TEXT
    )
    """)
    
    # Create document_chunks table for local SQLite pgvector mock fallback
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT,
        user_id TEXT,
        filename TEXT,
        page_number INTEGER,
        chunk_number INTEGER,
        content TEXT,
        embedding TEXT,
        created_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

class MockTableBuilder:
    def __init__(self, db_path, table_name):
        self.db_path = db_path
        self.table_name = table_name
        self.filters = {}
        self.order_by = None
        self.limit_val = None
        self.action = "select"  # "select", "insert", "update", "delete"
        self.action_payload = None

    def select(self, *columns, **kwargs):
        self.action = "select"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def order(self, column, desc=False, ascending=True):
        is_desc = desc or not ascending
        self.order_by = (column, not is_desc)
        return self

    def limit(self, val):
        self.limit_val = val
        return self

    def insert(self, payload):
        self.action = "insert"
        self.action_payload = payload
        return self

    def update(self, payload):
        self.action = "update"
        self.action_payload = payload
        return self

    def delete(self):
        self.action = "delete"
        return self

    def execute(self):
        if self.action == "select":
            return self._execute_select()
        elif self.action == "insert":
            return self._execute_insert()
        elif self.action == "update":
            return self._execute_update()
        elif self.action == "delete":
            return self._execute_delete()
        else:
            raise ValueError(f"Unknown action: {self.action}")

    def _execute_select(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {self.table_name}"
        params = []
        if self.filters:
            where_clauses = [f"{col} = ?" for col in self.filters.keys()]
            query += " WHERE " + " AND ".join(where_clauses)
            params = list(self.filters.values())
            
        if self.order_by:
            col, asc = self.order_by
            query += f" ORDER BY {col} {'ASC' if asc else 'DESC'}"
            
        if self.limit_val is not None:
            query += f" LIMIT {self.limit_val}"
            
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            data = []
            for r in rows:
                d = dict(r)
                # Parse JSON fields
                for json_col in ["citations", "sources"]:
                    if json_col in d and d[json_col]:
                        try:
                            d[json_col] = json.loads(d[json_col])
                        except Exception:
                            pass
                data.append(d)
            
            class MockResponse:
                def __init__(self, data):
                    self.data = data
            return MockResponse(data)
        finally:
            conn.close()

    def _execute_insert(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        payload = self.action_payload
        if isinstance(payload, list):
            payloads = payload
        else:
            payloads = [payload]
            
        inserted_rows = []
        try:
            for p in payloads:
                item = p.copy()
                if "id" not in item:
                    item["id"] = str(uuid.uuid4())
                if "created_at" not in item:
                    item["created_at"] = datetime.utcnow().isoformat() + "Z"
                if "updated_at" not in item and self.table_name == "conversations":
                    item["updated_at"] = item["created_at"]
                    
                # Encode JSON fields
                for json_col in ["citations", "sources"]:
                    if json_col in item and isinstance(item[json_col], (dict, list)):
                        item[json_col] = json.dumps(item[json_col])
                        
                cols = list(item.keys())
                vals = list(item.values())
                placeholders = ["?"] * len(cols)
                
                query = f"INSERT OR REPLACE INTO {self.table_name} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, vals)
                
                # Decode JSON fields back
                for json_col in ["citations", "sources"]:
                    if json_col in item and isinstance(item[json_col], str):
                        try:
                            item[json_col] = json.loads(item[json_col])
                        except Exception:
                            pass
                inserted_rows.append(item)
            conn.commit()
            
            class MockResponse:
                def __init__(self, data):
                    self.data = data
            return MockResponse(inserted_rows)
        finally:
            conn.close()

    def _execute_update(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            item = self.action_payload.copy()
            if "updated_at" not in item and self.table_name == "conversations":
                item["updated_at"] = datetime.utcnow().isoformat() + "Z"
                
            for json_col in ["citations", "sources"]:
                if json_col in item and isinstance(item[json_col], (dict, list)):
                    item[json_col] = json.dumps(item[json_col])
                    
            set_clauses = [f"{col} = ?" for col in item.keys()]
            query = f"UPDATE {self.table_name} SET {', '.join(set_clauses)}"
            params = list(item.values())
            
            if self.filters:
                where_clauses = [f"{col} = ?" for col in self.filters.keys()]
                query += " WHERE " + " AND ".join(where_clauses)
                params.extend(self.filters.values())
                
            cursor.execute(query, params)
            conn.commit()
            
            class MockResponse:
                def __init__(self, data):
                    self.data = []
            return MockResponse([])
        finally:
            conn.close()

    def _execute_delete(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            query = f"DELETE FROM {self.table_name}"
            params = []
            if self.filters:
                where_clauses = [f"{col} = ?" for col in self.filters.keys()]
                query += " WHERE " + " AND ".join(where_clauses)
                params = list(self.filters.values())
                
            cursor.execute(query, params)
            conn.commit()
            
            class MockResponse:
                def __init__(self, data):
                    self.data = []
            return MockResponse([])
        finally:
            conn.close()

class MockStorageBucket:
    def upload(self, path, file, file_options=None):
        return {"path": path}

    def remove(self, paths):
        return {"paths": paths}

    def download(self, path):
        parts = path.split("/")
        if len(parts) >= 2:
            filename = parts[-1]
            user_id = parts[0]
            local_path = os.path.join(settings.UPLOAD_FOLDER, user_id, filename)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    return f.read()
        return b""

class MockStorage:
    def from_(self, bucket_name):
        return MockStorageBucket()

class MockUserObj:
    def __init__(self, id: str, email: str):
        self.id = id
        self.email = email

class MockSessionObj:
    def __init__(self, user_id: str, email: str):
        self.access_token = f"{user_id}:{email}"
        self.refresh_token = "mock-refresh-token"
        self.expires_in = 3600
        self.expires_at = int(datetime.utcnow().timestamp()) + 3600

class MockAuthResponse:
    def __init__(self, user: MockUserObj, session: MockSessionObj = None):
        self.user = user
        self.session = session

class MockAuth:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def sign_up(self, credentials: dict) -> MockAuthResponse:
        email = credentials.get("email")
        password = credentials.get("password")
        if not email or not password:
            raise ValueError("Email and password are required")
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                raise Exception("User already registered")
            
            user_id = str(uuid.uuid4())
            created_at = datetime.utcnow().isoformat() + "Z"
            cursor.execute(
                "INSERT INTO users (id, email, password, created_at) VALUES (?, ?, ?, ?)",
                (user_id, email, password, created_at)
            )
            conn.commit()
            
            user = MockUserObj(user_id, email)
            session = MockSessionObj(user_id, email)
            return MockAuthResponse(user, session)
        finally:
            conn.close()

    def sign_in_with_password(self, credentials: dict) -> MockAuthResponse:
        email = credentials.get("email")
        password = credentials.get("password")
        if not email or not password:
            raise ValueError("Email and password are required")
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, password FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if not row or row[1] != password:
                raise Exception("Invalid email or password")
            
            user_id = row[0]
            user = MockUserObj(user_id, email)
            session = MockSessionObj(user_id, email)
            return MockAuthResponse(user, session)
        finally:
            conn.close()

    def reset_password_for_email(self, email: str):
        class ResetResponse:
            pass
        return ResetResponse()

class MockSupabaseClient:
    def __init__(self):
        # Create database file under the designated uploads folder or /tmp
        db_dir = settings.UPLOAD_FOLDER
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            db_dir = "/tmp"
            os.makedirs(db_dir, exist_ok=True)
            
        self.db_path = os.path.join(db_dir, "local_database.db")
        self.storage = MockStorage()
        try:
            init_local_db(self.db_path)
        except Exception as e:
            logger.warning(f"Could not initialize local SQLite database: {e}")
        self.auth = MockAuth(self.db_path)

    def table(self, table_name):
        return MockTableBuilder(self.db_path, table_name)

# Instantiation
mock_client = MockSupabaseClient()
supabase_anon = mock_client
supabase_service = mock_client

def get_supabase_client(use_service_role: bool = True) -> Client:
    """
    Returns the appropriate Supabase client. If Supabase credentials are not provided,
    falls back to the SQLite Mock client to allow offline testing and execution.
    """
    url_valid = bool(
        settings.SUPABASE_URL 
        and (settings.SUPABASE_URL.startswith("http://") or settings.SUPABASE_URL.startswith("https://"))
    )
    has_keys = bool(settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)
    
    if not (url_valid and has_keys):
        return mock_client
        
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY if (use_service_role and settings.SUPABASE_SERVICE_ROLE_KEY) else (settings.SUPABASE_ANON_KEY or settings.SUPABASE_SERVICE_ROLE_KEY)
        
    # Return real Supabase Cloud client with service_role / anon key
    return create_client(url, key)

import concurrent.futures

def safe_supabase_query(query_fn, fallback_fn=None, timeout_seconds=4.0):
    """
    Executes a primary Supabase Cloud query with a strict timeout.
    If the query fails or exceeds timeout, falls back to fallback_fn (e.g. SQLite mock DB).
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(query_fn)
            return future.result(timeout=timeout_seconds)
    except Exception as e:
        logger.warning(f"Primary Supabase query failed or timed out ({e}). Attempting fallback...")
        if fallback_fn:
            try:
                return fallback_fn()
            except Exception as fb_err:
                logger.error(f"Fallback query execution failed: {fb_err}")
                raise fb_err
        raise e

