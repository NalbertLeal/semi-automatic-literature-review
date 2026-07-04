import os
import re
import sys

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def processar_journal_dsn(prompts_abs_path: str):
    # Passo 4: Template inicial do prompt para os modelos do LM Studio
#     prompt_template = """Você é um assistente de pesquisa acadêmica avaliando artigos para uma revisão sistemática da literatura.
# Com base no Título, Abstract e Keywords abaixo, determine se o artigo deve prosseguir para a próxima etapa da revisão.

# Título: {titulo}
# Abstract: {abstract}

# Responda apenas com "RELEVANTE" ou "IRRELEVANTE" e justifique em uma única linha."""

    prompt_template = '''Role: You are a Senior Computer Science Researcher and an expert in Distributed Systems and Dependability.

Task: Your objective is to act as a rigorous screening assistant for a systematic literature review. You will analyze the [TITLE], [ABSTRACT], and [KEYWORDS] of a paper published at the DSN (Dependable Systems and Networks) conference and classify it as VALID, INVALID, or UNCERTAIN based on strict inclusion and exclusion criteria.

INCLUSION CRITERIA (ALL must be satisfied):
1. Target Domain (Intersection Required):
The paper MUST be primarily about Distributed Systems. Additionally, the distributed system's context or application MUST strictly fall into at least one of these specific domains:
- Wireless Sensor Networks (WSN)
- Internet of Things (IoT)
- Blockchain Systems
- Cyber-Physical Systems (CPS)
- Cloud Computing
- Data Centers
- High-Performance Computing (HPC)
- P2P networks
2. Fault Tolerance Focus:
Fault tolerance or dependability MUST be a major and explicit research contribution, proposed method, or primary evaluation focus. The paper must substantially address topics such as: Fault Tolerance, Dependability, Reliability, Availability, Resilience, Failure Detection/Recovery, Byzantine Fault Tolerance (BFT), Replication, Checkpointing, Redundancy, Self-Healing, or Crash Recovery.
(Papers mentioning fault tolerance only as motivation, background, or future work do not meet this criterion).
3. Study Type:
The paper must be a primary research study (proposing a method, framework, algorithm, or empirical evaluation).

EXCLUSION CRITERIA (If ANY match, classify as INVALID):
1. Hardware-Level Only: The fault tolerance approach is exclusively focused on low-level hardware (e.g., bit flips, radiation on chips) without a distributed system/network level approach.
2. Non-Primary Studies: The paper is a Survey, Systematic Literature Review (SLR), or Review.
3. Tangential Focus: The primary focus is strictly on Energy Efficiency, Routing Protocols, pure Telecommunications, Data Analytics, Artificial Intelligence, or Security/Privacy, UNLESS fault tolerance is explicitly proven to be the major co-contribution.

MANDATORY UNCERTAINTY RULE (CRITICAL):
If the abstract lacks sufficient detail, uses ambiguous language, or if you cannot reach ABSOLUTE CERTAINTY regarding the acceptance or rejection of the paper based on the criteria above, you MUST output "UNCERTAIN" as the final_label. Do NOT guess, infer missing data, or make assumptions. When in doubt, your default action must be UNCERTAIN.

INPUT DATA (the paper to analyse):
[TITLE]: {titulo}
[ABSTRACT]: {abstract}

OUTPUT FORMAT:
You must return ONLY a valid JSON object. Do not include markdown formatting like ```json or any conversational text. The JSON must strictly follow this structure:

{{
"chain_of_thought_analysis": "Write 3 to 4 sentences reasoning step-by-step. 1. Identify domain fit. 2. Analyze fault tolerance contribution. 3. Check exclusions. 4. Explicitly state whether the text provides enough information to be absolutely certain of the decision.",
"identified_domains": ["List the matched domains, e.g., Distributed Systems, IoT"],
"fault_tolerance_evidence": "Quote a short phrase from the abstract that proves fault tolerance is a major contribution, or write 'None' if absent.",
"exclusion_reason": "If rejected, state the exact exclusion criterion met. If accepted or uncertain, write null.",
"confidence_score": "0.0 to 1.0. IMPORTANT: If this score is less than 0.80, the final_label below MUST be UNCERTAIN.",
"final_label": "VALID | INVALID | UNCERTAIN"
}}'''

    anos_interesse = ['2021', '2022', '2023', '2024', '2025']

    with sync_playwright() as p:
        # Inicia o navegador em modo headless (invisível)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Passo 1: Acessar a página principal do journal
        url_base = "https://www.computer.org/csdl/proceedings/1000192"
        print(f"Acessando base: {url_base}")
        page.goto(url_base, wait_until="networkidle")
        
        soup_base = BeautifulSoup(page.content(), 'html.parser')
        
        # Passo 2: Acessar cada um dos anos (2021 até 2025)
        links_anos = []
        for tag_a in soup_base.find_all('a', href=True):
            texto_link = tag_a.text.strip()
            # Filtra links que contenham o ano alvo e que façam parte da DSN
            if any(ano == texto_link for ano in anos_interesse) and '/dsn/' in tag_a['href'].lower():
                url_ano = tag_a['href']
                # Ajusta rotas relativas
                if url_ano.startswith('/'):
                    url_ano = "https://www.computer.org" + url_ano
                links_anos.append(url_ano)
        
        links_anos = list(set(links_anos)) # Remove duplicatas

        links_anos = sorted(links_anos)

        # Passo 3: Na página do journal de cada ano, coletar os artigos
        for link_ano in links_anos:
            print(f"\n--- Processando edição anual: {link_ano} ---")
            page.goto(link_ano, wait_until="networkidle")
            soup_ano = BeautifulSoup(page.content(), 'html.parser')

            ano = link_ano[46:50]
            
            links_artigos = []
            for tag_a in soup_ano.find_all('a', href=True):
                # O padrão da URL de artigos publicados contém 'proceedings-article'
                if '/proceedings-article/dsn/' in tag_a['href'].lower():
                    url_artigo = tag_a['href']
                    if url_artigo.startswith('/'):
                        url_artigo = "https://www.computer.org" + url_artigo
                    links_artigos.append(url_artigo)
            
            links_artigos = list(set(links_artigos))
            
            for link_artigo in links_artigos:
                print(f"Extraindo artigo: {link_artigo}")
                page.goto(link_artigo, wait_until="networkidle")
                soup_artigo = BeautifulSoup(page.content(), 'html.parser')
                
                # Extração do Título
                h1_tag = soup_artigo.find('h1')
                titulo = h1_tag.text.strip() if h1_tag else "Título não encontrado"
                
                # Extração do Abstract
                element_selector = '#page-content-wrapper > csdl-proceeding-article > div > div > div.col-lg-6.col-md-7 > div > article > csdl-article-full-text > article > div.article-content.mt-lg.mb-lg'
                abstract_tag = soup_artigo.find('div', class_=re.compile("article-content", re.I)) #abstract

                valid_abstract = (abstract_tag.text is not None) and (type(abstract_tag.text) == str) and (abstract_tag.text != '')
                abstract = "Abstract não encontrado"
                if not valid_abstract:
                    continue
                else:
                    abstract = abstract_tag.text.strip()
                
                # Passo 4 (Conclusão): Aplica os elementos no template
                prompt_final = prompt_template.format(
                    titulo=titulo,
                    abstract=abstract
                )
                
                print("\n> Prompt Gerado:")
                print(prompt_final)
                print("\n" + "="*100 + "\n")

                cleantext = re.sub(r'[^a-zA-Z0-9 ]', '', titulo)
                filename =  '_'.join( cleantext.split(' ') ) + '.txt'
                file_path = os.path.join(prompts_abs_path, ano, filename)
                with open(file_path, 'w') as f:
                    f.write(prompt_final)
                
                # Pausa de 2 segundos para evitar bloqueios de IP (Rate Limiting) pela plataforma
                page.wait_for_timeout(2000)

        browser.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Tem que passar o parametro com o caminho absoluto para escrita dos prompts')
        sys.exit()

    prompts_abs_path = sys.argv[1]
    processar_journal_dsn(prompts_abs_path)