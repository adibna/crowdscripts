import requests
import time
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
# Configurações do YETI
YETI_BASE_URL = "http://localhost:8000"  # Altere para o IP/Domínio do seu Yeti
YETI_API_KEY = "SUA_YETI_API_KEY_AQUI"

# Configurações do CROWDSTRIKE
CS_CLIENT_ID = "SEU_CS_CLIENT_ID"
CS_CLIENT_SECRET = "SEU_CS_CLIENT_SECRET"
CS_BASE_URL = "https://api.crowdstrike.com" # Verifique se é us-1, us-2 ou eu-1

# --- CLASSE PARA O YETI (Baseada na sua documentação) ---
class YetiClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.token = None

    def authenticate(self):
        """Obtém o JWT token usando a API Key conforme documentação."""
        endpoint = f"{self.base_url}/api/v2/auth/api-token"
        headers = {"x-yeti-apikey": self.api_key}
        
        try:
            response = requests.post(endpoint, headers=headers)
            response.raise_for_status()
            self.token = response.json().get("access_token")
            # Atualiza a sessão para usar o token em chamadas futuras
            self.session.headers.update({"authorization": f"Bearer {self.token}"})
            print("[Yeti] Autenticado com sucesso.")
        except Exception as e:
            print(f"[Yeti] Erro na autenticação: {e}")
            raise

    def import_observables(self, observables_list, tags=["crowdstrike"]):
        """Importa uma lista de observables via endpoint de texto."""
        if not observables_list:
            print("[Yeti] Nenhum observable para importar.")
            return

        endpoint = f"{self.base_url}/api/v2/observables/import/text"
        
        # Converte a lista para uma string única separada por quebras de linha
        observables_text = "\n".join(observables_list)
        
        payload = {
            "text": observables_text,
            "tags": tags
        }

        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            print(f"[Yeti] Sucesso! {len(observables_list)} observables enviados.")
            return response.json()
        except Exception as e:
            print(f"[Yeti] Erro ao importar observables: {e}")

# --- CLASSE PARA O CROWDSTRIKE FALCON ---
class CrowdStrikeClient:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.headers = {}

    def authenticate(self):
        """Autenticação OAuth2 padrão do CrowdStrike."""
        endpoint = f"{self.base_url}/oauth2/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        try:
            response = requests.post(endpoint, data=data)
            response.raise_for_status()
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print("[CS] Autenticado com sucesso.")
        except Exception as e:
            print(f"[CS] Erro na autenticação: {e}")
            raise

    def get_recent_detections(self, minutes_back=60):
        """Busca IDs de detecções recentes."""
        endpoint = f"{self.base_url}/detects/queries/detects/v1"
        
        # Filtro FQL para pegar detecções recentes
        # Nota: Ajuste o filtro conforme a necessidade
        filter_query = f"created_timestamp: > 'now-{minutes_back}m'"
        
        params = {"filter": filter_query, "limit": 50}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("resources", [])
        except Exception as e:
            print(f"[CS] Erro ao buscar detecções: {e}")
            return []

    def get_detection_details(self, detection_ids):
        """Busca os detalhes das detecções para extrair IOCs."""
        if not detection_ids:
            return []
            
        endpoint = f"{self.base_url}/detects/entities/summaries/v1"
        
        # O CS aceita múltiplos IDs no body
        payload = {"ids": detection_ids}
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json().get("resources", [])
        except Exception as e:
            print(f"[CS] Erro ao buscar detalhes: {e}")
            return []

# --- LÓGICA DE INTEGRAÇÃO ---
def extract_iocs_from_cs_data(detections):
    """
    Analisa o JSON de detecção do CS e extrai IPs, Domínios e Hashes.
    Essa função precisa ser ajustada dependendo de onde o IOC reside no JSON da detecção
    (ex: behaviors, device destination, etc).
    """
    iocs = set() # Usamos set para evitar duplicatas
    
    for det in detections:
        # Exemplo: Pegando o IOA ou IOC associado ao comportamento
        behaviors = det.get("behaviors", [])
        for behavior in behaviors:
            # Tenta pegar hash MD5/SHA256 se disponível
            if "md5" in behavior: iocs.add(behavior["md5"])
            if "sha256" in behavior: iocs.add(behavior["sha256"])
            # Tenta pegar domínio ou IP de comando e controle
            if "domain" in behavior: iocs.add(behavior["domain"])
            if "ipv4" in behavior: iocs.add(behavior["ipv4"])
            
    return list(iocs)

def main():
    print("--- Iniciando Integração CrowdStrike -> Yeti ---")
    
    # 1. Instancia os clientes
    yeti = YetiClient(YETI_BASE_URL, YETI_API_KEY)
    cs = CrowdStrikeClient(CS_BASE_URL, CS_CLIENT_ID, CS_CLIENT_SECRET)

    # 2. Autentica
    try:
        yeti.authenticate()
        cs.authenticate()
    except:
        print("Falha crítica na autenticação. Abortando.")
        return

    # 3. Busca detecções no CrowdStrike (últimos 60 min)
    detection_ids = cs.get_recent_detections(minutes_back=60)
    print(f"[CS] Detecções encontradas: {len(detection_ids)}")

    if detection_ids:
        # 4. Busca detalhes para extrair os dados reais
        details = cs.get_detection_details(detection_ids)
        
        # 5. Extrai IOCs (Hash, IP, Domínio)
        extracted_iocs = extract_iocs_from_cs_data(details)
        print(f"[Int] IOCs extraídos: {extracted_iocs}")

        # 6. Envia para o Yeti
        if extracted_iocs:
            yeti.import_observables(extracted_iocs, tags=["crowdstrike", "detection", "high-severity"])
        else:
            print("[Int] Nenhum IOC válido encontrado nos detalhes das detecções.")
    else:
        print("[Int] Nenhuma nova detecção para processar.")

if __name__ == "__main__":
    main()
