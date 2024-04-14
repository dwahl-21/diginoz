import sqlite3 as sql

if __name__ == "__main__":
    with sql.connect("diginoz.db") as conn:
        cursor = conn.cursor()

        # Create table containing file path and content as SHA256 hashes
        # cursor.execute("CREATE TABLE files (id INTEGER PRIMARY KEY AUTOINCREMENT, pathHash varchar(64), path varchar(256), fileHash varchar(64), tags varchar(512));")
        
        # Clean Database
        # cursor.execute("DELETE FROM files WHERE id=null;")

        cursor.close()
        conn.commit()