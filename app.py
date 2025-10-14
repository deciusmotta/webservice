from flask import Flask, Response
from spyne import Application, rpc, ServiceBase, Unicode, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from datetime import datetime, timedelta
import json
import os
import requests
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Modelo de resposta ---
class LaudoResponse(ComplexModel):
    numero_laudo = Unicode
    data_emissao = Unicode
    data_validade = Unicode
    cpf_cnpj_cliente = Unicode
    nome_cliente = Unicode
    quantidade_caixas = Unicode
    modelo_caixas = Unicode

# URL do JSON no GitHub
# GITHUB_JSON_URL = "https://raw.githubusercontent.com/deciusmotta/laudo/main/laudos_gerados.json"
GITHUB_JSON_URL = "https://raw.githubusercontent.com/deciusmotta/laudo/refs/heads/main/laudos_gerados.json?token=GHSAT0AAAAAADMFTX6GPJXX2KHS4J46OOJ62HOVY2A"

# --- Serviço SOAP ---
class LaudoService(ServiceBase):

    @rpc(Unicode, Unicode, Unicode, Unicode, Unicode, _returns=LaudoResponse)
    def gerar_laudo(ctx, nome_cliente, cpf_cnpj_cliente, quantidade_caixas, modelo_caixas, numero_laudo):
        data_emissao = datetime.now().strftime("%d/%m/%Y")
        data_validade = (datetime.now() + timedelta(days=15)).strftime("%d/%m/%Y")

        laudo = {
            "numero_laudo": numero_laudo,
            "data_emissao": data_emissao,
            "data_validade": data_validade,
            "cpf_cnpj_cliente": cpf_cnpj_cliente,
            "nome_cliente": nome_cliente,
            "quantidade_caixas": quantidade_caixas,
            "modelo_caixas": modelo_caixas
        }

        arquivo_json = os.path.join(os.path.dirname(__file__), "laudos_gerados.json")

        # Baixa JSON do GitHub se não existir
        if not os.path.exists(arquivo_json):
            try:
                r = requests.get(GITHUB_JSON_URL)
                r.raise_for_status()
                with open(arquivo_json, "w", encoding="utf-8") as f:
                    f.write(r.text)
                logger.debug("[DEBUG] Arquivo JSON baixado do GitHub.")
            except Exception as e:
                logger.debug(f"[ERROR] Não foi possível baixar o JSON: {e}")
                return LaudoResponse(**laudo)  # Retorna apenas o laudo atual

        # Lê, adiciona e salva
        with open(arquivo_json, "r", encoding="utf-8") as f:
            try:
                dados = json.load(f)
            except json.JSONDecodeError:
                dados = []

        dados.append(laudo)
        with open(arquivo_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

        return LaudoResponse(**laudo)

    @rpc(Unicode, _returns=[LaudoResponse])
    def listar_laudos(ctx, data_emissao):
        logger.debug(f"[DEBUG] Parâmetro recebido: {data_emissao}")  # <- deve mostrar "14/10/2025"
        arquivo_json = os.path.join(os.path.dirname(__file__), "laudos_gerados.json")
        logger.debug(f"[DEBUG] Caminho do JSON: {arquivo_json}")
        logger.debug(f"[DEBUG] Data de emissão recebida: {data_emissao}")
        logger.debug(f"Caminho do JSON: {arquivo_json}")
        logger.debug(f"Data recebida: {data_emissao}")

        # Baixa JSON do GitHub se não existir local
        if not os.path.exists(arquivo_json):
            try:
                r = requests.get(GITHUB_JSON_URL)
                r.raise_for_status()
                with open(arquivo_json, "w", encoding="utf-8") as f:
                    f.write(r.text)
                logger.debug("[DEBUG] Arquivo JSON baixado do GitHub.")
            except Exception as e:
                logger.debug(f"[ERROR] Não foi possível baixar o JSON: {e}")
                return []

        # Lê JSON
        with open(arquivo_json, "r", encoding="utf-8") as f:
            try:
                laudos_data = json.load(f)
                logger.debug(f"[DEBUG] Conteúdo do JSON: {laudos_data}")
            except json.JSONDecodeError:
                logger.debug("[DEBUG] Erro ao decodificar JSON.")
                return []

        # Filtra por data de emissão
        laudos_filtrados = []
        for item in laudos_data:
            if item.get("data_emissao") == data_emissao:
                laudo = LaudoResponse(
                    numero_laudo=item.get("numero_laudo", ""),
                    data_emissao=item.get("data_emissao", ""),
                    data_validade=item.get("data_validade", ""),
                    cpf_cnpj_cliente=item.get("cpf_cnpj_cliente", ""),
                    nome_cliente=item.get("nome_cliente", ""),
                    quantidade_caixas=item.get("quantidade_caixas", ""),
                    modelo_caixas=item.get("modelo_caixas", "")
                )
                laudos_filtrados.append(laudo)

        logger.debug(f"[DEBUG] Laudos filtrados: {laudos_filtrados}")
        return laudos_filtrados


# --- Configuração SOAP ---
soap_app = Application(
    [LaudoService],
    tns="http://laudoservice.onrender.com/soap",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11()
)
wsgi_app = WsgiApplication(soap_app)
app.wsgi_app = wsgi_app

# --- Rota de verificação ---
@app.route("/")
def home():
    return "Serviço SOAP de Laudos ativo e funcional!"

# --- Rota para servir o WSDL ---
@app.route("/wsdl")
def wsdl():
    wsdl_path = os.path.join(os.path.dirname(__file__), "laudoservice.wsdl")
    if not os.path.exists(wsdl_path):
        return Response("WSDL não encontrado.", status=404)
    with open(wsdl_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content, mimetype="text/xml")

# --- Inicialização ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
