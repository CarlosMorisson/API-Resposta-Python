# autopsia.py

print("--- INICIANDO AUTÓPSIA FINAL ---")
print("Vamos inspecionar o módulo problemático diretamente.")

try:
    # 1. Tentamos importar o módulo exato que está falhando
    from google.ai.generativelanguage_v1beta.types import text_service
    
    print("\n[INFO] Módulo 'text_service' importado com sucesso.")
    
    # 2. Mostramos de qual arquivo ele foi carregado
    print(f"[INFO] Caminho do arquivo: {text_service.__file__}")
    
    # 3. A VERDADE ABSOLUTA: Listamos TUDO que existe dentro deste módulo
    print("\n--- CONTEÚDO DO MÓDULO 'text_service' ---")
    conteudo_real = dir(text_service)
    for item in conteudo_real:
        print(item)
    print("--- FIM DO CONTEÚDO ---")
    
    # 4. O Veredito Final
    if 'SynthesizeSpeechRequest' in conteudo_real:
        print("\n[VEREDITO] INACREDITÁVEL! 'SynthesizeSpeechRequest' FOI ENCONTRADO. O universo está quebrado.")
    else:
        print("\n[VEREDITO] A VERDADE! 'SynthesizeSpeechRequest' NÃO EXISTE neste arquivo.")
        print("Isso prova que a versão da biblioteca 'google-ai-generativelanguage' está DESATUALIZADA, apesar de todas as tentativas de upgrade.")
        
except ImportError:
    print("\n[FALHA] A importação de 'text_service' falhou. O problema é ainda mais estranho.")
except Exception as e:
    import traceback
    print(f"\n[ERRO INESPERADO] Ocorreu um erro: {traceback.format_exc()}")
    
print("\n--- AUTÓPSIA CONCLUÍDA ---")