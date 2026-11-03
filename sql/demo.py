# -*- coding: utf-8 -*-
"""演示 sql/basic_queries.sql：现场建一张合成小表并逐条执行。

不需要任何真实数据，任何人 clone 下来都能直接跑：
    python sql/demo.py
"""
import os
import sqlite3
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SQL_FILE = os.path.join(HERE, "basic_queries.sql")


def build_demo_db(path):
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE images (
            image_id INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            split    TEXT NOT NULL,
            width    INTEGER,
            height   INTEGER
        );
        CREATE TABLE shapes (
            shape_id INTEGER PRIMARY KEY,
            image_id INTEGER NOT NULL,
            label    TEXT NOT NULL,
            FOREIGN KEY (image_id) REFERENCES images(image_id)
        );
    """)
    images = [
        (1, "001.jpg", "Train", 320, 240),
        (2, "002.jpg", "Train", 640, 480),
        (3, "003.jpg", "Train", 320, 240),
        (4, "004.jpg", "Test", 512, 512),
        (5, "005.jpg", "Test", 320, 240),
    ]
    con.executemany("INSERT INTO images VALUES (?,?,?,?,?)", images)

    shapes = [
        (1, 1, "defect"), (2, 1, "defect"),
        (3, 2, "defect"),
        (4, 3, "scratch"),
        (5, 3, "stain"),
        (6, 4, "defect"),
        (7, 5, "scratch"),
    ]
    con.executemany("INSERT INTO shapes VALUES (?,?,?)", shapes)
    con.commit()
    return con


def load_queries(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    body = "\n".join(lines)
    return [q.strip() for q in body.split(";") if q.strip()]


def run(con, sql, idx):
    print("=" * 72)
    first = next((ln for ln in sql.splitlines() if ln.strip()), "")
    print("[%d] %s" % (idx, first))
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(" | ".join(cols))
    print("-" * 40)
    for r in rows:
        print(" | ".join(str(v) for v in r))
    print("")


def main():
    tmp = tempfile.mkdtemp(prefix="sql_demo_")
    db = os.path.join(tmp, "demo.db")
    con = build_demo_db(db)
    queries = load_queries(SQL_FILE)
    print("演示数据库：%d 张图 / %d 个标注多边形（合成数据）\n" % (
        con.execute("SELECT COUNT(*) FROM images").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM shapes").fetchone()[0]))
    for i, q in enumerate(queries, 1):
        run(con, q, i)
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
