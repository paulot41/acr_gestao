from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Organization, ProtocolConfiguration, Instructor, Resource, Modality, Person,
    GoverningBody, GoverningBodyMember
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

        # 7. Órgãos Sociais da Associação ACR (Mandato 2024–2028)
        term = "2024–2028"
        start_d = date(2024, 1, 15)
        end_d = date(2028, 1, 14)
        election_d = date(2024, 1, 12)

        # Direção
        board, _ = GoverningBody.objects.get_or_create(
            organization=org,
            body_type=GoverningBody.BodyType.BOARD,
            term_label=term,
            defaults={
                "start_date": start_d,
                "end_date": end_d,
                "election_date": election_d,
                "is_active": True,
                "electoral_minutes_ref": "Ata n.º 01/2024 da Assembleia Eleitoral da ACR",
                "notes": "Direção executiva em exercício ordinário de funções estatutárias.",
            }
        )
        board_roles = [
            ("Paulo Sérgio da Cunha Teixeira", "Presidente da Direção", 1, "Representante Legal da ACR"),
            ("António José Silva", "Vice-Presidente", 2, "Pelouro de Desporto e Instalações"),
            ("Manuel Carvalho", "Tesoureiro", 3, "Gestão Financeira e Controlo Orçamental"),
            ("Maria João Costa", "Secretária", 4, "Atas, Expediente e Registo de Sócios"),
            ("Joaquim Ribeiro", "Vogal", 5, "Apoio a Eventos e Relações Institucionais"),
        ]
        for name, role, order, notes in board_roles:
            GoverningBodyMember.objects.get_or_create(
                governing_body=board,
                name=name,
                defaults={"role": role, "order": order, "notes": notes}
            )

        # Mesa da Assembleia Geral
        assembly, _ = GoverningBody.objects.get_or_create(
            organization=org,
            body_type=GoverningBody.BodyType.GENERAL_ASSEMBLY,
            term_label=term,
            defaults={
                "start_date": start_d,
                "end_date": end_d,
                "election_date": election_d,
                "is_active": True,
                "electoral_minutes_ref": "Ata n.º 01/2024 da Assembleia Eleitoral da ACR",
                "notes": "Mesa condutora dos trabalhos da Assembleia Geral.",
            }
        )
        assembly_roles = [
            ("Fernando Moreira", "Presidente da Mesa", 1, "Convocatória e Direção das Assembleias"),
            ("Rui Pereira", "1.º Secretário", 2, "Redação de Atas"),
            ("Ana Ramos", "2.ª Secretária", 3, "Apoio ao Escrutínio e Caderno Eleitoral"),
        ]
        for name, role, order, notes in assembly_roles:
            GoverningBodyMember.objects.get_or_create(
                governing_body=assembly,
                name=name,
                defaults={"role": role, "order": order, "notes": notes}
            )

        # Conselho Fiscal
        fiscal, _ = GoverningBody.objects.get_or_create(
            organization=org,
            body_type=GoverningBody.BodyType.FISCAL_COUNCIL,
            term_label=term,
            defaults={
                "start_date": start_d,
                "end_date": end_d,
                "election_date": election_d,
                "is_active": True,
                "electoral_minutes_ref": "Ata n.º 01/2024 da Assembleia Eleitoral da ACR",
                "notes": "Fiscalização de contas e emissão de pareceres obrigatórios.",
            }
        )
        fiscal_roles = [
            ("José Barbosa", "Presidente do Conselho Fiscal", 1, "Fiscalização e Relatório de Contas"),
            ("Vítor Martins", "Relator", 2, "Elaboração de Pareceres de Gestão"),
            ("Teresa Fernandes", "Vogal", 3, "Verificação Patrimonial e Documental"),
        ]
        for name, role, order, notes in fiscal_roles:
            GoverningBodyMember.objects.get_or_create(
                governing_body=fiscal,
                name=name,
                defaults={"role": role, "order": order, "notes": notes}
            )

        # 9. Configurar Grupos e Permissões Oficiais (ACR vs ProForm)
        from django.core.management import call_command
        from django.contrib.auth.models import User, Group
        from core.models import UserProfile

        call_command("setup_roles_and_permissions")

        # 10. Utilizadores Institucionais de Referência
        # 10.1 Paulo Teixeira (Presidente da Direção da Associação ACR)
        paulo_user, p_created = User.objects.get_or_create(
            username="paulo.teixeira",
            defaults={
                "first_name": "Paulo",
                "last_name": "Teixeira",
                "email": "paulo.t.41@gmail.com",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if p_created:
            paulo_user.set_password("acr_direcao_2026")
            paulo_user.save()

        UserProfile.objects.update_or_create(
            user=paulo_user,
            organization=org,
            defaults={
                "user_type": UserProfile.UserType.ACR_DIRECTION,
                "entity_affiliation": UserProfile.EntityAffiliation.ACR_ONLY,
                "can_view_finances": True,
                "can_manage_bookings": True,
                "can_view_all_clients": True,
                "can_create_events": True,
            }
        )
        dir_acr_group = Group.objects.filter(name="Direção ACR").first()
        if dir_acr_group:
            paulo_user.groups.add(dir_acr_group)

        # 10.2 Daniel Coelho (Diretor Técnico Oficial do ProForm)
        daniel_user, d_created = User.objects.get_or_create(
            username="daniel.coelho",
            defaults={
                "first_name": "Daniel",
                "last_name": "Coelho",
                "email": "daniel.coelho@proform.pt",
                "is_staff": True,
                "is_superuser": False,
            }
        )
        if d_created:
            daniel_user.set_password("proform_dt_2026")
            daniel_user.save()

        UserProfile.objects.update_or_create(
            user=daniel_user,
            organization=org,
            defaults={
                "user_type": UserProfile.UserType.PROFORM_DIRECTOR,
                "entity_affiliation": UserProfile.EntityAffiliation.PROFORM_ONLY,
                "instructor": daniel,
                "can_view_finances": True,
                "can_manage_bookings": True,
                "can_view_all_clients": True,
                "can_create_events": True,
            }
        )
        dt_pf_group = Group.objects.filter(name="Direção Técnica Proform").first()
        if dt_pf_group:
            daniel_user.groups.add(dt_pf_group)

        self.stdout.write(self.style.SUCCESS(
            f"Parametrização concluída com sucesso! Organização: '{org.name}'\n"
            f"• Apólice: {config.insurance_policy_number} ({config.insurance_company})\n"
            f"• Mediador: {config.broker_name} (ASF: {config.broker_asf_number})\n"
            f"• Diretor Técnico: {daniel.full_name} (Cédula: {daniel.ipdj_license_number})\n"
            f"• Espaço: {pavilhao.name} ({pavilhao.get_facility_type_display()})\n"
            f"• Órgãos Sociais da ACR: Mandato {term} (Direção, Mesa AG, Conselho Fiscal)\n"
            f"• Utilizadores de Referência configurados: 'paulo.teixeira' (Direção ACR) e 'daniel.coelho' (Direção Técnica ProForm)\n"
            f"• Atletas registados/atualizados: {created_count} criados de {len(initial_athletes)} da pasta oficial."
        ))
