# list_models.py

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERRO: Chave GEMINI_API_KEY não encontrada no arquivo .env")
else:
    genai.configure(api_key=GEMINI_API_KEY)

    print("--- Modelos Disponíveis que Suportam 'generateContent' (necessário para TTS) ---\n")
    
    found_tts_model = False
    for m in genai.list_models():
      # Vamos verificar se o método que estamos usando ('generateContent') é suportado pelo modelo
      if 'generateContent' in m.supported_generation_methods:
        # E vamos focar apenas nos modelos que parecem ser de TTS
        if 'tts' in m.name:
          print(f"Modelo Encontrado: {m.name}")
          found_tts_model = True
          
    if not found_tts_model:
        print("\nNenhum modelo de TTS encontrado. Verifique se sua conta tem acesso à API de TTS.")
        print("Modelos de texto disponíveis:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                print(f"- {m.name}")

    print("\n--- Fim da Lista ---")