from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Organization
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Configuração inicial do sistema para produção'

    def add_arguments(self, parser):
        parser.add_argument('--create-superuser', action='store_true', help='Criar superusuário')
        parser.add_argument('--create-org', type=str, help='Criar organização com domínio')
        parser.add_argument('--org-name', type=str, help='Nome da organização')

    def handle(self, *args, **options):
        self.stdout.write("=== Configuração Inicial ACR Gestão ===")

        # Criar superusuário se solicitado
        if options['create_superuser']:
            self.create_superuser()

        # Criar organização se solicitado
        if options['create_org']:
            self.create_organization(options['create_org'], options.get('org_name'))

        self.stdout.write(self.style.SUCCESS("✅ Configuração concluída!"))

    def create_superuser(self):
        """Criar superusuário se não existir"""
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("ℹ️ Superusuário já existe")
            return

        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

        if not password:
            self.stdout.write(self.style.ERROR("❌ Defina DJANGO_SUPERUSER_PASSWORD"))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"✅ Superusuário criado: {username}"))

    def create_organization(self, domain, name=None):
        """Criar organização se não existir"""
        if Organization.objects.filter(domain=domain).exists():
            self.stdout.write(f"ℹ️ Organização {domain} já existe")
            return

        org_name = name or domain.split('.')[0].title()
        org = Organization.objects.create(name=org_name, domain=domain)
        self.stdout.write(self.style.SUCCESS(f"✅ Organização criada: {org_name} ({domain})"))
