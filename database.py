import sqlite3

DB_PATH = 'company.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 帰社日スケジュールテーブル
    cursor.execute('''CREATE TABLE IF NOT EXISTS schedules 
                      (dept TEXT, date_time TEXT)''')
    # メンバー所属テーブル
    cursor.execute('''CREATE TABLE IF NOT EXISTS members 
                      (name TEXT, dept TEXT)''')
    conn.commit()
    conn.close()

def get_member_schedule(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # メンバーの所属を特定し、その課の全スケジュールを取得
    cursor.execute('''SELECT m.dept, s.date_time 
                      FROM members m 
                      JOIN schedules s ON m.dept = s.dept 
                      WHERE m.name = ?''', (name,))
    results = cursor.fetchall()
    conn.close()
    return results
