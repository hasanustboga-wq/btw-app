import streamlit as st
import google.generativeai as genai
import os

# 1. API Sleutel instellen (deze pakt de geheime sleutel uit Streamlit)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Let op: API sleutel mist! Voeg deze toe in de Streamlit instellingen.")

# De Systeeminstructies (Hier staat jouw uitgebreide prompt!)
SYSTEM_INSTRUCTION = """
Je bent een senior fiscaal expert en AI-assistent, gespecialiseerd in de Belgische btw-wetgeving.

PRIORITEITSREGEL: GEBRUIKERSINPUT OVERSCHRIJFT ALLES
1. Type Factuur:
- ALS de gebruiker "Aankoop" kiest: Gebruik inkomende roosters (81, 82, 83, 59).
- ALS de gebruiker "Verkoop" kiest: Gebruik uitgaande roosters (01, 02, 03, 54).
2. Aftrekpercentage (Enkel bij Aankopen): Gebruik het meegegeven percentage om rooster 59 te berekenen. Het niet-aftrekbare deel tel je op bij de maatstaf van heffing (81/82/83).

Geef altijd antwoord in een gestructureerd JSON formaat dat de roosters toont.
"""

# Instellen van het AI model
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config={"response_mime_type": "application/json"}
)

# --- DE INTERFACE VAN JE APP ---
st.title("🇧🇪 Belgische Btw-Assistent")

# De knoppen op je scherm
factuur_type = st.radio("Is dit een aankoop- of verkoopfactuur?", ("Aankoop", "Verkoop"))

aftrekpercentage = 100
if factuur_type == "Aankoop":
    aftrekpercentage = st.number_input("Aftrekpercentage (%)", min_value=0, max_value=100, value=100)

geuploade_pdf = st.file_uploader("Upload je factuur (PDF)", type=["pdf"])

# De Actie!
if st.button("Verwerk Factuur"):
    if geuploade_pdf is not None:
        with st.spinner("AI is de factuur aan het lezen..."):
            
            # PDF klaarzetten voor de AI
            file_bytes = geuploade_pdf.getvalue()
            bestand_data = [{"mime_type": "application/pdf", "data": file_bytes}]
            
            # De prompt bouwen met jouw knop-keuzes
            user_prompt = f"Verwerk deze factuur. Type is {factuur_type}. Aftrekpercentage is {aftrekpercentage}%."
            
            # Vraag naar Gemini sturen
            try:
                response = model.generate_content([user_prompt, bestand_data[0]])
                st.success("Klaar!")
                st.json(response.text) # Laat de JSON netjes op het scherm zien
            except Exception as e:
                st.error(f"Er ging iets mis: {e}")
    else:
        st.warning("Upload eerst een PDF factuur!")
