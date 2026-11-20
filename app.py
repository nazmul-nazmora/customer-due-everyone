"""Customer Due Book - Streamlit web app (SQLite edition)"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Customer Due Book", page_icon="📒", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DUE_DB_PATH", BASE_DIR / "customer_due.db"))
OLD_JSON_FILE = BASE_DIR / "customers.json"  # old data is imported once, automatically


def get_owner_name():
    """Owner name: Streamlit secrets (OWNER_NAME) -> env DUE_OWNER_NAME -> 'nazmul'."""
    try:
        return str(st.secrets["OWNER_NAME"]).strip().lower()
    except Exception:
        return os.getenv("DUE_OWNER_NAME", "nazmul").strip().lower()


OWNER_NAME = get_owner_name()

# ---------------------------------------------------------------- styling
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp h1, .stApp h2, .stApp h3 {
    font-family: 'Hind Siliguri', 'Segoe UI', sans-serif;
}
.stApp { background: #EEF2F4; }
.block-container { padding-top: 1.6rem; max-width: 1050px; }

[data-testid="stSidebar"] { background: #0B3B38; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #E6F0EE;
}
[data-testid="stSidebar"] hr { border-color: #2B5C58; }

.app-header { background: #0B3B38; color: #F2F7F6; padding: 1.3rem 1.6rem;
    border-radius: 10px; margin-bottom: 1.2rem; }
.app-header h1 { color: #F2F7F6; font-size: 1.9rem; margin: 0; padding: 0; font-weight: 700; }
.app-header p { color: #B5CFCB; margin: .2rem 0 0 0; }

[data-testid="stVerticalBlockBorderWrapper"] { background: #FFFFFF; border-radius: 10px; }
[data-testid="stMetric"] { background: #F6F9FA; border: 1px solid #DCE5E8;
    border-radius: 10px; padding: .8rem 1rem; }
[data-testid="stMetricValue"] { color: #0B3B38; font-weight: 700; }

.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
    border-radius: 8px; font-weight: 600; min-height: 2.6rem;
}
.stFormSubmitButton > button[kind="primary"], .stButton > button[kind="primary"] {
    background: #0B6B63; border-color: #0B6B63;
}
.due-pill { display: inline-block; padding: .15rem .7rem; border-radius: 999px;
    font-weight: 600; background: #FBE9E7; color: #B3261E; }
.paid-pill { display: inline-block; padding: .15rem .7rem; border-radius: 999px;
    font-weight: 600; background: #E3F4EA; color: #1E7B4F; }
.section-note { color: #5C6B70; margin-top: -.4rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- database
@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now_text():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE,
                due INTEGER NOT NULL CHECK (due >= 0),
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL
                    REFERENCES customers(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL CHECK (amount > 0),
                paid_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id)")


def migrate_old_json():
    """One-time import of the old customers.json (only if the database is empty)."""
    if not OLD_JSON_FILE.exists():
        return
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] > 0:
            return
        try:
            raw = json.loads(OLD_JSON_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, list):
            return
        for item in raw:
            try:
                name = str(item["Name"]).strip()
                due = int(item["Due"])
            except (KeyError, TypeError, ValueError):
                continue
            if name and due >= 0:
                conn.execute(
                    "INSERT INTO customers(name, due, created_at) VALUES (?, ?, ?)",
                    (name, due, now_text()),
                )
    try:  # keep the old file as a backup so nothing is lost
        OLD_JSON_FILE.replace(OLD_JSON_FILE.with_suffix(".imported.json"))
    except OSError:
        pass


def like_escape(text):
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def fetch_customers(search=""):
    with get_connection() as conn:
        if search:
            return conn.execute(
                "SELECT id, name, due, created_at FROM customers "
                "WHERE name LIKE ? ESCAPE '\\' ORDER BY name COLLATE NOCASE, id",
                (f"%{like_escape(search)}%",),
            ).fetchall()
        return conn.execute(
            "SELECT id, name, due, created_at FROM customers ORDER BY name COLLATE NOCASE, id"
        ).fetchall()


def add_customer(name, due):
    """Add a new customer. If the name already exists, the amount is added to that customer."""
    name = name.strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, due FROM customers WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            new_due = row["due"] + int(due)
            conn.execute("UPDATE customers SET due=? WHERE id=?", (new_due, row["id"]))
            return "updated", row["name"], new_due
        conn.execute(
            "INSERT INTO customers(name, due, created_at) VALUES (?, ?, ?)",
            (name, int(due), now_text()),
        )
        return "created", name, int(due)


def record_payment(customer_id, amount):
    amount = int(amount)
    if amount <= 0:
        raise ValueError("Payment cannot be negative or zero.")
    with get_connection() as conn:
        row = conn.execute("SELECT due FROM customers WHERE id=?", (customer_id,)).fetchone()
        if row is None:
            raise ValueError("Customer not found.")
        if amount > row["due"]:
            raise ValueError("Payment cannot exceed due amount.")
        new_due = row["due"] - amount
        conn.execute("UPDATE customers SET due=? WHERE id=?", (new_due, customer_id))
        conn.execute(
            "INSERT INTO payments(customer_id, amount, paid_at) VALUES (?, ?, ?)",
            (customer_id, amount, now_text()),
        )
        return new_due


def fetch_payments(customer_id, limit=10):
    with get_connection() as conn:
        return conn.execute(
            "SELECT amount, paid_at FROM payments WHERE customer_id=? "
            "ORDER BY id DESC LIMIT ?",
            (customer_id, limit),
        ).fetchall()


# ---------------------------------------------------------------- helpers
def flash(kind, message):
    st.session_state.flash = (kind, message)


def show_flash():
    item = st.session_state.pop("flash", None)
    if item:
        getattr(st, item[0])(item[1])


def to_text(rows):
    return "\n".join(f"Name: {r['name']} - Due: {r['due']} TK" for r in rows)


def to_dataframe(rows):
    data = [
        {
            "#": i + 1,
            "Name": r["name"],
            "Due (TK)": r["due"],
            "Status": "Due" if r["due"] > 0 else "Paid",
            "Added": r["created_at"][:10],
        }
        for i, r in enumerate(rows)
    ]
    return pd.DataFrame(data, columns=["#", "Name", "Due (TK)", "Status", "Added"])


# ---------------------------------------------------------------- pages
def page_add():
    with st.container(border=True):
        st.subheader("Add a customer")
        st.markdown(
            '<p class="section-note">কাস্টমারের নাম ও বাকির পরিমাণ লিখুন।</p>',
            unsafe_allow_html=True,
        )
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Customer name", placeholder="যেমন: Rahim Uddin")
            due = st.number_input("Due amount (TK)", min_value=0, step=50, value=0)
            submitted = st.form_submit_button(
                "Add customer", type="primary", use_container_width=True
            )
        if submitted:
            name = name.strip()
            if not name:
                st.error("Customer name cannot be empty.")
            elif due <= 0:
                st.error("Due amount must be greater than zero.")
            else:
                try:
                    kind, shown_name, total = add_customer(name, due)
                except sqlite3.Error as exc:
                    st.error(f"Could not save: {exc}")
                    return
                if kind == "created":
                    flash("success", f"{shown_name} added successfully!")
                else:
                    flash(
                        "info",
                        f"{shown_name} already existed - added {int(due)} TK. "
                        f"Updated due: {total} TK.",
                    )
                st.rerun()


def page_view():
    with st.container(border=True):
        st.subheader("Customers")
        query = st.text_input(
            "Search by name",
            placeholder="Type a name, or leave empty / type 'all' to see everyone",
        ).strip()

        search = "" if query.lower() in ("", "all") else query
        shown = fetch_customers(search)

        if not shown:
            if search:
                st.warning("Customer not found.")
            else:
                st.info("No customer found. Add your first customer from the sidebar.")
            return

        df = to_dataframe(shown)
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "#": st.column_config.NumberColumn(width="small"),
                "Due (TK)": st.column_config.NumberColumn(format="%d TK"),
            },
        )

        c1, c2 = st.columns(2)
        c1.download_button(
            "Download as CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="customers.csv",
            mime="text/csv",
            use_container_width=True,
        )
        c2.download_button(
            "Download as TXT",
            to_text(shown).encode("utf-8"),
            file_name="customers.txt",
            mime="text/plain",
            use_container_width=True,
        )


def page_payment():
    customers = fetch_customers()
    with st.container(border=True):
        st.subheader("Receive a payment")
        if not customers:
            st.info("No customer found. Add a customer first.")
            return

        by_id = {r["id"]: r for r in customers}
        cid = st.selectbox(
            "Customer",
            list(by_id.keys()),
            format_func=lambda i: f"{by_id[i]['name']}  -  {by_id[i]['due']} TK",
        )
        customer = by_id[cid]

        c1, c2 = st.columns(2)
        c1.metric("Customer", customer["name"])
        c2.metric("Current due", f"{customer['due']} TK")

        if customer["due"] == 0:
            st.success("This customer has no due balance.")
        else:
            with st.form("payment_form", clear_on_submit=True):
                payment = st.number_input(
                    "Payment amount (TK)", min_value=0, step=50, value=0
                )
                b1, b2 = st.columns(2)
                pay = b1.form_submit_button(
                    "Pay now", type="primary", use_container_width=True
                )
                later = b2.form_submit_button("Pay later", use_container_width=True)

            if later:
                st.info("Please pay on time.")
            elif pay:
                if payment <= 0:
                    st.error("Payment cannot be negative or zero.")
                elif payment > customer["due"]:
                    st.error("Payment cannot exceed due amount.")
                else:
                    try:
                        remaining = record_payment(cid, payment)
                    except (sqlite3.Error, ValueError) as exc:
                        st.error(str(exc))
                        return
                    if remaining == 0:
                        flash("success", "Payment successful! Due balance is 0.")
                    else:
                        flash("success", f"Payment successful! Due balance is {remaining} TK.")
                    st.rerun()

        history = fetch_payments(cid)
        if history:
            with st.expander("Recent payments (সাম্প্রতিক পেমেন্ট)"):
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"Date": h["paid_at"].replace("T", " "), "Amount (TK)": h["amount"]}
                            for h in history
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )


def page_total():
    with st.container(border=True):
        st.subheader("Total due (owner only)")
        st.markdown(
            '<p class="section-note">মোট বকেয়া শুধু মালিক দেখতে পারবেন।</p>',
            unsafe_allow_html=True,
        )
        customers = fetch_customers()
        if not customers:
            st.info("No customer found.")
            return

        name = st.text_input("Owner name", placeholder="Enter the owner's name").strip().lower()
        if not name:
            st.caption("Only the owner can view the total.")
        elif name == OWNER_NAME:
            total = sum(r["due"] for r in customers)
            with_due = sum(1 for r in customers if r["due"] > 0)
            m1, m2, m3 = st.columns(3)
            m1.metric("Total customers due", f"{total:,} TK")
            m2.metric("Customers", len(customers))
            m3.metric("Still owing", with_due)

            top = sorted((r for r in customers if r["due"] > 0), key=lambda r: -r["due"])[:5]
            if top:
                st.markdown("##### Highest dues (সবচেয়ে বেশি বাকি)")
                st.dataframe(
                    pd.DataFrame([{"Name": r["name"], "Due (TK)": r["due"]} for r in top]),
                    hide_index=True,
                    use_container_width=True,
                    column_config={"Due (TK)": st.column_config.NumberColumn(format="%d TK")},
                )
        else:
            st.error("You are not the owner. Only the owner can view the total.")


# ---------------------------------------------------------------- main
try:
    init_db()
    migrate_old_json()
except sqlite3.Error as exc:
    st.error(f"Database could not be started: {exc}")
    st.stop()

PAGES = {
    "Add customer": page_add,
    "View customers": page_view,
    "Payment": page_payment,
    "Total due": page_total,
}

with st.sidebar:
    st.title("📒 Due Book")
    st.caption("Customer Due Management")
    st.divider()
    choice = st.radio("Menu", list(PAGES.keys()), label_visibility="collapsed")
    st.divider()
    try:
        st.caption(f"{len(fetch_customers())} customers saved")
    except sqlite3.Error:
        st.warning("Could not read the database.")
    st.caption("Amounts are in Bangladeshi Taka (TK). Data is stored in a SQLite database.")

st.markdown(
    """
<div class="app-header">
  <h1>Customer Due Book</h1>
  <p>Track what your customers owe and record payments. · সহজে কাস্টমারের বাকি হিসাব রাখুন।</p>
</div>
""",
    unsafe_allow_html=True,
)

show_flash()
PAGES[choice]()