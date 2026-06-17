import psycopg2
import sys

# Force UTF-8 stdout for Windows
sys.stdout.reconfigure(encoding='utf-8')

passes = 'Morijin3012'
ref = 'vfikgarwtzipevwpojuq'

configs = [
    # 1. Direct 
    {'host': f'db.{ref}.supabase.co', 'port': 5432, 'user': 'postgres', 'password': passes, 'dbname': 'postgres', 'sslmode': 'require'},
    # 2. Pooler 6543 (Transaction)
    {'host': 'aws-0-ap-southeast-1.pooler.supabase.com', 'port': 6543, 'user': f'postgres.{ref}', 'password': passes, 'dbname': 'postgres', 'sslmode': 'require'},
    # 3. Pooler 5432 (Session)
    {'host': 'aws-0-ap-southeast-1.pooler.supabase.com', 'port': 5432, 'user': f'postgres.{ref}', 'password': passes, 'dbname': 'postgres', 'sslmode': 'require'},
    # 4. Fallback options
    {'host': 'aws-0-ap-southeast-1.pooler.supabase.com', 'port': 5432, 'user': f'postgres.{ref}', 'password': passes, 'dbname': 'postgres'}
]

for i, c in enumerate(configs):
    print(f"\\n[Testing Config {i+1}] host={c.get('host')} port={c.get('port')} user={c.get('user')}")
    try:
        conn = psycopg2.connect(**c, connect_timeout=5)
        print("SUCCESS")
        conn.close()
    except Exception as e:
        print(f"FAILED: {str(e).strip()[:100]}...")
