import streamlit as st

# App ka Title
st.title("Welcome to My Streamlit App! 🚀")

# Subheader aur Text
st.subheader("Yeh meri pehli Streamlit application hai.")
st.write("Aapne successfully GitHub par code paste kar diya hai aur ab aap isay deploy kar rahe hain.")

# User Input lene ke liye
name = st.text_input("Apna naam likhein:")

if name:
    st.success(f"Hello, {name}! Aapka app bilkul theek chal raha hai! 🎉")

# Ek simple button
if st.button("Click Me"):
    st.balloons()
    st.write("Mubarak ho! Aapne successfully Streamlit app run kar li hai.")
