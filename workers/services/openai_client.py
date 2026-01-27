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
    "os30zscm7hd00tp6qkabp90q": "Qual o seu nome completo?",
    "kp5n1z4vi4b63q56xh29qucc": "Seu melhor E-mail",
    "qxuxu27rubvcq0ntvodpjm0d": "Seu @ do Instagram",
    "vx6qkcwblt53wv8dnaqchih4": "1) Qual é o seu nicho principal?",
    "yfr6nkshb10u5ti1cxjswuqp": "2) Qual é o objetivo principal do seu perfil?",
    "i5d6nazh8tcbrr2myi2e947y": "3) Quem é o seu público ideal?",
    "souo56m9fmv8sqb0sbk8gjli": "4) O que você vende hoje?",
    "fu5kn4hvizxp9rr2bk94oeos": "5) Qual é o ticket médio do seu produto/serviço principal?",
    "glvh90gl5tkzeg1wng36ktqe": "6) Quantos clientes você consegue atender por mês?",
    "uookpj515mmrd9kmp5nm6x0r": "7) Quantos seguidores você tem hoje?",
    "let97ou6szewi8t6jy10jao2": "8) Quantas postagens você faz por semana?",
    "ppmyppicazkuu3kz3990dz17": "9) Qual é o seu formato principal de conteúdo?",
    "ks56y6w0jvbgbq5edrd3yc33": "10) Qual é sua média de visualizações nos Reels?",
    "jhbs540l5uxdg790u1a5tszr": "11) Sua taxa aproximada de conversão (seguidores → clientes) é:",
    "pwq7k6pu5d6dar9033u78f31": "12) Como você descreve seu crescimento atual nas redes sociais?",
    "s354uknjwoj9xfubtute3kyt": "13) Quanto tempo você dedica ao Instagram por dia?",
    "iivcze2c1om40x9w3pa6fc8m": "14) Qual é sua meta de seguidores para os próximos 6 meses?",
    "v9osxzrbno0un8z2cwhxfzcm": "15) Qual é sua meta mensal de faturamento?",
    "lth71by3o7on8ubznk66ip33": "16) Qual é o faturamento médio mensal atual?",
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
        "Adicione ao texto final quantos % (de 0 a 60%) a pessoa tem de viralizar para atingir os resultados desejados.E o que ela precisa fazer para começar a viralizar de uma forma estruturada e escalável."
        "Enriqueça o texto com insights estratégicos baseados nos dados fornecidos."
        "MANTENHA EXATAMENTE as classes CSS e a estrutura do template fornecido. "
        "Não use blocos de Markdown como ```html ... ```. Retorne o texto puro do HTML.."
    )

    # Map IDs to questions
    raw_data = payload.get("data", {}).get("data", {})
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
                "os30zscm7hd00tp6qkabp90q": "Natan Spreed",
                "kp5n1z4vi4b63q56xh29qucc": "natan@spreed.ai",
                "qxuxu27rubvcq0ntvodpjm0d": "natanspreed",
                "vx6qkcwblt53wv8dnaqchih4": "Infoprodutor / Educação Online",
                "yfr6nkshb10u5ti1cxjswuqp": "Vender mentorias de automação e escala",
                "i5d6nazh8tcbrr2myi2e947y": "Empreendedores digitais faturando acima de 10k/mês",
                "souo56m9fmv8sqb0sbk8gjli": "Mentoria de Escala com IA",
                "fu5kn4hvizxp9rr2bk94oeos": "R$ 5.000,00",
                "glvh90gl5tkzeg1wng36ktqe": "10",
                "uookpj515mmrd9kmp5nm6x0r": "15.400",
                "let97ou6szewi8t6jy10jao2": "7 posts e infinitos stories",
                "ppmyppicazkuu3kz3990dz17": "Reels e Carrosséis Técnicos",
                "ks56y6w0jvbgbq5edrd3yc33": "5k a 10k",
                "jhbs540l5uxdg790u1a5tszr": "2% a 5%",
                "pwq7k6pu5d6dar9033u78f31": "Crescimento constante mas estagnado no faturamento",
                "s354uknjwoj9xfubtute3kyt": "4 horas",
                "iivcze2c1om40x9w3pa6fc8m": "50.000",
                "v9osxzrbno0un8z2cwhxfzcm": "R$ 100.000,00",
                "lth71by3o7on8ubznk66ip33": "R$ 25.000,00",
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
