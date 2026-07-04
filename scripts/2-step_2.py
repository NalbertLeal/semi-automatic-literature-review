import json
import os
import re
import requests
import sys

from openai import OpenAI
import ollama

def processar_prompts_com_lmstudio(pasta_prompts, pasta_resultados, model):
    # Cria a pasta de resultados se ela não existir
    os.makedirs(pasta_resultados, exist_ok=True)

    # 3. Iterar sobre todos os arquivos TXT
    arquivos_txt = [f for f in os.listdir(pasta_prompts) if f.endswith('.txt')]
    total_arquivos = len(arquivos_txt)
    
    print(f"Encontrados {total_arquivos} prompts para processar.")

    results = []

    for index, nome_arquivo in enumerate(arquivos_txt, 1):
        caminho_arquivo = os.path.join(pasta_prompts, nome_arquivo)
        
        # Lê o conteúdo do prompt
        with open(caminho_arquivo, 'r', encoding='utf-8') as file:
            conteudo_prompt = file.read()
            
        print(f"[{index}/{total_arquivos}] Processando: {nome_arquivo}...")

        try:
            response = requests.post(
                "http://localhost:1234/api/v1/chat",
                headers={
                    # "Authorization": f"Bearer {os.environ['LM_API_TOKEN']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "input": '/no_think '+conteudo_prompt,
                    "temperature": 0.1,
                    "top_p": 0.1,
                }
            )

            response_json = response.json() # json.loads( response.json(), indent=2 )

            # Extrai o texto da resposta
            resultado_texto = response_json['output'][0]['content']

            # 5. Salvar a resposta
            # nome_arquivo_saida = nome_arquivo.replace('.txt', '_analise.json')
            # caminho_saida = os.path.join(pasta_resultados, nome_arquivo_saida)
            
            # with open(caminho_saida, 'w', encoding='utf-8') as file_out:
            #     file_out.write(resultado_json)
            
            pattern = r"\{(.*?)\}"
            matches = re.findall(pattern, resultado_texto, flags=re.DOTALL)
            if len(matches) == 0:
                continue

            json_result = '{' +'\"prompt_txt_file\":\"'+nome_arquivo+'\",' + matches[0]+'}'
            json_result.replace('\\', '')

            print('-'*100)
            print(json_result + '\n')
            print('-'*100)
            results.append( json.loads(json_result) )

        except json.JSONDecodeError:
             print(f"Erro: O modelo não retornou um JSON válido para o arquivo {nome_arquivo}.")
             # Salva o texto quebrado para você inspecionar o que deu errado
             with open(os.path.join(pasta_resultados, f"ERRO_{nome_arquivo}"), 'w', encoding='utf-8') as file_err:
                 file_err.write(resultado_texto)
        except Exception as e:
            print(f"Erro ao processar o arquivo {nome_arquivo}: {e}")

    json_result = json.dumps( results )

    ano = os.path.basename(pasta_prompts)
    file_path = os.path.join(pasta_resultados, ano+'.json')
    with open(file_path, 'w', encoding='utf-8') as file_out:
        file_out.write(json_result)

    print("\nProcessamento concluído!")





if __name__ == "__main__":
    print(sys.argv)
    if len(sys.argv) != 3:
        print('Tem que passar o parametro com o caminho absoluto para escrita dos prompts')
        sys.exit()
    
    pasta_prompts = sys.argv[1]
    pasta_resultados = sys.argv[2]
    
    processar_prompts_com_lmstudio(pasta_prompts, pasta_resultados, 'hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:UD-Q5_K_XL')
    # processar_prompts_com_lmstudio(pasta_prompts, pasta_resultados, 'qwen3.5-9b')
    # processar_prompts_com_lmstudio(pasta_prompts, pasta_resultados, 'llama-3.1-8b-instruct')