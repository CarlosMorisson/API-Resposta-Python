# main.py

import os
import base64
import asyncio
import re
import struct
import traceback
from typing import Dict # << NOVO IMPORT

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from cachetools import TTLCache

import google.generativeai as genai
from google.generativeai.generative_models import ChatSession # << NOVO IMPORT
from google.cloud import texttospeech
from google.api_core import client_options

# --- SETUP ---
load_dotenv()
app = FastAPI()

# ... (configuração do Gemini e TTS não muda) ...
# --- CONFIGURAÇÃO GEMINI (para STT e LLM) ---
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
    print("✅ SUCESSO: Cliente Google Cloud Text-to-Speech carregado.")
except Exception as e:
    print(f"❌ FALHA CRÍTICA ao carregar o cliente TTS: {e}")
    tts_client = None

tts_cache = TTLCache(maxsize=100, ttl=3600)
TTS_SAMPLE_RATE = 24000


# --- MODELO DE DADOS ---
# << MUDANÇA 1: ATUALIZAR O MODELO DE DADOS PARA ACEITAR OS NOVOS PARÂMETROS >>
class AudioRequest(BaseModel):
    audioBase64: str
    sampleRate: int
    personality: str = "Você é um assistente virtual amigável. Responda de forma concisa."
    voiceName: str = "pt-BR-Standard-A"
    sessionId: str # Obrigatório

class ClearRequest(BaseModel):
    sessionId: str

# --- FUNÇÕES AUXILIARES ---
# ... (create_wav_file_from_pcm não muda) ...
def create_wav_file_from_pcm(pcm_data_base64: str, sample_rate: int) -> bytes:
    # ... código idêntico ao anterior ...
    pcm_bytes = base64.b64decode(pcm_data_base64)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(pcm_bytes)
    file_size = data_size + 36
    header = struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',file_size,b'WAVE',b'fmt ',16,1,num_channels,sample_rate,byte_rate,block_align,bits_per_sample,b'data',data_size)
    return header + pcm_bytes

# << MUDANÇA 2: ATUALIZAR A FUNÇÃO DE TTS E O CACHE >>
async def text_to_speech_pcm(text: str, voice_name: str) -> bytes | None:
    if not tts_client:
        print("Erro: Cliente TTS não está disponível.")
        return None

    # A chave do cache agora inclui o nome da voz para evitar colisões
    cache_key = f"pcm_cloud_{voice_name}_{text}"
    if cache_key in tts_cache:
        print(f'TTS (Cloud) | Cache HIT para voz "{voice_name}" e texto: "{text}"')
        return base64.b64decode(tts_cache[cache_key])

    print(f'TTS (Cloud) | Gerando novo áudio com voz "{voice_name}" para: "{text}"')
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        # Usamos o nome da voz recebido como parâmetro
        voice = texttospeech.VoiceSelectionParams(
            language_code="pt-BR", 
            name=voice_name 
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=TTS_SAMPLE_RATE,
        )

        response = await tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        audio_content = response.audio_content
        tts_cache[cache_key] = base64.b64encode(audio_content).decode('utf-8')
        return audio_content
        
    except Exception as e:
        print(f"Erro na API de TTS (Google Cloud) com a voz '{voice_name}': {e}")
        traceback.print_exc()
        return None

# << MUDANÇA 3: ATUALIZAR O GERADOR DE STREAM PARA PASSAR A VOZ >>
async def audio_stream_generator(llm_response_text: str, voice_name: str):
    try:
        if not llm_response_text: return
        sentence_endings = re.compile(r'(?<=[.!?…])\s*') 
        sentences = sentence_endings.split(llm_response_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 1:
                print(f"--> Gerando áudio para: '{sentence}'")
                # Passa o nome da voz para a função de TTS
                audio_chunk = await text_to_speech_pcm(sentence, voice_name)
                if audio_chunk: yield audio_chunk
        print("✅ Stream de áudio concluído.")
    except Exception as e:
        print(f"Erro durante a geração do stream de áudio: {traceback.format_exc()}")

# << MUDANÇA 4: ATUALIZAR O ENDPOINT PRINCIPAL PARA USAR OS NOVOS PARÂMETROS >>
@app.post("/voicechat-stream")
async def voicechat_stream(request: AudioRequest):
    try:
        session_id = request.sessionId
        print(f"\n--- Nova Requisição de Voz [Sessão: {session_id}] ---")

        # Gerencia a sessão de chat
        if session_id not in chat_sessions:
            print(f"Criando nova sessão de chat para ID: {session_id}")
            # Cria um novo modelo com a personalidade definida
            llm_model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=request.personality # Define o comportamento da IA
            )
            chat_sessions[session_id] = llm_model.start_chat()

        chat = chat_sessions[session_id]

        # STT (Speech-to-Text) - Sem mudanças aqui
        wav_buffer = create_wav_file_from_pcm(request.audioBase64, request.sampleRate)
        audio_blob = {'mime_type': 'audio/wav', 'data': wav_buffer}
        print("STT | Convertendo áudio para texto...")
        prompt_stt = ["Transcreva este áudio em português:", audio_blob]
        stt_response = await stt_model.generate_content_async(prompt_stt)
        transcribed_text = stt_response.text.strip() if hasattr(stt_response, 'text') else ""
        
        if not transcribed_text:
             print("STT | Resposta da API não continha texto.")
             async def empty_generator(): yield b''
             return StreamingResponse(empty_generator(), media_type="application/octet-stream")

        print(f'STT | Texto reconhecido: "{transcribed_text}"')
        
        # LLM (Large Language Model) - AGORA USANDO O CHAT
        print(f'LLM | Enviando para o chat: "{transcribed_text}"')
        
        # Em vez de generate_content_async, usamos send_message_async no objeto de chat
        llm_response = await chat.send_message_async(transcribed_text)
        
        llm_response_text = llm_response.text
        print(f'LLM | Resposta recebida: "{llm_response_text}"')

        # O histórico (chat.history) é atualizado automaticamente pela biblioteca

        # TTS (Text-to-Speech) - Sem mudanças aqui
        return StreamingResponse(
            audio_stream_generator(llm_response_text, request.voiceName), 
            media_type="application/octet-stream"
        )

    except Exception as e:
        print(f"Erro detalhado na rota /voicechat-stream: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor")


# << MUDANÇA 4: NOVA ROTA PARA LIMPAR O HISTÓRICO >>
@app.post("/clear-session")
async def clear_session(request: ClearRequest):
    session_id = request.sessionId
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        print(f"✅ Histórico da sessão {session_id} foi limpo.")
        return JSONResponse(
            status_code=200, 
            content={"message": f"Histórico da sessão {session_id} foi limpo."}
        )
    else:
        print(f"⚠️ Tentativa de limpar sessão inexistente: {session_id}")
        return JSONResponse(
            status_code=404, 
            content={"message": f"Sessão {session_id} não encontrada."}
        )


@app.get("/")
def read_root():
    return {"message": "Servidor de Chat por Voz com Memória de Contexto está rodando!"}
# ... (bloco para rodar o servidor não muda) ...

# --- PARA RODAR O SERVIDOR ---
# No terminal, execute:
# cd PythonProject\gemini-audio-python
# venv\Scripts\activate
# uvicorn main:app --reload --host 0.0.0.0 --port 3000