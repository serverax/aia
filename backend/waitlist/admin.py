import sqlite3
import sys


def list_signups():
    try:
        conn = sqlite3.connect("waitlist.db")
        c = conn.cursor()
        c.execute(
            "SELECT id, name, email, profession, company, created_at FROM waitlist ORDER BY created_at DESC"
        )
        rows = c.fetchall()
        conn.close()

        if not rows:
            print("No signups yet")
            return

        print("\n" + "=" * 100)
        print(
            f"{'ID':<5} {'Name':<20} {'Email':<30} {'Profession':<25} {'Company':<15} {'Joined':<20}"
        )
        print("=" * 100)

        for row in rows:
            print(f"{row[0]:<5} {row[1]:<20} {row[2]:<30} {row[3]:<25} {row[4]:<15} {row[5]:<20}")

        print("=" * 100)
        print(f"Total: {len(rows)} signups\n")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_signups()
    else:
        print("Usage: python admin.py list")
