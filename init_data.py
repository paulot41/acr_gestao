import os
import sys
import django
import logging
from django.db.utils import IntegrityError, OperationalError
from django.core.exceptions import ValidationError

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acr_gestao.settings')
django.setup()

from core.models import Organization, Modality, Resource, Instructor

logger = logging.getLogger(__name__)

def create_initial_data():
    print("🚀 Criando dados iniciais para desenvolvimento local...")

    # Criar organização localhost
    org_local, created = Organization.objects.get_or_create(
        domain='localhost',
        defaults={
            'name': 'ACR Gestão - Desenvolvimento Local',
            'org_type': 'both',
            'gym_monthly_fee': 30.00,
            'wellness_monthly_fee': 45.00,
            'primary_color': '#0d6efd',
            'secondary_color': '#6c757d'
        }
    )
    print(f"✅ Organização: {org_local.name} ({'criada' if created else 'já existe'})")

    # Criar modalidades com cores personalizadas
    modalities_data = [
        {
            'name': 'Musculação',
            'entity_type': 'acr',
            'color': '#dc3545',
            'duration': 60,
            'capacity': 15
        },
        {
            'name': 'Cardio',
            'entity_type': 'acr',
            'color': '#fd7e14',
            'duration': 45,
            'capacity': 12
        },
        {
            'name': 'Pilates',
            'entity_type': 'proform',
            'color': '#28a745',
            'duration': 60,
            'capacity': 10
        },
        {
            'name': 'Yoga',
            'entity_type': 'proform',
            'color': '#6f42c1',
            'duration': 75,
            'capacity': 8
        }
    ]

    for mod_data in modalities_data:
        modality, created = Modality.objects.get_or_create(
            organization=org_local,
            name=mod_data['name'],
            defaults={
                'entity_type': mod_data['entity_type'],
                'color': mod_data['color'],
                'default_duration_minutes': mod_data['duration'],
                'max_capacity': mod_data['capacity'],
                'is_active': True
            }
        )
        print(f"✅ Modalidade: {modality.name} ({'criada' if created else 'já existe'})")

    # Criar recursos/espaços
    resources_data = [
        {
            'name': 'Sala de Musculação',
            'entity_type': 'acr',
            'capacity': 25,
            'equipment': 'Máquinas de musculação, halteres, barras',
            'features': 'Ar condicionado, espelhos, som ambiente'
        },
        {
            'name': 'Sala Cardio',
            'entity_type': 'acr',
            'capacity': 15,
            'equipment': 'Passadeiras, bicicletas, elípticas',
            'features': 'Ventilação, TVs, música'
        },
        {
            'name': 'Estúdio Pilates',
            'entity_type': 'proform',
            'capacity': 10,
            'equipment': 'Colchões, bolas, elásticos, reformer',
            'features': 'Luz natural, espelhos, ambiente zen'
        },
        {
            'name': 'Sala Polivalente',
            'entity_type': 'both',
            'capacity': 20,
            'equipment': 'Equipamento versátil para várias modalidades',
            'features': 'Espaço amplo, som, iluminação ajustável'
        }
    ]

    for res_data in resources_data:
        resource, created = Resource.objects.get_or_create(
            organization=org_local,
            name=res_data['name'],
            defaults={
                'entity_type': res_data['entity_type'],
                'capacity': res_data['capacity'],
                'equipment_list': res_data['equipment'],
                'special_features': res_data['features'],
                'is_available': True
            }
        )
        print(f"✅ Recurso: {resource.name} ({'criado' if created else 'já existe'})")

    # Criar instrutores de exemplo
    instructors_data = [
        {
            'first_name': 'João',
            'last_name': 'Silva',
            'email': 'joao@acr.local',
            'entity_affiliation': 'acr_only',
            'specialties': 'Musculação, Treino Funcional'
        },
        {
            'first_name': 'Maria',
            'last_name': 'Santos',
            'email': 'maria@acr.local',
            'entity_affiliation': 'proform_only',
            'specialties': 'Pilates, Yoga, Relaxamento'
        },
        {
            'first_name': 'Carlos',
            'last_name': 'Mendes',
            'email': 'carlos@acr.local',
            'entity_affiliation': 'both',
            'specialties': 'Personal Training, Pilates Clínico'
        }
    ]

    for inst_data in instructors_data:
        instructor, created = Instructor.objects.get_or_create(
            organization=org_local,
            email=inst_data['email'],
            defaults={
                'first_name': inst_data['first_name'],
                'last_name': inst_data['last_name'],
                'entity_affiliation': inst_data['entity_affiliation'],
                'specialties': inst_data['specialties'],
                'is_active': True
            }
        )
        print(f"✅ Instrutor: {instructor.full_name} ({'criado' if created else 'já existe'})")

    print("\n🎉 Setup inicial completo!")
    print("📋 Resumo criado:")
    print(f"   • 1 Organização: {org_local.name}")
    print(f"   • {Modality.objects.filter(organization=org_local).count()} Modalidades")
    print(f"   • {Resource.objects.filter(organization=org_local).count()} Recursos/Espaços")
    print(f"   • {Instructor.objects.filter(organization=org_local).count()} Instrutores")
    print("\n🌐 Acesso: http://localhost (admin/admin123)")

if __name__ == '__main__':
    try:
        create_initial_data()
    except (IntegrityError, ValidationError, OperationalError) as e:
        logger.error("Erro ao criar dados iniciais: %s", e)
        sys.exit(1)
