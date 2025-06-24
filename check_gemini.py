# check_gemini.py - Diagnóstico Completo

print("--- INICIANDO TESTE DE DIAGNÓSTICO PROFUNDO ---")

try:
    # Passo 1: Importar o módulo
    import google.generativeai as genai
    print("✅ SUCESSO: Módulo 'google.generativeai' importado.")
    print("-" * 50)

    # Passo 2: Informações Cruciais do Módulo
    print("INFORMAÇÕES DO MÓDULO:")
    try:
        print(f"  - Versão detectada: {genai.__version__}")
    except AttributeError:
        print("  - Versão detectada: Não foi possível encontrar o atributo __version__ (indica versão muito antiga).")
        
    print(f"  - Caminho do arquivo: {genai.__file__}")
    print("-" * 50)

    # Passo 3: Listar TODOS os atributos e funções disponíveis
    print("ATRIBUTOS E FUNÇÕES DISPONÍVEIS NO MÓDULO 'genai':")
    
    available_items = [item for item in dir(genai) if not item.startswith('_')]
    
    if not available_items:
        print("  Nenhum atributo público encontrado.")
    else:
        for item in sorted(available_items):
            print(f"  - {item}")
    print("-" * 50)

    # Passo 4: Verificar especificamente pelas funções que precisamos
    print("VERIFICAÇÃO DE FUNÇÕES-CHAVE PARA TTS:")
    
    tts_functions_to_check = ['text_to_speech', 'synthesize_speech']
    found_any_tts = False

    for func_name in tts_functions_to_check:
        if hasattr(genai, func_name):
            print(f"  ✅ SUCESSO: A função '{func_name}' FOI ENCONTRADA!")
            found_any_tts = True
        else:
            print(f"  ❌ FALHA: A função '{func_name}' NÃO foi encontrada.")
    
    if not found_any_tts:
         print("\nAVISO: Nenhuma das funções TTS padrão foi encontrada. Isso confirma uma versão antiga da biblioteca.")
    
    print("-" * 50)

except ImportError:
    print("❌ FALHA CRÍTICA: Não foi possível importar a biblioteca 'google-generativeai'.")
    print("   Verifique se a biblioteca foi instalada no ambiente correto com 'pip install google-generativeai'.")
except Exception as e:
    print(f"❌ Ocorreu um erro inesperado: {e}")

print("--- TESTE DE DIAGNÓSTICO CONCLUÍDO ---")