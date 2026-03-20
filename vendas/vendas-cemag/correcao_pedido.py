import os
import json
import requests
import google.generativeai as genai
import instructor
from pydantic import BaseModel, Field
from typing import List, Dict, Literal, Optional
from dotenv import load_dotenv

# 1. Configuração Inicial
# ------------------------------------------------------------------
load_dotenv()

# Verifica se a chave existe
if not os.environ.get("GOOGLE_API_KEY"):
    raise ValueError("A chave GOOGLE_API_KEY não foi encontrada no arquivo .env")

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Configura o cliente Instructor com Gemini 1.5 Flash (Rápido e barato)
client = instructor.from_gemini(
    client=genai.GenerativeModel(model_name="models/gemini-1.5-flash"),
    mode=instructor.Mode.GEMINI_JSON,
)

# 2. Definição dos Modelos de Dados (O "Contrato" de Entrada e Saída)
# ------------------------------------------------------------------

class ResultadoAnalise(BaseModel):
    """Estrutura exata que o Agente deve retornar."""
    
    status: Literal["APROVADO", "CORRIGIDO", "IMPOSSIVEL_DETERMINAR"] = Field(
        ..., description="Status final do produto após processar a observação."
    )
    codigo_final: str = Field(
        ..., description="O código do produto (SKU) final, recalculado com base nas mudanças."
    )
    alteracoes_detectadas: Dict[str, str] = Field(
        ..., description="Dicionário com 'campo': 'novo_valor' para tudo que mudou baseada na observação. Ex: {'cor': 'Azul'}."
    )
    raciocinio: str = Field(
        ..., description="Breve explicação de como a IA deduziu o novo código ou as mudanças."
    )

# 3. Integração com a API Externa (O "Cérebro" Dinâmico)
# ------------------------------------------------------------------

def buscar_referencias_api(classe_produto: str = None, limit: int = 5) -> List[dict]:
    """
    Busca produtos 'exemplares' na API para ensinar o padrão ao Agente.
    """
    # URL DA SUA API AQUI
    # Se você ainda não tem a URL subida, troque por um mock/lista fixa para testar
    API_URL = "https://cemag.innovaro.com.br/api/publica/v1/tabelas/listarProdutos" 
    
    try:
        # Exemplo de chamada real (descomente e ajuste quando tiver a URL)
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        dados = response.json()
        print(dados)
        return dados.get("produtos", []) # Ajuste conforme o retorno real da sua API
        
        # --- MOCK (SIMULAÇÃO) PARA VOCÊ RODAR AGORA ---
        # Estou retornando os dados que você me passou no exemplo
        # return [
        #     {
        #         "codigo": "CBHM5000 GR SS RD M17",
        #         "modelo": "CBHM5000",
        #         "molaFreio": "SS",
        #         "rodado": "RD",
        #         "descGenerica": "Graneleira",
        #         "cor": "Laranja"
        #     },
        #     {
        #         "codigo": "CBHM2000 SC RS M25",
        #         "modelo": "CBHM2000",
        #         "molaFreio": "SC",
        #         "rodado": "RS",
        #         "descGenerica": "Uso Geral",
        #         "cor": "Laranja"
        #     }
        # ]

    except Exception as e:
        print(f"⚠️ Erro ao buscar referências na API: {e}")
        return [] # Retorna vazio para não quebrar o fluxo, o agente tentará sem exemplos

# 4. O Agente Inteligente
# ------------------------------------------------------------------

def processar_produto_com_ia(produto_atual: dict) -> ResultadoAnalise:
    """
    Função principal que orquestra a busca de exemplos e a chamada à IA.
    """
    
    # Passo A: Buscar contexto dinâmico
    print(f"🔄 Buscando referências para classe: {produto_atual.get('classe', 'Geral')}...")
    exemplos = buscar_referencias_api(classe_produto=produto_atual.get("classe"))
    
    # Passo B: Montar o Prompt
    # O segredo está em instruir a IA a priorizar a 'observacao'
    prompt_sistema = f"""
    Você é um Engenheiro de Configuração de Produtos.
    
    SUA MISSÃO:
    1. Analise o produto recebido e o campo 'observacao'. A 'observacao' é MANDATÓRIA e sobrescreve qualquer dado existente.
    2. Se a observação pedir mudanças (ex: "quero azul", "com freio"), altere os campos técnicos virtuais.
    3. Recalcule o campo 'codigo' para refletir essas mudanças, baseando-se no padrão dos EXEMPLOS DE REFERÊNCIA.
    
    --- EXEMPLOS DE REFERÊNCIA (APRENDA O PADRÃO DAQUI) ---
    {json.dumps(exemplos, indent=2)}
    -------------------------------------------------------
    
    REGRAS DE OURO:
    - Se a observação alterar um componente que faz parte do código (como Rodado ou Mola), o código DEVE mudar.
    - Se a observação alterar algo que não está no código (ex: apenas a Cor, se a cor não fizer parte da string do código), mantenha o código original.
    - Mantenha sufixos numéricos (como M17) se não houver instrução para mudá-los.
    """

    # Passo C: Chamar o Gemini
    print("🤖 Agente analisando...")
    return client.chat.completions.create(
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Produto para processar: {json.dumps(produto_atual)}"}
        ],
        response_model=ResultadoAnalise,
        max_retries=2 # Se o JSON vier quebrado, ele tenta de novo automaticamente
    )

# 5. Execução de Teste
# ------------------------------------------------------------------

if __name__ == "__main__":
    # Cenário: Produto padrão, mas o cliente pediu uma alteração na observação
    produto_input = {
        "codigo": "CBHM5000 GR SS RD M17",
        "modelo": "CBHM5000",
        "classe": "Carretas Basculantes",
        "molaFreio": "SS", # SS = Sem Suspensão
        "rodado": "RD",
        "cor": "Laranja",
        "observacao": "Cliente solicitou alteração para incluir Freios (SC) e pintura Azul."
    }

    try:
        resultado = processar_produto_com_ia(produto_input)
        
        print("\n" + "="*40)
        print("RESULTADO DO AGENTE")
        print("="*40)
        print(f"STATUS: {resultado.status}")
        print(f"CÓDIGO FINAL: {resultado.codigo_final}")
        print(f"ALTERAÇÕES: {json.dumps(resultado.alteracoes_detectadas, indent=2)}")
        print(f"RACIOCÍNIO: {resultado.raciocinio}")
        print("="*40)
        
    except Exception as e:
        print(f"❌ Ocorreu um erro fatal: {e}")