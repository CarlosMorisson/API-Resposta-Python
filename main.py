import os
import base64
import asyncio
import re
import struct
import traceback
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from cachetools import TTLCache

import google.generativeai as genai
from google.generativeai.generative_models import ChatSession
from google.cloud import texttospeech
from google.api_core import client_options

# --- SETUP ---
load_dotenv()
app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY não foi encontrada no arquivo .env")
genai.configure(api_key=GEMINI_API_KEY)

stt_model = genai.GenerativeModel("gemini-1.5-pro-latest")
llm_model = genai.GenerativeModel("gemini-1.5-pro-latest")

chat_sessions: Dict[str, ChatSession] = {}

try:
    client_opts = client_options.ClientOptions(api_key=GEMINI_API_KEY)
    tts_client = texttospeech.TextToSpeechAsyncClient(client_options=client_opts)
    print("✅ Cliente TTS carregado com sucesso.")
except Exception as e:
    print(f"❌ Erro ao carregar cliente TTS: {e}")
    tts_client = None

tts_cache = TTLCache(maxsize=100, ttl=3600)
TTS_SAMPLE_RATE = 24000

# --- MODELOS ---
class AudioRequest(BaseModel):
    audioBase64: str
    sampleRate: int
    personality: str = "Você é um assistente virtual amigável. Responda de forma concisa."
    voiceName: str = "pt-BR-Standard-A"
    sessionId: str

class ClearRequest(BaseModel):
    sessionId: str

# --- FUNÇÕES AUXILIARES ---
def create_wav_file_from_pcm(pcm_data_base64: str, sample_rate: int) -> bytes:
    pcm_bytes = base64.b64decode(pcm_data_base64)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(pcm_bytes)
    file_size = data_size + 36
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', file_size, b'WAVE', b'fmt ', 16, 1, num_channels,
        sample_rate, byte_rate, block_align, bits_per_sample, b'data', data_size)
    return header + pcm_bytes

async def text_to_speech_pcm(text: str, voice_name: str) -> bytes | None:
    if not tts_client:
        return None

    cache_key = f"pcm_cloud_{voice_name}_{text}"
    if cache_key in tts_cache:
        print(f"🎵 TTS Cache HIT: \"{text}\"")
        return base64.b64decode(tts_cache[cache_key])

    try:
        print(f"🎤 Gerando TTS: \"{text}\"")
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(language_code="pt-BR", name=voice_name)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=TTS_SAMPLE_RATE,
        )

        response = await tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        audio_content = response.audio_content

        print(f"📦 Chunk gerado: {len(audio_content)} bytes")
        tts_cache[cache_key] = base64.b64encode(audio_content).decode('utf-8')
        return audio_content

    except Exception as e:
        print(f"❌ Erro TTS: {e}")
        traceback.print_exc()
        return None

async def audio_stream_generator(text: str, voice_name: str):
    sentence_endings = re.compile(r'(?<=[.!?…])\s*')
    sentences = sentence_endings.split(text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 1:
            chunk = await text_to_speech_pcm(sentence, voice_name)
            if chunk:
                yield chunk
                await asyncio.sleep(0)  # Libera event loop

# --- ENDPOINT PRINCIPAL COM STREAMING (normal) ---
@app.post("/voicechat-stream")
async def voicechat_stream(request: AudioRequest):
    try:
        session_id = request.sessionId
        if session_id not in chat_sessions:
            print(f"🧠 Nova sessão: {session_id}")
            llm = genai.GenerativeModel("gemini-2.5-flash", system_instruction=request.personality)
            chat_sessions[session_id] = llm.start_chat()
        chat = chat_sessions[session_id]

        print(f"🗣️ Recebendo fala de: {session_id}")
        wav_buffer = create_wav_file_from_pcm(request.audioBase64, request.sampleRate)
        audio_blob = {'mime_type': 'audio/wav', 'data': wav_buffer}

        stt_response = await stt_model.generate_content_async([
            "Transcreva este áudio em português:", audio_blob
        ])
        user_text = stt_response.text.strip() if hasattr(stt_response, "text") else ""

        if not user_text:
            return StreamingResponse((b"" for _ in range(1)), media_type="application/octet-stream")

        print(f"✍️ Texto STT: \"{user_text}\"")
        llm_response = await chat.send_message_async(user_text)
        final_text = llm_response.text.strip()
        print(f"🤖 IA respondeu: \"{final_text}\"")

        return StreamingResponse(
            audio_stream_generator(final_text, request.voiceName),
            media_type="application/octet-stream"
        )

    except Exception:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Erro interno.")

# --- ENDPOINT ALTERNATIVO: BUFFERIZADO (NÃO STREAMING) ---
@app.post("/voicechat-stream-buffered")
async def voicechat_stream_buffered(request: AudioRequest):
    try:
        session_id = request.sessionId
        if session_id not in chat_sessions:
            llm = genai.GenerativeModel("gemini-2.5-flash", system_instruction=request.personality)
            chat_sessions[session_id] = llm.start_chat()
        chat = chat_sessions[session_id]

        wav_buffer = create_wav_file_from_pcm(request.audioBase64, request.sampleRate)
        audio_blob = {'mime_type': 'audio/wav', 'data': wav_buffer}
        stt_response = await stt_model.generate_content_async([
            "Transcreva este áudio em português:", audio_blob
        ])
        user_text = stt_response.text.strip() if hasattr(stt_response, "text") else ""

        if not user_text:
            return Response(content=b"", media_type="application/octet-stream")

        llm_response = await chat.send_message_async(user_text)
        final_text = llm_response.text.strip()
        print(f"[BUFFERED] Texto IA: {final_text}")

        sentence_endings = re.compile(r'(?<=[.!?…])\s*')
        sentences = sentence_endings.split(final_text)

        full_audio = b""
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                chunk = await text_to_speech_pcm(sentence, request.voiceName)
                if chunk:
                    full_audio += chunk

        return Response(content=full_audio, media_type="application/octet-stream")

    except Exception:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Erro interno (buffered).")

# --- LIMPAR HISTÓRICO ---
@app.post("/clear-session")
async def clear_session(request: ClearRequest):
    sid = request.sessionId
    if sid in chat_sessions:
        del chat_sessions[sid]
        return {"message": f"Histórico da sessão {sid} foi limpo."}
    return {"message": f"Sessão {sid} não encontrada."}

@app.get("/")
def home():
    return {"status": "Servidor Gemini + TTS ativo!"}

# ... (bloco para rodar o servidor não muda) ...

# --- PARA RODAR O SERVIDOR ---
# No terminal, execute:
# cd PythonProject\gemini-audio-python
# venv\Scripts\activate
# uvicorn main:app --reload --host 0.0.0.0 --port 3000
#gcloud compute ssh root@therafy-vm --zone=us-central1-a