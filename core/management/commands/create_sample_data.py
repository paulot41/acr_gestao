from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Organization, Resource, Modality, Instructor, Person
from django.utils import timezone


class Command(BaseCommand):
    help = 'Popula a base de dados com dados de exemplo para teste do sistema multi-entidade (ACR + Proform)'

    def handle(self, *args, **options):
        # Criar organização de exemplo com configurações multi-entidade
        org, created = Organization.objects.get_or_create(
            domain='acr.local',
            defaults={
                'name': 'ACR + Proform',
                'org_type': 'both',
                'gym_monthly_fee': 35.00,
                'wellness_monthly_fee': 50.00
            }
        )
        if created:
            self.stdout.write(f"✅ Organização: {org.name} criada")
        else:
            # Atualizar organização existente com novos campos
            org.org_type = 'both'
            org.gym_monthly_fee = 35.00
            org.wellness_monthly_fee = 50.00
            org.save()
            self.stdout.write(f"✅ Organização: {org.name} atualizada para multi-entidade")

        # Criar utilizador admin se não existir
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@acr.local', 'admin123')
            self.stdout.write("✅ Utilizador admin criado (admin/admin123)")

        # Criar os espaços para ACR e Proform
        spaces = [
            {'name': 'Ginásio', 'capacity': 25},  # ACR
            {'name': 'Sala de Pilates', 'capacity': 12},  # Proform
            {'name': 'Pavilhão', 'capacity': 30},  # ACR
            {'name': 'Sala de Yoga', 'capacity': 15},  # Proform
        ]

        for space_data in spaces:
            resource, created = Resource.objects.get_or_create(
                organization=org,
                name=space_data['name'],
                defaults={'capacity': space_data['capacity']}
            )
            status = "criado" if created else "já existe"
            self.stdout.write(f"✅ Espaço: {resource.name} ({resource.capacity} pessoas) - {status}")

        # Criar modalidades para ACR e Proform
        modalities = [
            # Modalidades ACR (Ginásio)
            {
                'name': 'Musculação', 'entity_type': 'acr',
                'description': 'Treino com pesos e máquinas',
                'duration': 60, 'capacity': 25, 'color': '#0d6efd', 'price': 5.00
            },
            {
                'name': 'CrossFit', 'entity_type': 'acr',
                'description': 'Treino funcional de alta intensidade',
                'duration': 45, 'capacity': 16, 'color': '#fd7e14', 'price': 12.00
            },
            {
                'name': 'Cardio', 'entity_type': 'acr',
                'description': 'Treino cardiovascular intenso',
                'duration': 30, 'capacity': 20, 'color': '#dc3545', 'price': 8.00
            },

            # Modalidades Proform (Pilates/Wellness)
            {
                'name': 'Pilates', 'entity_type': 'proform',
                'description': 'Exercícios de fortalecimento e flexibilidade',
                'duration': 50, 'capacity': 12, 'color': '#198754', 'price': 15.00
            },
            {
                'name': 'Yoga', 'entity_type': 'proform',
                'description': 'Prática de yoga e meditação',
                'duration': 60, 'capacity': 15, 'color': '#6f42c1', 'price': 18.00
            },
            {
                'name': 'Stretching', 'entity_type': 'proform',
                'description': 'Alongamento e mobilidade',
                'duration': 45, 'capacity': 10, 'color': '#20c997', 'price': 12.00
            },

            # Modalidades mistas
            {
                'name': 'Personal Training', 'entity_type': 'both',
                'description': 'Treino personalizado individual',
                'duration': 60, 'capacity': 1, 'color': '#ffc107', 'price': 35.00
            },
        ]

        for mod_data in modalities:
            modality, created = Modality.objects.get_or_create(
                organization=org,
                name=mod_data['name'],
                defaults={
                    'description': mod_data['description'],
                    'default_duration_minutes': mod_data['duration'],
                    'max_capacity': mod_data['capacity'],
                    'color': mod_data['color'],
                    'entity_type': mod_data['entity_type'],
                    'price_per_class': mod_data['price'],
                }
            )
            status = "criada" if created else "já existe"
            entity_display = {"acr": "ACR", "proform": "Proform", "both": "Ambas"}[mod_data['entity_type']]
            self.stdout.write(f"✅ Modalidade: {modality.name} ({entity_display}) - {status}")

        # Criar instrutores para ACR e Proform
        instructors = [
            # Instrutores ACR
            {
                'first_name': 'João', 'last_name': 'Silva', 'email': 'joao@acr.local',
                'phone': '912345678', 'specialties': 'Musculação, CrossFit',
                'entity_affiliation': 'acr_only', 'acr_commission': 65.00, 'proform_commission': 70.00
            },
            {
                'first_name': 'Pedro', 'last_name': 'Costa', 'email': 'pedro@acr.local',
                'phone': '914567890', 'specialties': 'Cardio, Funcional',
                'entity_affiliation': 'acr_only', 'acr_commission': 60.00, 'proform_commission': 65.00
            },

            # Instrutores Proform
            {
                'first_name': 'Maria', 'last_name': 'Santos', 'email': 'maria@proform.local',
                'phone': '913456789', 'specialties': 'Pilates, Yoga',
                'entity_affiliation': 'proform_only', 'acr_commission': 60.00, 'proform_commission': 75.00
            },
            {
                'first_name': 'Ana', 'last_name': 'Ferreira', 'email': 'ana@proform.local',
                'phone': '915678901', 'specialties': 'Yoga, Stretching, Meditação',
                'entity_affiliation': 'proform_only', 'acr_commission': 60.00, 'proform_commission': 75.00
            },

            # Instrutor que trabalha em ambas
            {
                'first_name': 'Carlos', 'last_name': 'Oliveira', 'email': 'carlos@acrproform.local',
                'phone': '916789012', 'specialties': 'Personal Training, Pilates, Musculação',
                'entity_affiliation': 'both', 'acr_commission': 70.00, 'proform_commission': 75.00
            },
        ]

        for inst_data in instructors:
            instructor, created = Instructor.objects.get_or_create(
                organization=org,
                email=inst_data['email'],
                defaults={
                    'first_name': inst_data['first_name'],
                    'last_name': inst_data['last_name'],
                    'phone': inst_data['phone'],
                    'specialties': inst_data['specialties'],
                    'entity_affiliation': inst_data['entity_affiliation'],
                    'acr_commission_rate': inst_data['acr_commission'],
                    'proform_commission_rate': inst_data['proform_commission'],
                }
            )
            status = "criado" if created else "já existe"
            entity_display = {
                "acr_only": "ACR", "proform_only": "Proform", "both": "ACR + Proform"
            }[inst_data['entity_affiliation']]
            self.stdout.write(f"✅ Instrutor: {instructor.full_name} ({entity_display}) - {status}")

        # Criar clientes com diferentes afiliações
        clients = [
            # Clientes só ACR
            {
                'first_name': 'Miguel', 'last_name': 'Pereira', 'email': 'miguel@exemplo.com',
                'phone': '920123456', 'nif': '111111111', 'entity_affiliation': 'acr_only'
            },
            {
                'first_name': 'Rui', 'last_name': 'Mendes', 'email': 'rui@exemplo.com',
                'phone': '921234567', 'nif': '222222222', 'entity_affiliation': 'acr_only'
            },

            # Clientes só Proform
            {
                'first_name': 'Sofia', 'last_name': 'Rodrigues', 'email': 'sofia@exemplo.com',
                'phone': '922345678', 'nif': '333333333', 'entity_affiliation': 'proform_only'
            },
            {
                'first_name': 'Carla', 'last_name': 'Alves', 'email': 'carla@exemplo.com',
                'phone': '923456789', 'nif': '444444444', 'entity_affiliation': 'proform_only'
            },

            # Clientes em ambas entidades
            {
                'first_name': 'André', 'last_name': 'Silva', 'email': 'andre@exemplo.com',
                'phone': '924567890', 'nif': '555555555', 'entity_affiliation': 'both'
            },
            {
                'first_name': 'Patrícia', 'last_name': 'Costa', 'email': 'patricia@exemplo.com',
                'phone': '925678901', 'nif': '666666666', 'entity_affiliation': 'both'
            },
        ]

        for client_data in clients:
            # Verificar se já existe cliente com esse email ou NIF
            existing_client = Person.objects.filter(
                organization=org,
                email=client_data['email']
            ).first()

            if existing_client:
                # Atualizar cliente existente se necessário
                existing_client.entity_affiliation = client_data['entity_affiliation']
                existing_client.save()
                monthly_fee = existing_client.get_monthly_fee()
                entity_display = {
                    "acr_only": "ACR", "proform_only": "Proform", "both": "ACR + Proform"
                }[client_data['entity_affiliation']]
                self.stdout.write(f"✅ Cliente: {existing_client.full_name} ({entity_display}) - €{monthly_fee}/mês - atualizado")
            else:
                # Criar novo cliente
                person = Person.objects.create(
                    organization=org,
                    **client_data
                )
                monthly_fee = person.get_monthly_fee()
                entity_display = {
                    "acr_only": "ACR", "proform_only": "Proform", "both": "ACR + Proform"
                }[client_data['entity_affiliation']]
                self.stdout.write(f"✅ Cliente: {person.full_name} ({entity_display}) - €{monthly_fee}/mês - criado")

        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 SISTEMA MULTI-ENTIDADE CRIADO COM SUCESSO!\n'
                '================================================\n'
                f'📍 Organização: {org.name}\n'
                f'🏋️  ACR (Ginásio): €{org.gym_monthly_fee}/mês\n'
                f'🧘 Proform (Pilates): €{org.wellness_monthly_fee}/mês\n'
                '\n📊 Dados criados:\n'
                f'   • 4 espaços (Ginásio, Pilates, Pavilhão, Yoga)\n'
                f'   • 7 modalidades (3 ACR, 3 Proform, 1 mista)\n'
                f'   • 5 instrutores (2 ACR, 2 Proform, 1 ambos)\n'
                f'   • 6 clientes (2 ACR, 2 Proform, 2 ambos)\n'
                '\n🌐 Acesso ao sistema:\n'
                '   URL: http://localhost:8000/admin/\n'
                '   Login: admin / admin123\n'
                '\n✨ Funcionalidades disponíveis:\n'
                '   • Interface admin integrada\n'
                '   • Gestão multi-entidade (ACR + Proform)\n'
                '   • Cálculo automático de mensalidades\n'
                '   • Comissões configuráveis por instrutor\n'
                '   • Sistema Gantt para 4 espaços\n'
            )
        )
