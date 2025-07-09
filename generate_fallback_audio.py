# generate_fallback_audio.py
from google.cloud import texttospeech
import os

# Verifique se a autenticação do Google Cloud está configurada
# (ex: via `gcloud auth application-default login` ou variável de ambiente)

# Configurações
TEXT_TO_SPEAK = "Desculpe, não consegui processar sua fala. Por favor, tente novamente."
OUTPUT_FILENAME = "fallback_audio.raw"
SAMPLE_RATE = 24000

# Cliente
try:
    client = texttospeech.TextToSpeechClient()

    # Configuração da requisição
    synthesis_input = texttospeech.SynthesisInput(text=TEXT_TO_SPEAK)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="pt-BR",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE
    )

    print("Gerando áudio de fallback...")
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice_params, audio_config=audio_config
    )

    # Salva os bytes brutos do áudio no arquivo
    with open(OUTPUT_FILENAME, "wb") as out:
        out.write(response.audio_content)

    print(f"Áudio de fallback salvo com sucesso em '{OUTPUT_FILENAME}'")
    print(f"Total de bytes: {len(response.audio_content)}")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
    print("\nCertifique-se de que a API Text-to-Speech está habilitada no seu projeto Google Cloud.")
    print("E que suas credenciais de autenticação estão configuradas corretamente.")