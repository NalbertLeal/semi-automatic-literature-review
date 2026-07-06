# export OLLAMA_FLASH_ATTENTION=1; OLLAMA_KV_CACHE_TYPE=q4_0; ollama run hf.co/unsloth/Qwen3.5-9B-GGUF:IQ4_XS 
# python scripts/process_prompts.py      ./results/2021         ./results

# ollama run hf.co/unsloth/Ministral-3-8B-Instruct-2512-GGUF:Q4_K_M
# ollama run hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M
# ollama run hf.co/unsloth/Qwen3.5-9B-GGUF:IQ4_XS

import json
import os
import re
import requests
import sys

from openai import OpenAI
import ollama

def processar_prompts_com_ollama(pasta_prompts, pasta_resultados, model):
    # 1. Definir os diretórios
    # pasta_prompts = "./prompts_gerados"
    # pasta_resultados = "./resultados_ollama"
    
    os.makedirs(pasta_resultados, exist_ok=True)

    arquivos_txt = [f for f in os.listdir(pasta_prompts) if f.endswith('.txt')]
    total_arquivos = len(arquivos_txt)
    
    # Substitua pelo nome exato do modelo que você baixou no terminal
    modelo_escolhido = model
    
    print(f"Encontrados {total_arquivos} prompts para processar com o modelo '{modelo_escolhido}'.")

    results = []

    for index, nome_arquivo in enumerate(arquivos_txt, 1):
        caminho_arquivo = os.path.join(pasta_prompts, nome_arquivo)
        
        with open(caminho_arquivo, 'r', encoding='utf-8') as file:
            conteudo_prompt = file.read()
            
        print(f"[{index}/{total_arquivos}] Processando: {nome_arquivo}...")

        try:
            # 2. Fazer a requisição para a API do Ollama
            response = ollama.chat(
                model=modelo_escolhido,
                messages=[
                    {"role": "user", "content": '/no_think '+conteudo_prompt}
                ],
                # Força a saída estritamente em formato JSON
                format='json', 
                options={
                    "num_gpu": 1000,
                    "thinking": False,
                    "enable_thinking": False,
                    "temperature": 0.1, # Mantém as respostas focadas e consistentes
                    "top_p": 0.1,
                    "top_k": 10,
                    "repeat_penalty": 1.1,
                    "num_ctx": 8192     # Aumenta a janela de contexto para 8192 tokens (crucial para abstracts grandes)
                }
            )

            # Extrai o texto da resposta
            resultado_texto = response['message']['content']

            # 3. Validar e salvar a resposta
            # nome_arquivo_saida = nome_arquivo.replace('.txt', '_analise.json')
            # caminho_saida = os.path.join(pasta_resultados, nome_arquivo_saida)
            
            # with open(caminho_saida, 'w', encoding='utf-8') as file_out:
            #     # Opcional: formata o JSON gerado para ficar bonito no arquivo (indent=4)
            #     json_formatado = json.loads(resultado_texto)
            #     json.dump(json_formatado, file_out, indent=4, ensure_ascii=False)

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



def processar_prompts_com_lmstudio(pasta_prompts, pasta_resultados, model):
    # 1. Configurar o cliente para apontar para o servidor local do LM Studio
    # A chave da API pode ser qualquer string, o LM Studio não faz validação de segurança local
    client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

    # 2. Definir os diretórios (ajuste conforme a organização do seu projeto)
    # pasta_prompts = "./prompts_gerados" # Pasta onde estão os seus TXTs
    # pasta_resultados = "./resultados_llm" # Pasta onde os JSONs serão salvos
    
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
            # 4. Fazer a requisição para a API local
            response = client.chat.completions.create(
                model=model, # O LM Studio usa automaticamente o modelo que estiver carregado na aba Local Server
                messages=[
                    {"role": "user", "content": '/no_think '+conteudo_prompt}
                ],
                extra_body={
                    "thinking": {"type": "disabled"} # Desliga o raciocínio (se suportado)
                },
                # Temperatura baixa (0.0 a 0.2) é CRÍTICA para extração de dados e JSON estruturado,
                # pois evita que o modelo "invente" respostas e foca na precisão.
                temperature=0.1,
                top_p=0.1,
                
                # Se o modelo suportar, forçamos a saída como JSON (nem todos os modelos locais respeitam, 
                # mas é uma boa prática adicionar, pois seu prompt já exige JSON).
                response_format={ "type": "json_object" },
                stream=False,
            )

            print(response)
            sys.exit()

            # Extrai o texto da resposta
            resultado_json = response.choices[0].message.content

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






def processar_prompts_com_lmstudio2(pasta_prompts, pasta_resultados, model):
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
    # processar_prompts_com_ollama(pasta_prompts, pasta_resultados, 'hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:UD-Q5_K_XL')
    # processar_prompts_com_ollama(pasta_prompts, pasta_resultados, 'hf.co/unsloth/Qwen3.5-9B-GGUF:IQ4_XS')
    # processar_prompts_com_ollama(pasta_prompts, pasta_resultados, '')
    
    # processar_prompts_com_lmstudio2(pasta_prompts, pasta_resultados, 'hf.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:UD-Q5_K_XL')
    # processar_prompts_com_lmstudio2(pasta_prompts, pasta_resultados, 'qwen3.5-9b')
    processar_prompts_com_lmstudio2(pasta_prompts, pasta_resultados, 'llama-3.1-8b-instruct')
