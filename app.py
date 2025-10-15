import json
import logging
import requests
from spyne import Application, rpc, ServiceBase, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from spyne.model.complex import ComplexModel
from datetime import datetime

# Configuração de log
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# URL do arquivo JSON no GitHub
GITHUB_JSON_URL = "https://raw.githubusercontent.com/deciusmotta/laudo/main/laudos_gerados.json"

class LaudoResponse(ComplexModel):
    numero_laudo = Unicode
    data_emissao = Unicode
    data_validade = Unicode
    cpf_cnpj_cliente = Unicode
    nome_cliente = Unicode
    quantidade_caixas = Unicode
    modelo_caixas = Unicode

class LaudoService(ServiceBase):

    @rpc(Unicode, _returns=[LaudoResponse])
    def listar_laudos(ctx, data_emissao):
        logger.debug(f"[DEBUG] Data de emissão recebida: {data_emissao}")
        try:
            logger.debug("[DEBUG] Baixando JSON atualizado do GitHub...")
            r = requests.get(GITHUB_JSON_URL)
            r.raise_for_status()
            laudos_data = r.json()
            logger.debug(f"[DEBUG] Conteúdo do JSON obtido: {laudos_data}")
        except Exception as e:
            logger.error(f"[ERROR] Falha ao baixar/ler JSON do GitHub: {e}")
            return []

        laudos_filtrados = []
        for item in laudos_data:
            try:
                json_date = datetime.strptime(item.get("data_emissao", "").strip(), "%d/%m/%Y")
                req_date = datetime.strptime(data_emissao.strip(), "%d/%m/%Y")
                if json_date == req_date:
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
            except Exception as ex:
                logger.debug(f"[DEBUG] Ignorando item inválido: {item}, erro: {ex}")
                continue

        logger.debug(f"[DEBUG] Laudos filtrados: {laudos_filtrados}")
        return laudos_filtrados

    @rpc(Unicode, Unicode, Unicode, Unicode, Unicode, _returns=LaudoResponse)
    def gerar_laudo(ctx, nome_cliente, cpf_cnpj_cliente, quantidade_caixas, modelo_caixas, numero_laudo):
        logger.debug("[DEBUG] Gerando novo laudo...")

        laudo = {
            "numero_laudo": numero_laudo,
            "data_emissao": "2025-10-15",
            "data_validade": "2026-10-15",
            "cpf_cnpj_cliente": cpf_cnpj_cliente,
            "nome_cliente": nome_cliente,
            "quantidade_caixas": quantidade_caixas,
            "modelo_caixas": modelo_caixas
        }

        arquivo_json = "laudos_gerados.json"
        try:
            with open(arquivo_json, "r", encoding="utf-8") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    dados = []
        except FileNotFoundError:
            dados = []

        dados.append(laudo)
        with open(arquivo_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

        logger.debug(f"[DEBUG] Novo laudo gerado: {laudo}")
        return laudo

application = Application([LaudoService],
    tns="http://laudoservice.onrender.com/soap",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(application)

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    logging.info("Iniciando servidor SOAP na porta 8000...")
    server = make_server("0.0.0.0", 8000, wsgi_app)
    server.serve_forever()
