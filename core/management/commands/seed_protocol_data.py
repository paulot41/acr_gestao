from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Organization, ProtocolConfiguration, Instructor, Resource, Modality, Person
)


class Command(BaseCommand):
    help = "Carrega e sincroniza os dados reais e oficiais do Protocolo ACR & Proform SC."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("A inicializar parametrização oficial do Protocolo..."))

        # 1. Obter ou criar a organização unificada
        org = Organization.objects.filter(domain__in=["acr.local", "testserver"]).first()
        if not org:
            org, _ = Organization.objects.get_or_create(
                name="ACR & Proform SC",
                domain="acr.local",
                defaults={"org_type": Organization.Type.BOTH}
            )

        # 2. Diretor Técnico Oficial (Daniel Coelho)
        daniel, created = Instructor.objects.get_or_create(
            organization=org,
            first_name="Daniel",
            last_name="Coelho",
            defaults={
                "email": "daniel.coelho@proform.pt",
                "phone": "+351 910 000 000",
                "specialties": "Direção Técnica, Treino Funcional, Força & Condicionamento",
                "entity_affiliation": Instructor.EntityAffiliation.PROFORM_ONLY,
                "is_technical_director": True,
                "ipdj_license_number": "97575",
                "ipdj_license_expiry": date(2027, 12, 31),
                "ipdj_project_name": "Protocolo ACR-Proform / Artes Marciais",
                "acr_commission_rate": Decimal("60.00"),
                "proform_commission_rate": Decimal("70.00"),
                "is_active": True,
            }
        )
        if not created:
            daniel.is_technical_director = True
            daniel.ipdj_license_number = "97575"
            daniel.save()

        # 3. Parametrização Dinâmica do Protocolo e Apólice Generali
        config, cfg_created = ProtocolConfiguration.objects.get_or_create(
            organization=org,
            defaults={
                "acr_official_name": "ACR - Associação Cultural e Recreativa de Basto (Santa Tecla)",
                "acr_nipc": "510695744",
                "acr_address": "Lugar da Igreja, 4890-526 Basto (Santa Tecla)",
                "acr_representative_name": "Paulo Sérgio da Cunha Teixeira",
                "acr_representative_role": "Presidente da Direção",

                "proform_official_name": "PROFORM - Strength & Conditioning",
                "proform_nipc": "210263601",
                "proform_address": "Rua Senhora da Conceição 24, 4890-223 Celorico de Basto",
                "proform_representative_name": "Daniel Silvério Leite Coelho",
                "proform_representative_role": "Diretor Técnico",

                "active_technical_director": daniel,
                "active_ipdj_project": "Protocolo de Desportos de Combate e Artes Marciais (ACR & Proform SC)",

                "insurance_company": "Generali Seguros, S.A.",
                "insurance_policy_number": "0010189147",
                "insurance_product_name": "AP DESP CULT RECREIO - Ginásios com artes marciais",
                "insurance_policy_start": date(2025, 8, 19),
                "insurance_policy_expiry": date(2026, 8, 18),
                "insurance_annual_premium": Decimal("362.82"),
                "insurance_base_insured_count": 25,
                "insurance_claim_deadline_days": 3,

                "capital_death_disability": Decimal("33500.00"),
                "capital_treatment": Decimal("5500.00"),
                "treatment_deductible": Decimal("75.00"),
                "capital_funeral": Decimal("3000.00"),

                "broker_name": "SPR AGENTE SEGUROS LDA",
                "broker_asf_number": "4195560913",
                "broker_phone": "963 958 018",
                "broker_address": "Av. João Pinto Ribeiro 98 Fracção A, 4890-221 Celorico de Basto",

                "acr_admin_fee_per_athlete": Decimal("1.00"),
                "insurance_split_mode": ProtocolConfiguration.InsuranceSplitMode.MONTHLY_AMORTIZATION,
            }
        )
        if not cfg_created and not config.active_technical_director:
            config.active_technical_director = daniel
            config.save()

        # 4. Instalações / Espaço Municipal Cedido
        pavilhao, _ = Resource.objects.get_or_create(
            organization=org,
            name="Pavilhão da Antiga C+S",
            defaults={
                "description": "Pavilhão desportivo cedido pelo Município para a prática de artes marciais e desportos de combate.",
                "capacity": 25,
                "entity_type": Resource.EntityType.BOTH,
                "facility_type": Resource.FacilityType.MUNICIPAL_CESSION,
                "cession_entity": "Município de Celorico de Basto",
                "address": "Celorico de Basto",
                "is_available": True,
            }
        )

        # 5. Modalidades Oficiais
        for mod_name in ["Kickboxing", "Jiu-Jitsu", "Boxe"]:
            Modality.objects.get_or_create(
                organization=org,
                name=mod_name,
                defaults={
                    "description": f"Modalidade desportiva amadora de {mod_name} ao abrigo do protocolo ACR & Proform SC.",
                    "entity_type": Modality.EntityType.BOTH,
                    "default_duration_minutes": 60,
                    "is_active": True,
                }
            )

        # 6. Carregamento dos Atletas Existentes das Fichas Físicas
        initial_athletes = [
            ("Mariana", "Silva", "mariana.silva@exemplo.pt", Person.MemberCategory.SOCIO),
            ("Leonardo", "Alves", "leonardo.alves@exemplo.pt", Person.MemberCategory.NAO_SOCIO),
            ("Marcos", "Gonçalves", "marcos.goncalves@exemplo.pt", Person.MemberCategory.SOCIO),
            ("Claudia", "Miguel", "claudia.miguel@exemplo.pt", Person.MemberCategory.NAO_SOCIO),
            ("Tiago", "Leite", "tiago.leite@exemplo.pt", Person.MemberCategory.SOCIO),
            ("Catarina", "Ramada", "catarina.ramada@exemplo.pt", Person.MemberCategory.NAO_SOCIO),
            ("Carlos", "Silva", "carlos.silva@exemplo.pt", Person.MemberCategory.SOCIO),
            ("Pedro", "Guimarães", "pedro.guimaraes@exemplo.pt", Person.MemberCategory.SOCIO),
            ("Marisa", "Palmeira", "marisa.palmeira@exemplo.pt", Person.MemberCategory.NAO_SOCIO),
            ("Leonel", "Rodrigues", "leonel.rodrigues@exemplo.pt", Person.MemberCategory.SOCIO),
            ("Ivo", "Santos", "ivo.santos@exemplo.pt", Person.MemberCategory.NAO_SOCIO),
        ]

        created_count = 0
        for fname, lname, mail, cat in initial_athletes:
            person, p_created = Person.objects.get_or_create(
                organization=org,
                first_name=fname,
                last_name=lname,
                defaults={
                    "email": mail,
                    "status": Person.Status.ACTIVE,
                    "entity_affiliation": Person.EntityAffiliation.BOTH,
                    "member_category": cat,
                    "insurance_policy": config.insurance_policy_number,
                    "insurance_expiry": config.insurance_policy_expiry,
                    "consent_rgpd": True,
                    "regulation_accepted": True,
                    "image_consent": True,
                }
            )
            if p_created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Parametrização concluída com sucesso! Organização: '{org.name}'\n"
            f"• Apólice: {config.insurance_policy_number} ({config.insurance_company})\n"
            f"• Mediador: {config.broker_name} (ASF: {config.broker_asf_number})\n"
            f"• Diretor Técnico: {daniel.full_name} (Cédula: {daniel.ipdj_license_number})\n"
            f"• Espaço: {pavilhao.name} ({pavilhao.get_facility_type_display()})\n"
            f"• Atletas registados/atualizados: {created_count} criados de {len(initial_athletes)} da pasta oficial."
        ))
