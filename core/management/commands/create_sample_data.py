from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Organization, Resource, Modality, Instructor, Person
from django.utils import timezone


class Command(BaseCommand):
    help = 'Popula a base de dados com dados de exemplo para teste'

    def handle(self, *args, **options):
        # Criar organização de exemplo
        org, created = Organization.objects.get_or_create(
            domain='acr.local',
            defaults={'name': 'ACR Ginásio'}
        )
        self.stdout.write(f"Organização: {org.name} {'criada' if created else 'já existe'}")

        # Criar utilizador admin se não existir
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@acr.local', 'admin123')
            self.stdout.write("Utilizador admin criado (admin/admin123)")

        # Criar os 3 espaços principais
        spaces = [
            {'name': 'Ginásio', 'capacity': 20},
            {'name': 'Sala de Pilates', 'capacity': 15},
            {'name': 'Pavilhão', 'capacity': 30},
        ]

        for space_data in spaces:
            resource, created = Resource.objects.get_or_create(
                organization=org,
                name=space_data['name'],
                defaults={'capacity': space_data['capacity']}
            )
            self.stdout.write(f"Espaço: {resource.name} {'criado' if created else 'já existe'}")

        # Criar modalidades
        modalities = [
            {'name': 'Musculação', 'description': 'Treino com pesos e máquinas', 'duration': 60, 'capacity': 20, 'color': '#0d6efd'},
            {'name': 'Pilates', 'description': 'Exercícios de fortalecimento e flexibilidade', 'duration': 45, 'capacity': 15, 'color': '#198754'},
            {'name': 'Cardio', 'description': 'Treino cardiovascular intenso', 'duration': 30, 'capacity': 25, 'color': '#dc3545'},
            {'name': 'Yoga', 'description': 'Prática de yoga e meditação', 'duration': 60, 'capacity': 12, 'color': '#6f42c1'},
            {'name': 'CrossFit', 'description': 'Treino funcional de alta intensidade', 'duration': 45, 'capacity': 16, 'color': '#fd7e14'},
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
                }
            )
            self.stdout.write(f"Modalidade: {modality.name} {'criada' if created else 'já existe'}")

        # Criar instrutores
        instructors = [
            {'first_name': 'João', 'last_name': 'Silva', 'email': 'joao@acr.local', 'phone': '912345678', 'specialties': 'Musculação, CrossFit'},
            {'first_name': 'Maria', 'last_name': 'Santos', 'email': 'maria@acr.local', 'phone': '913456789', 'specialties': 'Pilates, Yoga'},
            {'first_name': 'Pedro', 'last_name': 'Costa', 'email': 'pedro@acr.local', 'phone': '914567890', 'specialties': 'Cardio, Funcional'},
        ]

        for inst_data in instructors:
            instructor, created = Instructor.objects.get_or_create(
                organization=org,
                email=inst_data['email'],
                defaults=inst_data
            )
            self.stdout.write(f"Instrutor: {instructor.full_name} {'criado' if created else 'já existe'}")

        # Criar clientes de exemplo
        clients = [
            {'first_name': 'Ana', 'last_name': 'Pereira', 'email': 'ana@exemplo.com', 'phone': '920123456', 'nif': '123456789'},
            {'first_name': 'Carlos', 'last_name': 'Oliveira', 'email': 'carlos@exemplo.com', 'phone': '921234567', 'nif': '234567890'},
            {'first_name': 'Sofia', 'last_name': 'Rodrigues', 'email': 'sofia@exemplo.com', 'phone': '922345678', 'nif': '345678901'},
            {'first_name': 'Miguel', 'last_name': 'Ferreira', 'email': 'miguel@exemplo.com', 'phone': '923456789', 'nif': '456789012'},
        ]

        for client_data in clients:
            person, created = Person.objects.get_or_create(
                organization=org,
                email=client_data['email'],
                defaults=client_data
            )
            self.stdout.write(f"Cliente: {person.full_name} {'criado' if created else 'já existe'}")

        self.stdout.write(
            self.style.SUCCESS(
                '\n✅ Dados de exemplo criados com sucesso!\n'
                'Pode agora aceder ao sistema em: http://localhost:8000\n'
                'Login: admin / admin123'
            )
        )
