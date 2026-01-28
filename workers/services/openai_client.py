from pathlib import Path
from typing import Any, Dict

from openai import OpenAI

from api.settings import api_settings


def _load_assets() -> Dict[str, str]:
    assets_path = Path(__file__).resolve().parents[2] / "assets"
    import base64
    logo_path = assets_path / "logo.svg"
    logo_base64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    logo_data_uri = f"data:image/svg+xml;base64,{logo_base64}"
    
    return {
        "template": (assets_path / "auditoria_template.html").read_text(encoding="utf-8"),
        "css": (assets_path / "auditoria.css").read_text(encoding="utf-8"),
        "logo_uri": logo_data_uri
    }



QUESTION_MAP = {
    "name": "Qual o seu nome completo?",
    "email": "Seu melhor E-mail",
    "instagram": "Seu @ do Instagram",
    "nicho": "1) Qual é o seu nicho principal?",
    "objetivo": "2) Qual é o objetivo principal do seu perfil?",
    "publico": "3) Quem é o seu público ideal?",
    "oque_vende": "4) O que você vende hoje?",
    "ticket_medio": "5) Qual é o ticket médio do seu produto/serviço principal?",
    "clientes_mes": "6) Quantos clientes você consegue atender por mês?",
    "total_seguidores": "7) Quantos seguidores você tem hoje?",
    "postagens_semana": "8) Quantas postagens você faz por semana?",
    "formato_conteudo": "9) Qual é o seu formato principal de conteúdo?",
    "media_reels": "10) Qual é sua média de visualizações nos Reels?",
    "taxa_conversao": "11) Sua taxa aproximada de conversão (seguidores → clientes) é:",
    "crescimento_redes": "12) Como você descreve seu crescimento atual nas redes sociais?",
    "tempo_insta": "13) Quanto tempo você dedica ao Instagram por dia?",
    "meta_seguidores": "14) Qual é sua meta de seguidores para os próximos 6 meses?",
    "meta_faturamento_mensal": "15) Qual é sua meta mensal de faturamento?",
    "faturamento_medio_atual": "16) Qual é o faturamento médio mensal atual?",
}


