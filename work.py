import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Connect to SQLite database
conn = sqlite3.connect("tasks.db", check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute("""CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)""")
c.execute("""CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    task TEXT,
    task_date TEXT,
    duration REAL,
    category TEXT,
    priority TEXT,
    status TEXT
)""")
conn.commit()

# Default admin user
c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?)", ("admin", "1234", "admin"))
conn.commit()

# Session state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = None

# Login / Register
if not st.session_state["logged_in"]:
    st.title("🔐 Login or Register")
    option = st.radio("Choose an option:", ["Login", "Register"])

    if option == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = c.fetchone()
            if user:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("Logged in successfully ✅")
                st.rerun()
            else:
                st.error("Invalid credentials ❌")

    elif option == "Register":
        new_user = st.text_input("New username")
        new_pass = st.text_input("New password", type="password")
        if st.button("Register"):
            try:
                c.execute("INSERT INTO users VALUES (?,?,?)", (new_user, new_pass, "user"))
                conn.commit()
                st.success("Registration successful ✅")
            except:
                st.error("Username already exists ❌")

else:
    # Get user role
    role = c.execute("SELECT role FROM users WHERE username=?", (st.session_state["username"],)).fetchone()[0]

    # Sidebar menu
    st.sidebar.title("Navigation")
    if role == "admin":
        page = st.sidebar.radio("Select page", ["Home", "Tasks", "Reports", "Profile", "Admin"])
    else:
        page = st.sidebar.radio("Select page", ["Home", "Tasks", "Profile"])

    st.sidebar.write(f"👤 Logged in as: {st.session_state['username']}")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.rerun()

    # Home page
    if page == "Home":
        st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🌟 Task Management System 🌟</h1>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=200)
        st.write("Welcome! This app helps you:")
        st.markdown("""
        - 📝 Record and manage your daily tasks  
        - ⏱ Track how long each task takes  
        - 📊 View reports and summaries  
        - 👨‍💼 Admins can manage all users and tasks  
        """)
        st.info("Use the sidebar to navigate between pages.")
        st.success("Ready to get things done? Let's go 🚀")

    # Tasks page
    elif page == "Tasks":
        st.title("📝 Add a New Task")
        task_name = st.text_input("Task name")
        task_date = st.date_input("Task date", date.today())
        duration = st.number_input("Duration (hours)", min_value=0.0, step=0.25)
        category = st.text_input("Category/Project")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        status = st.selectbox("Status", ["Pending", "In Progress", "Done"])

        if st.button("Save task"):
            c.execute("INSERT INTO tasks (username, task, task_date, duration, category, priority, status) VALUES (?,?,?,?,?,?,?)",
                      (st.session_state["username"], task_name, str(task_date), duration, category, priority, status))
            conn.commit()
            st.success("Task saved successfully ✅")

        st.subheader("📋 Your Tasks")
        df = pd.read_sql_query("SELECT task, task_date, duration, category, priority, status FROM tasks WHERE username=?",
                               conn, params=(st.session_state["username"],))
        st.table(df)
        st.write(f"⏱ Total hours: {df['duration'].sum()} h")

    # Reports page (admin only)
    elif page == "Reports":
        st.title("📊 Reports")

        # Filters
        dates = ["All"] + [row[0] for row in c.execute("SELECT DISTINCT task_date FROM tasks").fetchall()]
        date_option = st.selectbox("Filter by date", dates)

        users = ["All"] + [row[0] for row in c.execute("SELECT DISTINCT username FROM tasks").fetchall()]
        user_option = st.selectbox("Filter by user", users)

        query = "SELECT username, task, task_date, duration, category, priority, status FROM tasks WHERE 1=1"
        params = []

        if date_option != "All":
            query += " AND task_date=?"
            params.append(date_option)
        if user_option != "All":
            query += " AND username=?"
            params.append(user_option)

        df = pd.read_sql_query(query, conn, params=params)
        st.table(df)
        st.write(f"⏱ Total hours: {df['duration'].sum()} h")

        # Chart
        if not df.empty:
            st.bar_chart(df.groupby("username")["duration"].sum())

        # Export button with download
        if st.button("📤 Download total work per user"):
            summary = df.groupby("username")["duration"].sum().reset_index()
            csv = summary.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="user_total_work.csv",
                mime="text/csv"
            )

    # Profile page
    elif page == "Profile":
        st.title("👤 User Profile")
        st.write(f"**Username:** {st.session_state['username']}")
        st.write(f"**Role:** {role}")

        df = pd.read_sql_query("SELECT task, task_date, duration, category, priority, status FROM tasks WHERE username=?",
                               conn, params=(st.session_state["username"],))
        total_tasks = len(df)
        total_hours = df["duration"].sum()

        st.write(f"**Total tasks:** {total_tasks}")
        st.write(f"**Total hours worked:** {total_hours} h")

        if not df.empty:
            st.subheader("📊 Task Summary")
            st.bar_chart(df.groupby("status")["duration"].sum())

    # Admin page (admin only)
    elif page == "Admin":
        if role == "admin":
            st.title("⚙️ Admin Panel")
            st.write("All tasks from all users:")
            df = pd.read_sql_query("SELECT * FROM tasks", conn)
            st.table(df)
        else:
            st.error("⛔ Access denied. Admins only.")
