import customtkinter as ctk
from tkinter import messagebox, simpledialog, ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os, hashlib
from datetime import datetime

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

FILE = "study_data.csv"
USER_FILE = "users.csv"
GOAL_FILE = "goals.csv"

current_user = None

# -------- PASSWORD --------
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# -------- USER SYSTEM --------
def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE, dtype=str).fillna("")
    else:
        df = pd.DataFrame([["admin", hash_password("1234")]],
                          columns=["Username","Password"])
        df.to_csv(USER_FILE,index=False)
        return df

def register():
    user = username_entry.get()
    pwd = hash_password(password_entry.get())

    users = load_users()

    if user in users["Username"].values:
        messagebox.showerror("Error","User exists")
        return

    users = pd.concat([users,
        pd.DataFrame([[user,pwd]],columns=["Username","Password"])])

    users.to_csv(USER_FILE,index=False)
    messagebox.showinfo("Success","Registered!")

def login():
    global current_user
    user = username_entry.get()
    pwd = hash_password(password_entry.get())

    users = load_users()
    match = users[(users["Username"]==user)&(users["Password"]==pwd)]

    if not match.empty:
        current_user = user
        app.destroy()
        main_app()
    else:
        messagebox.showerror("Error","Invalid login")

def toggle_password():
    password_entry.configure(show="" if password_entry.cget("show")=="*" else "*")

