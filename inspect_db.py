import sqlite3
con = sqlite3.connect('debugai.db')
cur = con.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
for row in cur.fetchall():
    print(row[1])
    print()