def generate_html(payload: Dict[str, Any]) -> str:
    client = OpenAI(api_key=api_settings.openai_api_key)
    assets = _load_assets()

    system_prompt = (
        "Você é um especialista sênior em marketing digital, branding e estratégia de autoridade. "
        "Sua missão é transformar dados brutos de um formulário em uma Auditoria Estratégica Premium. "
        "O texto deve ser persuasivo, autoritário, mas ao mesmo tempo acolhedor e altamente estratégico. "
        "Inspire-se em auditorias de alto nível: use termos como 'Alavancagem de Autoridade', 'Escalabilidade Digital', 'Público Qualificado' e 'Lacunas de Conversão'. "
        "IMPORTANTE: Você deve retornar APENAS o código HTML preenchido. "
        "Adicione ao texto final quantos % (de 0 a 60%) qual é chance que pessoa tem de viralizar para atingir os resultados desejados baseado APENAS nas respostas do formulário. E o que ela precisa fazer para começar a viralizar de uma forma estruturada e escalável."
        "Importante: queremos uma margem de melhora, ou seja, apenas de 0 à 60% apenas, exemplo: Sua taxa de viralização é entre 30% a 60% por causa de..."
        "Enriqueça o texto com insights estratégicos baseados nos dados fornecidos. E uma conclusão elaborada e técnica com pelo menos 10 linhas."
        "MANTENHA EXATAMENTE as classes CSS e a estrutura do template fornecido. "
        "Não use blocos de Markdown como ```html ... ```. Retorne o texto puro do HTML.."
    )

    # Map IDs to questions
    raw_data = payload.get("data", {}).get("data", {})
    
    # Sanitize Instagram handle (remove @ and whitespace)
    if "instagram" in raw_data and isinstance(raw_data["instagram"], str):
        raw_data["instagram"] = raw_data["instagram"].strip().lstrip("@").strip()

    mapped_data = {QUESTION_MAP.get(k, k): v for k, v in raw_data.items()}
    user_prompt = (
        f"Dados do cliente capturados no formulário:\n{mapped_data}\n\n"
        f"Use este Template HTML para preencher as informações:\n{assets['template']}\n\n"
        "Instruções cruciais de preenchimento:\n"
        "1. Substitua os placeholders {{field}} pelo conteúdo gerado.\n"
        "2. {{nome_completo}}, {{instagram}} e {{nicho_principal}} devem ser extraídos fielmente dos dados.\n"
        "3. {{resumo_executivo}} deve ser um texto curto (2-3 linhas) impactante sobre o momento atual do cliente.\n"
        "4. {{ticket_medio}}, {{meta_seguidores}}, etc, devem ser formatados de forma bonita (ex: R$ 500,00 ou 50k).\n"
        "5. Os campos terminados em '_html' devem conter uma estrutura estratégica rica (use <p>, <ul>, <li>, <strong>).\n"
        "6. O tone deve ser de um consultor premium que realmente analisou os dados e está dando o caminho das pedras.\n"
        "7. Não substitua o placeholder {{logo_url}}, deixe-o exatamente como está.\n"
        "8. Não use placeholders ou textos genéricos. Gere insights reais baseados no nicho e público informado."
    )

    response = client.responses.create(
        model=api_settings.openai_model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    # Pegamos o texto gerado da estrutura de Responses
    html = ""
    if hasattr(response, "output_text"):
        html = response.output_text.strip()
    
    if not html:
        # Fallback para percorrer a lista de output caso output_text não esteja disponível
        for item in response.output or []:
            for content in item.content or []:
                if getattr(content, "text", None):
                    html = content.text.strip()
                    break
            if html:
                break

    # Remove markdown code blocks if the AI included them
    if html.startswith("```"):
        # Remove first line if it's ```html or ```
        lines = html.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        html = "\n".join(lines).strip()

    # Injeta o logo real no lugar do placeholder
    html = html.replace("{{logo_url}}", assets["logo_uri"])

    # Inject CSS into the <head>
    css_style = f"<style>{assets['css']}</style>"
    if "</head>" in html:
        html = html.replace("</head>", f"{css_style}\n</head>")
    else:
        html = f"{css_style}\n{html}"

    return html


if __name__ == "__main__":
    # Payload de teste simulando as respostas do formulário
    test_payload = {
        "data": {
            "data": {
                "name": "Natan Spreed",
                "email": "natan@spreed.ai",
                "instagram": "natanspreed",
                "nicho": "Infoprodutor / Educação Online",
                "objetivo": "Vender mentorias de automação e escala",
                "publico": "Empreendedores digitais faturando acima de 10k/mês",
                "oque_vende": "Mentoria de Escala com IA",
                "ticket_medio": "R$ 5.000,00",
                "clientes_mes": "10",
                "total_seguidores": "15.400",
                "postagens_semana": "7 posts e infinitos stories",
                "formato_conteudo": "Reels e Carrosséis Técnicos",
                "media_reels": "5k a 10k",
                "taxa_conversao": "2% a 5%",
                "crescimento_redes": "Crescimento constante mas estagnado no faturamento",
                "tempo_insta": "4 horas",
                "meta_seguidores": "50.000",
                "meta_faturamento_mensal": "R$ 100.000,00",
                "faturamento_medio_atual": "R$ 25.000,00",
            }
        }
    }

    try:
        print("🚀 Gerando auditoria de teste...")
        result_html = generate_html(test_payload)
        
        # Salva o resultado em um arquivo HTML para você abrir no navegador
        output_file = "test_auditoria.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_html)
            
        print(f"✅ HTML gerado com sucesso: {output_file}")
        print("💡 Abra este arquivo no seu navegador para ver o resultado!")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
