#!/usr/bin/env python
import sqlite3

# Check tenant database
print("Checking databases...")
try:
    conn = sqlite3.connect('tenant_databases/db_sos-herman-gmeiner-school.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    tenant_tables = cursor.fetchone()[0]
    print(f'Tenant database tables: {tenant_tables}')
    
    if tenant_tables > 0:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f'  Tables: {", ".join(tables[:5])}...')
    conn.close()
except Exception as e:
    print(f'Error checking tenant database: {e}')

# Check default database
try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    default_tables = cursor.fetchone()[0]
    print(f'Default database tables: {default_tables}')
    
    if default_tables > 0:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f'  Tables: {", ".join(tables[:5])}...')
    conn.close()
except Exception as e:
    print(f'Error checking default database: {e}')
