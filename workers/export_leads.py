"""
Daily cronjob to export non-converted leads to CSV and clean them from database.
Should be run at midnight via cron or similar scheduler.

Usage:
    uv run python workers/export_leads.py
"""
import csv
from datetime import datetime
from pathlib import Path

from db.session import SessionLocal
from db.models import Lead


def export_and_cleanup_leads():
    """
    Export leads that haven't purchased or booked to CSV,
    then delete them from the database.
    """
    db = SessionLocal()
    
    try:
        # Query for non-converted leads
        non_converted_leads = db.query(Lead).filter(
            Lead.has_purchased == False,
            Lead.has_booked == False
        ).all()
        
        if not non_converted_leads:
            print("✅ Nenhum lead não convertido encontrado.")
            return
        
        # Create exports directory if it doesn't exist
        exports_dir = Path(__file__).parent.parent / "exports"
        exports_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = exports_dir / f"leads_nao_convertidos_{timestamp}.csv"
        
        # Write to CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'name', 'phone', 'created_at', 'updated_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for lead in non_converted_leads:
                writer.writerow({
                    'id': lead.id,
                    'name': lead.name,
                    'phone': lead.phone,
                    'created_at': lead.created_at.isoformat(),
                    'updated_at': lead.updated_at.isoformat()
                })
        
        print(f"✅ CSV gerado: {csv_filename}")
        print(f"📊 Total de leads não convertidos: {len(non_converted_leads)}")
        
        # Delete non-converted leads from database
        for lead in non_converted_leads:
            db.delete(lead)
        
        db.commit()
        print(f"🗑️  {len(non_converted_leads)} leads não convertidos removidos do banco de dados.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao exportar/limpar leads: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Iniciando exportação de leads não convertidos...")
    export_and_cleanup_leads()
    print("✅ Processo concluído!")
