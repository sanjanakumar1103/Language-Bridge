import os
import streamlit as st
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from deep_translator import GoogleTranslator
import sqlite3

# Detect OS and set Tesseract path accordingly
if os.name == "nt":  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\kaavi\Music\code\Tesseract-OCR\tesseract.exe'
else:  # Linux (Streamlit Cloud)
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


# Database Setup
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS translation_history (username TEXT, text_input TEXT, translated_text TEXT)''')
    conn.commit()
    conn.close()

# Ensure the database is initialized when the app starts
init_db()  # Initialize the database

def register_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists

def login_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def save_translation_history(username, text_input, translated_text):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT INTO translation_history (username, text_input, translated_text) VALUES (?, ?, ?)", 
              (username, text_input, translated_text))
    conn.commit()
    conn.close()

def get_translation_history(username):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT text_input, translated_text FROM translation_history WHERE username = ?", (username,))
    history = c.fetchall()
    conn.close()
    return history

# Set up Streamlit page config
st.set_page_config(page_title="Language Bridge", layout="wide")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Login", "Register", "Translate"])

# Colors & Styling
st.markdown(
    """
    <style>
        body {background-color: #e0f7fa;}  
        .stTextInput, .stButton, .stSelectbox {border-radius: 10px; border: 2px solid #004d40;} 
        .css-18e3th9 {padding: 20px;}  
        .css-1d391kg {background-color: #80deea; border-radius: 10px;}  
        h1, h2, h3 {color: #004d40;}  
        .stButton>button {background-color: #004d40; color: white; border-radius: 8px;} 
        .stButton>button:hover {background-color: #00796b;}  
        .stTextInput>div>input {border: 2px solid #00796b; border-radius: 8px; padding: 10px;}  
        .stTextInput>div>label {color: #00796b;}  
        .stTextArea>textarea {border: 2px solid #00796b; border-radius: 8px; padding: 10px;}  
        .stRadio {padding: 0;}  
        .stRadio, .stButton, .stTextInput, .stSelectbox, .stTextArea {
            box-shadow: none;
            border-width: 0 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Home Page
if page == "Home":
    st.title("📖 Language Bridge: Translating Educational Content")
    st.write("Hello, welcome to Language Bridge! This tool is designed to help students translate their textbooks and study materials into languages they are comfortable with. We currently support English, Tamil, and Hindi. With this app, you can easily extract text from images and PDFs and get them translated into your preferred language.")

# Login Page
elif page == "Login":
    st.title("🔑 Student Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.success("Login successful!")
            st.session_state["logged_in"] = True
            st.session_state["logged_in_username"] = username  # Store the username in session state
            st.session_state["page"] = "Translate"  # Set the next page to Translate
        else:
            st.error("Invalid credentials")

# Register Page
elif page == "Register":
    st.title("📝 Student Registration")
    new_username = st.text_input("Create Username")
    new_password = st.text_input("Create Password", type="password")
    if st.button("Register"):
        if register_user(new_username, new_password):
            st.success("Account created successfully!")
            st.session_state["page"] = "Login"  # After registration, set the page to login
        else:
            st.error("Username already exists, please choose another one.")

# Translate Page
elif page == "Translate":
    st.title("📜 Translate Educational Content")

    # Check if user is logged in
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.warning("You need to log in to access the translation page.")
    else:
        username = st.session_state.get("logged_in_username", "")

        uploaded_file = st.file_uploader("Upload an Image or PDF", type=["png", "jpg", "jpeg", "pdf"])

        if uploaded_file:
            extracted_text = ""
            
            col1, col2 = st.columns(2)
            with col1:
                if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Uploaded Image", use_column_width=True)
                    extracted_text = pytesseract.image_to_string(image)
                elif uploaded_file.type == "application/pdf":
                    images = convert_from_bytes(uploaded_file.read())
                    extracted_text = "\n".join([pytesseract.image_to_string(img) for img in images])
                
                st.text_area("Extracted Text", extracted_text, height=200)

            with col2:
                lang_options = {"English": "en", "Tamil": "ta", "Hindi": "hi"}
                tgt_lang = st.selectbox("Target Language", list(lang_options.keys()))
                if st.button("Translate"):
                    if extracted_text.strip():
                        translated_text = GoogleTranslator(source="auto", target=lang_options[tgt_lang]).translate(extracted_text)
                        st.text_area("Translated Text", translated_text, height=200)

                        # Save translation history to the database
                        save_translation_history(username, extracted_text, translated_text)
                    else:
                        st.warning("No text found. Please check the uploaded file.")

        # Display user's translation history
        st.subheader("Your Translation History")
        history = get_translation_history(username)
        if history:
            for record in history:
                with st.expander(f"Original Text: {record[0]}"):  # Expandable section with one line of original text
                    st.write(f"**Translated Text:** {record[1]}")
        else:
            st.write("No translations found in your history.")
            # Add this after the Translate page logic, around line 160+

# Functions to retrieve data from the database
def show_users():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return users

def show_translation_history():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM translation_history")
    history = c.fetchall()
    conn.close()
    return history

# Sidebar buttons to show database contents
st.sidebar.title("Admin Panel")  # Add a title for better organization

if st.sidebar.button("Show Users"):
    users = show_users()
    if users:
        st.write("### Registered Users")
        st.table(users)
    else:
        st.write("No users found.")

if st.sidebar.button("Show Translation History"):
    history = show_translation_history()
    if history:
        st.write("### Translation History")
        st.table(history)
    else:
        st.write("No history found.")

