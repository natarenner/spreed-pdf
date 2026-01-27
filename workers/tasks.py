from datetime import datetime
from pathlib import Path

import dramatiq
import re
from dramatiq.brokers.redis import RedisBroker
from dotenv import load_dotenv
from weasyprint import HTML, CSS

load_dotenv()

from db.session import SessionLocal
from db.models import WebhookRequest, Charge
from workers.services.gdrive import upload_pdf
from workers.services.openai_client import generate_html
from workers.services.woovi import create_pix_charge
from sqlalchemy import or_
from workers.services.botconversa import ensure_subscriber_and_send_message
from workers.services.ploomes import (
    create_contact, 
    create_deal, 
    get_user_id_by_email, 
    update_deal,
    get_contact_id_by_email
)
from api.settings import api_settings


broker = RedisBroker(url=api_settings.dramatiq_broker_url)
dramatiq.set_broker(broker)


OUTPUT_DIR = Path("/tmp/pdf-output")
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


@dramatiq.actor
def process_webhook(webhook_id: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        record = db.get(WebhookRequest, webhook_id)
        if not record:
            return

        record.status = "processing"
        db.commit()

        raw_data = record.payload.get("data", {}).get("data", {})
        name = raw_data.get("os30zscm7hd00tp6qkabp90q", "Cliente").split()[0]
        email = raw_data.get("kp5n1z4vi4b63q56xh29qucc", "")
        
        # Tenta pegar o telefone para as notificações
        phone = None
        last_charge = db.query(Charge).filter(Charge.customer_email == email).order_by(Charge.created_at.desc()).first()
        if last_charge:
            phone = last_charge.customer_phone

        # --- MENSAGEM INICIAL (FEEDBACK INSTANTÂNEO) ---
        if phone:
            try:
                start_msg = (
                    f"Recebemos suas respostas do formulário com sucesso,{name}. 📝\n\n"
                    "Agora é só aguardar até o horário reservado para sua auditoria. Até lá!"
                )
                ensure_subscriber_and_send_message(phone=phone, first_name=name, message=start_msg)
                print(f"WHATSAPP: Feedback inicial enviado para {name}")
            except Exception as e:
                print(f"WHATSAPP START MSG ERROR: {e}")

        # --- GERAÇÃO DO PDF (PROCESSO PESADO) ---
        html = generate_html(record.payload)

        def render_with_height(height_mm: int):
            modified_html = re.sub(r'--pageH:\s*\d+mm\s*;', f'--pageH: {height_mm}mm;', html)
            return HTML(string=modified_html, base_url=str(ASSETS_DIR)).render(media_type="screen")

        low, high = 400, 5000
        best_height = high
        
        while low <= high:
            mid = (low + high) // 2
            doc = render_with_height(mid)
            if len(doc.pages) == 1:
                best_height = mid
                high = mid - 1
            else:
                low = mid + 1

        insta = raw_data.get("qxuxu27rubvcq0ntvodpjm0d", "").strip().lstrip("@").strip().replace(" ", "_")
        filename = f"auditoria-{insta if insta else webhook_id}-{webhook_id}.pdf"
        pdf_path = OUTPUT_DIR / filename
        
        final_doc = render_with_height(best_height)
        final_doc.write_pdf(target=str(pdf_path))
        drive_info = upload_pdf(pdf_path, filename)

        record.status = "done"
        record.pdf_filename = filename
        record.drive_file_id = drive_info.get("id")
        record.error_message = None
        db.commit()

        # --- MENSAGEM FINAL (CONCLUSÃO) ---
        if phone:
            try:
                finish_msg = (
                    f"Recebemos suas respostas da auditoria, {name}! 🙌\n\n"
                    "Muito obrigado por preencher. Nossos especialistas já estão com seus dados em mãos e te aguardam "
                    "no horário agendado para fazermos sua Auditoria Estratégica.\n\n"
                    "Até breve! 🚀"
                )
                ensure_subscriber_and_send_message(phone=phone, first_name=name, message=finish_msg)
                print(f"WHATSAPP: Mensagem de conclusão enviada para {name}")
            except Exception as e:
                print(f"WHATSAPP FINISH MSG ERROR: {e}")

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        record = db.get(WebhookRequest, webhook_id)
        if record:
            record.status = "failed"
            record.error_message = f"{type(exc).__name__}: {exc}"
            db.commit()
    finally:
        db.close()


@dramatiq.actor(max_retries=3)
def create_woovi_charge_task(charge_id: int) -> None:
    db = SessionLocal()
    try:
        charge = db.get(Charge, charge_id)
        if not charge:
            return

        payload = {
            "correlationID": charge.correlation_id,
            "value": charge.value,
            "customer": {
                "name": charge.customer_name,
                "taxID": charge.customer_tax_id,
                "email": charge.customer_email,
                "phone": charge.customer_phone,
            },
        }

        result = create_pix_charge(payload)

        # A Woovi retorna {"charge": {...}}. Se por algum erro de rede ou conflito buscarmos
        # novamente, garantimos que pegamos o objeto interno.
        charge_result = result.get("charge") if isinstance(result, dict) and "charge" in result else result
        
        # Mapeamento exato baseado no exemplo do usuário
        charge.br_code = charge_result.get("brCode")
        charge.qr_code_url = charge_result.get("qrCodeImage")
        charge.payment_link_url = charge_result.get("paymentLinkUrl")
        
        # Parse da data de expiração (formato: "2021-04-01T17:28:51.882Z")
        expires_date_str = charge_result.get("expiresDate")
        if expires_date_str:
            charge.expires_at = datetime.fromisoformat(expires_date_str.replace("Z", "+00:00"))

        print(f"WORKER SUCCESS: PIX gerado para {charge.correlation_id}")
        print(f"BRCODE: {charge.br_code[:50]}...")
            
        db.commit()
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


@dramatiq.actor(max_retries=3)
def send_purchase_confirmation_whatsapp(charge_id: int) -> None:
    db = SessionLocal()
    try:
        charge = db.get(Charge, charge_id)
        if not charge:
            return

        from urllib.parse import quote
        name_url = quote(charge.customer_name)
        email_url = quote(charge.customer_email)
        phone_url = quote(charge.customer_phone or "")
        
        cal_link = f"https://cal.com/team/spreed/auditoria?name={name_url}&email={email_url}&attendeePhoneNumber={phone_url}"

        message = (
            f"Olá {charge.customer_name}! Seu pagamento foi confirmado com sucesso. ✅\n\n"
            "Agora, *agende o horário da sua auditoria* pelo link abaixo:\n"
            f"👉 {cal_link}\n\n"
            "*Após agendar, não esqueça de preencher o formulário que será enviado para completar sua inscrição.*"
        )

        ensure_subscriber_and_send_message(
            phone=charge.customer_phone,
            first_name=charge.customer_name.split()[0],  # Use first name
            message=message
        )
        print(f"WHATSAPP: Mensagem enviada para {charge.customer_name} ({charge.customer_phone})")
    except Exception as exc:
        print(f"WHATSAPP ERROR: {exc}")
        raise exc
    finally:
        db.close()


@dramatiq.actor(max_retries=3)
def send_cal_booking_confirmation_whatsapp(phone: str, name: str) -> None:
    try:
        message = (
            f"Olá {name}! Sua reserva foi confirmada com sucesso. 📅\n\n"
            "Agora, o próximo passo é preencher o *formulário de auditoria* para que possamos analisar seu caso:\n"
            "👉 https://forms.meudominio.com/s/cmkr7p7a3000imi01peleo60g\n\n"
            "_Pode desconsiderar esta mensagem se você já preencheu o formulário anteriormente._"
        )

        ensure_subscriber_and_send_message(
            phone=phone,
            first_name=name.split()[0],
            message=message
        )
        print(f"WHATSAPP: Mensagem de agendamento enviada para {name} ({phone})")
    except Exception as exc:
        print(f"WHATSAPP CAL ERROR: {exc}")
        raise exc


@dramatiq.actor(max_retries=3)
def track_purchase_ploomes_task(charge_id: int) -> None:
    db = SessionLocal()
    try:
        charge = db.get(Charge, charge_id)
        if not charge:
            return

        # IDEMPOTÊNCIA: Se já temos o Deal ID, não fazemos nada
        if charge.ploomes_deal_id:
            print(f"PLOOMES: Negócio já existe para {charge.customer_name} (ID: {charge.ploomes_deal_id}). Pulando.")
            return

        print(f"PLOOMES: Registrando compra para {charge.customer_name}")
        
        # 1) Verifica se já temos o contato no nosso DB
        contact_id = charge.ploomes_contact_id
        
        # 2) Se não tem no DB, busca no Ploomes pelo e-mail (evita duplicidade no CRM)
        if not contact_id:
            contact_id = get_contact_id_by_email(charge.customer_email)
            if contact_id:
                print(f"PLOOMES: Contato já existe no CRM (ID: {contact_id}). Reutilizando.")
        
        # 3) Se ainda não encontrou nem no Ploomes, cria um novo
        if not contact_id:
            contact_id = create_contact(
                name=charge.customer_name,
                email=charge.customer_email,
                phone=charge.customer_phone
            )
            print(f"PLOOMES: Novo contato criado (ID: {contact_id})")
        
        # Salva o contact_id no DB
        charge.ploomes_contact_id = contact_id
        db.commit()
        
        deal_id = create_deal(
            title=f"{charge.customer_name} - Auditoria Estratégica",
            contact_id=contact_id,
            stage_id=110128040
        )
        
        charge.ploomes_deal_id = deal_id
        db.commit()
        
        print(f"PLOOMES: Negócio criado para {charge.customer_name} (ID: {deal_id})")
    except Exception as exc:
        print(f"PLOOMES PURCHASE ERROR: {exc}")
        raise exc
    finally:
        db.close()


@dramatiq.actor(max_retries=3)
def track_booking_ploomes_task(name: str, email: str, phone: str, organizer_email: str) -> None:
    db = SessionLocal()
    try:
        print(f"PLOOMES: Buscando registro para atualizar agendamento de {name}")
        
        # Tenta encontrar o registro da compra no DB para obter o deal_id
        charge = db.query(Charge).filter(
            or_(
                Charge.customer_email == email,
                Charge.customer_phone == phone
            )
        ).order_by(Charge.created_at.desc()).first()

        if not charge or not charge.ploomes_deal_id:
            print(f"PLOOMES: Nao foi encontrado negócio prévio para {name}. Ignorando update.")
            return

        # 1) Get organizer/owner ID
        next_owner_id = get_user_id_by_email(organizer_email)
        
        # 2) Update existing Deal
        try:
            update_deal(
                deal_id=charge.ploomes_deal_id,
                stage_id=110128042,
                next_owner_id=next_owner_id
            )
            print(f"PLOOMES: Negócio {charge.ploomes_deal_id} atualizado para 'Agendado' ({name})")
        except Exception as api_exc:
            # Se der 404 (Negócio excluído no Ploomes), não queremos que a fila trave
            if "404" in str(api_exc):
                print(f"PLOOMES WARNING: O negócio {charge.ploomes_deal_id} foi excluído manualmente no CRM. Ignorando update.")
            else:
                raise api_exc
    except Exception as exc:
        print(f"PLOOMES BOOKING ERROR: {exc}")
        raise exc
    finally:
        db.close()
