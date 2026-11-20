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
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp, p, span, div, label, button, input, select, textarea, h1, h2, h3, h4, h5 {
    font-family: 'Plus Jakarta Sans', 'Hind Siliguri', sans-serif !important;
}

.stApp {
    background: linear-gradient(180deg, #F3F8F5 0%, #E8F2EC 100%) !important;
    color: #162620 !important;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1020px !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #164A32 0%, #0F3524 100%) !important;
    border-right: 2px solid rgba(212, 160, 36, 0.30);
}

[data-testid="stSidebar"] * {
    color: #F2F8F4 !important;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255, 255, 255, 0.16) !important;
}

.app-header {
    background: linear-gradient(120deg, #1B5E3A 0%, #2E7D32 65%, #8C6D1F 100%);
    color: #FFFFFF;
    padding: 1.45rem 1.75rem;
    border-radius: 14px;
    margin-bottom: 1.35rem;
    border: 1px solid rgba(212, 160, 36, 0.35);
    box-shadow: 0 8px 20px rgba(22, 74, 50, 0.10);
}

.app-header h1 {
    color: #FFFFFF !important;
    font-size: 1.85rem;
    margin: 0;
    font-weight: 700;
}

.app-header p {
    color: #F6FBF7 !important;
    margin: 0.35rem 0 0 0;
    font-size: 0.98rem;
}

/* কার্ডের ভেতরে সবকিছু ঠিকভাবে বসিয়ে রাখা, বাইরে যেন না যায় */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #F9FCFA 100%) !important;
    border: 1.5px solid #C8DDD0 !important;
    border-top: 4px solid #23703B !important;
    border-radius: 14px !important;
    padding: 0.75rem 1rem !important;
    box-shadow: 0 4px 14px rgba(22, 74, 50, 0.06) !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

/* Expander-এর আইকন লেখা যেন হেডারের ওপর না বসে */
[data-testid="stExpander"] summary [data-testid="stIconMaterial"],
[data-testid="stExpander"] summary .material-symbols-rounded,
[data-testid="stExpander"] summary .material-icons {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    font-size: 1.25rem !important;
    width: 1.25rem !important;
    min-width: 1.25rem !important;
    overflow: hidden !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-right: 0.4rem !important;
    color: #143D29 !important;
    -webkit-text-fill-color: #143D29 !important;
}

[data-testid="stExpander"] summary {
    display: flex !important;
    align-items: center !important;
    color: #143D29 !important;
    -webkit-text-fill-color: #143D29 !important;
    font-weight: 700 !important;
}

/* সব ইনপুট বক্স, লেখা ও প্লেসহোল্ডার একদম স্পষ্ট করার নিয়ম */
[data-testid="stVerticalBlockBorderWrapper"] label,
.stTextInput label,
.stNumberInput label,
.stSelectbox label {
    color: #162620 !important;
    font-weight: 600 !important;
}

input, textarea, [data-baseweb="input"] input, [data-baseweb="select"] input {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    caret-color: #164A32 !important;
}

input::placeholder, textarea::placeholder {
    color: #6B7280 !important;
    -webkit-text-fill-color: #6B7280 !important;
    opacity: 1 !important;
}

[data-baseweb="input"], [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border-color: #A7C4B3 !important;
    color: #111827 !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(135deg, #F2F9F4 0%, #FFFDF6 100%) !important;
    border: 1px solid #C6DEC9 !important;
    border-left: 4px solid #C8961E !important;
    border-radius: 10px !important;
    padding: 0.85rem 1rem !important;
}

[data-testid="stMetricValue"] {
    color: #164A32 !important;
    font-weight: 700 !important;
}

/* সাধারণ বাটনগুলো */
.stButton > button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    min-height: 2.65rem !important;
    background: linear-gradient(180deg, #EBF5EF 0%, #D9EAE0 100%) !important;
    color: #144730 !important;
    -webkit-text-fill-color: #144730 !important;
    border: 1px solid #9EC0AC !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

.stButton > button:hover {
    background: linear-gradient(180deg, #DCEEE3 0%, #C6E0D0 100%) !important;
    border-color: #1E6B3B !important;
}

/* View customers-এর Download বাটন: সুন্দর রঙিন লুক */
.stDownloadButton > button {
    border-radius: 9px !important;
    font-weight: 700 !important;
    min-height: 2.65rem !important;
    background: linear-gradient(135deg, #1B6B43 0%, #268454 100%) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 1px solid #145333 !important;
    box-shadow: 0 4px 12px rgba(27, 107, 67, 0.22) !important;
}

.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #145333 0%, #1E6E45 100%) !important;
}

/* প্রাইমারি / ফর্ম সাবমিট বাটন: আগের মতো আকর্ষণীয় লালচে-গোলাপি রঙ */
.stFormSubmitButton > button,
button[kind="primary"] {
    background: linear-gradient(135deg, #C92A4B 0%, #E03155 100%) !important;
    border: 1px solid #A61E3B !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    min-height: 2.65rem !important;
    box-shadow: 0 4px 12px rgba(201, 42, 75, 0.24) !important;
}

button[kind="primary"]:hover {
    background: linear-gradient(135deg, #AD203D 0%, #C92A4B 100%) !important;
}

/* ওভারল্যাপ / জড়িয়ে যাওয়া লেখা বা বাটন টেক্সট ঠিক রাখা */
.stButton > button > div,
.stDownloadButton > button > div,
.stFormSubmitButton > button > div,
button > div {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.35rem !important;
    line-height: 1.3 !important;
}

.section-note {
    color: #4F635A !important;
    margin-top: -0.25rem;
    margin-bottom: 0.9rem;
    font-size: 0.95rem;
}

/* সাইডবার টগল বাটনের ওপর কার্সার নিলে অপ্রয়োজনীয় লেখা/আইকন বিরক্ত না করার জন্য */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}
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
    st.markdown(
        """
        <div style="padding-bottom: 0.25rem;">
            <h1 style="margin: 0; font-size: 1.65rem; color: #FFFFFF;">📒 Due Book</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
        <div style="margin-top: 0.85rem; padding-top: 0.65rem; border-top: 1px solid rgba(255, 255, 255, 0.16); font-size: 0.85rem; color: #E6F2EA;">
            Developed by <strong>Nazmul Islam</strong> · Founder of <strong>Nazmora</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

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