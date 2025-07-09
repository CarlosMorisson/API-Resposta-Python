# run.py
import uvicorn

if __name__ == "__main__":
    # Este script inicia o servidor de forma programática.
    # Isso força o Python a usar o ambiente virtual correto,
    # contornando o problema do seu sistema.
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)