# -------- MAIN APP --------
def main_app():
    root = ctk.CTk()
    root.geometry("950x600")
    root.title("Study Dashboard")

    # -------- LAYOUT --------
    left = ctk.CTkFrame(root, width=250)
    left.pack(side="left", fill="y", padx=10, pady=10)

    right = ctk.CTkFrame(root)
    right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    graph_frame = ctk.CTkFrame(right)
    graph_frame.pack(fill="both", expand=True, pady=10)

    # -------- DATA --------
    def load_data():
        if not os.path.exists(FILE):
            return pd.DataFrame(columns=["Username","Date","Subject","Hours"])
        df = pd.read_csv(FILE)
        return df[df["Username"] == current_user]

    def save_data(df):
        if os.path.exists(FILE):
            old = pd.read_csv(FILE)
            old = old[old["Username"] != current_user]
            df = pd.concat([old, df])
        df.to_csv(FILE, index=False)

    # -------- GRAPH HELPER --------
    def show_graph(fig):
        for w in graph_frame.winfo_children():
            w.destroy()
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # -------- FUNCTIONS --------
    def add_record():
        try:
            datetime.strptime(date_entry.get(), "%d-%m-%Y")
            hours = float(hours_entry.get())
        except:
            messagebox.showerror("Error","Invalid input")
            return

        df = load_data()
        new = pd.DataFrame([[current_user, date_entry.get(),
                             subject_entry.get(), hours]],
            columns=["Username","Date","Subject","Hours"])

        df = pd.concat([df, new])
        save_data(df)
        update_dashboard()

    def view_data():
        df = load_data()
        if df.empty:
            messagebox.showerror("Error","No data")
            return

        win = ctk.CTkToplevel(root)
        win.title("Data")

        tree = ttk.Treeview(win)
        tree["columns"] = list(df.columns)

        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col)

        for _, row in df.iterrows():
            tree.insert("", "end", values=list(row))

        tree.pack(fill="both", expand=True)

    def delete_all():
        if messagebox.askyesno("Confirm","Delete ALL data?"):
            df = pd.read_csv(FILE)
            df = df[df["Username"] != current_user]
            df.to_csv(FILE,index=False)
            update_dashboard()

    def delete_specific():
        date = simpledialog.askstring("Date","Enter Date:")
        subject = simpledialog.askstring("Subject","Enter Subject:")

        df = load_data()
        df = df[~((df["Date"]==date)&(df["Subject"]==subject))]
        save_data(df)
        update_dashboard()

    # -------- GRAPHS --------
    def bar_graph():
        df = load_data()
        g = df.groupby("Subject")["Hours"].sum()

        fig, ax = plt.subplots()
        ax.bar(g.index, g.values)
        ax.set_title("Subject Hours")

        show_graph(fig)

    def pie_chart():
        df = load_data()
        g = df.groupby("Subject")["Hours"].sum()

        fig, ax = plt.subplots()
        ax.pie(g.values, labels=g.index, autopct='%1.1f%%')

        show_graph(fig)

    def trend():
        df = load_data()
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
        weekly = df.groupby(pd.Grouper(key="Date", freq="W"))["Hours"].sum()

        fig, ax = plt.subplots()
        ax.plot(weekly.index, weekly.values, marker='o')
        ax.set_title("Weekly Trend")

        show_graph(fig)

    # -------- ANALYSIS --------
    def update_dashboard():
        df = load_data()

        for w in right.winfo_children():
            if w != graph_frame:
                w.destroy()

        if df.empty:
            return

        total = df["Hours"].sum()
        avg = total / len(df["Date"].unique())
        best = df.groupby("Subject")["Hours"].sum().idxmax()

        top = ctk.CTkFrame(right)
        top.pack(fill="x")

        for text in [f"Total: {total}",
                     f"Avg/Day: {avg:.2f}",
                     f"Best: {best}"]:
            ctk.CTkLabel(top, text=text).pack(side="left", padx=10)

        trend()

        # Goals
        if os.path.exists(GOAL_FILE):
            goals = pd.read_csv(GOAL_FILE)
            totals = df.groupby("Subject")["Hours"].sum()

            for _, r in goals.iterrows():
                val = totals.get(r["Subject"], 0)
                prog = val / r["Goal"] if r["Goal"] else 0

                ctk.CTkLabel(right,
                    text=f"{r['Subject']} {val}/{r['Goal']}").pack()

                bar = ctk.CTkProgressBar(right)
                bar.set(min(prog,1))
                bar.pack()

    # -------- GOALS --------
    def set_goal():
        goal = float(hours_entry.get())

        if os.path.exists(GOAL_FILE):
            g = pd.read_csv(GOAL_FILE)
        else:
            g = pd.DataFrame(columns=["Subject","Goal"])

        g = g[g["Subject"] != subject_entry.get()]
        g = pd.concat([g, pd.DataFrame([[subject_entry.get(), goal]],
            columns=["Subject","Goal"])])

        g.to_csv(GOAL_FILE, index=False)
        update_dashboard()

    # -------- EXPORT --------
    def export():
        df = load_data()
        df.to_excel(f"{current_user}_data.xlsx", index=False)
        messagebox.showinfo("Done","Exported")

    # -------- THEME --------
    def toggle_theme():
        mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode("dark" if mode=="Light" else "light")

    # -------- UI --------
    ctk.CTkLabel(left, text=f"User: {current_user}").pack(pady=10)

    date_entry = ctk.CTkEntry(left, placeholder_text="Date DD-MM-YYYY")
    date_entry.pack(pady=5)

    subject_entry = ctk.CTkEntry(left, placeholder_text="Subject")
    subject_entry.pack(pady=5)

    hours_entry = ctk.CTkEntry(left, placeholder_text="Hours")
    hours_entry.pack(pady=5)

    ctk.CTkButton(left, text="Add", command=add_record).pack(pady=5)
    ctk.CTkButton(left, text="View Data", command=view_data).pack(pady=5)
    ctk.CTkButton(left, text="Delete All", command=delete_all).pack(pady=5)
    ctk.CTkButton(left, text="Delete Specific", command=delete_specific).pack(pady=5)

    ctk.CTkButton(left, text="Bar Graph", command=bar_graph).pack(pady=5)
    ctk.CTkButton(left, text="Pie Chart", command=pie_chart).pack(pady=5)
    ctk.CTkButton(left, text="Trend", command=trend).pack(pady=5)

    ctk.CTkButton(left, text="Set Goal", command=set_goal).pack(pady=5)
    ctk.CTkButton(left, text="Export Excel", command=export).pack(pady=5)
    ctk.CTkButton(left, text="Toggle Theme", command=toggle_theme).pack(pady=5)

    update_dashboard()
    root.mainloop()

# -------- LOGIN --------
app = ctk.CTk()
app.geometry("300x250")

username_entry = ctk.CTkEntry(app, placeholder_text="Username")
username_entry.pack(pady=10)

password_entry = ctk.CTkEntry(app, placeholder_text="Password", show="*")
password_entry.pack(pady=10)

ctk.CTkCheckBox(app, text="Show", command=toggle_password).pack()

ctk.CTkButton(app, text="Login", command=login).pack(pady=5)
ctk.CTkButton(app, text="Register", command=register).pack()

app.mainloop()
