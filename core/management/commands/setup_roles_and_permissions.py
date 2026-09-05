from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from core.models import (
    GoverningBody, GoverningBodyMember, ProtocolConfiguration, ProtocolPeriodSettlement,
    Person, AthleteGraduation, Event, Booking, Modality, Resource, Instructor,
    Payment, ClientSubscription
)


class Command(BaseCommand):
    help = "Cria e parametriza os 5 grupos Django oficiais de separação entre Associação ACR e ProForm."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("A configurar grupos e permissões oficiais (ACR vs ProForm)..."))

        def get_perms(model, actions):
            ct = ContentType.objects.get_for_model(model)
            codenames = [f"{action}_{model._meta.model_name}" for action in actions]
            return list(Permission.objects.filter(content_type=ct, codename__in=codenames))

        groups_config = {
            "Direção ACR": [
                (GoverningBody, ["add", "change", "delete", "view"]),
                (GoverningBodyMember, ["add", "change", "delete", "view"]),
                (ProtocolConfiguration, ["change", "view"]),
                (ProtocolPeriodSettlement, ["add", "change", "delete", "view"]),
                (Person, ["add", "change", "delete", "view"]),
                (Payment, ["add", "change", "delete", "view"]),
                (ClientSubscription, ["add", "change", "delete", "view"]),
                (AthleteGraduation, ["view"]),
                (Event, ["view"]),
                (Booking, ["view"]),
            ],
            "Staff ACR": [
                (GoverningBody, ["view"]),
                (GoverningBodyMember, ["view"]),
                (Person, ["add", "change", "view"]),
                (Payment, ["add", "change", "view"]),
                (ClientSubscription, ["add", "change", "view"]),
                (AthleteGraduation, ["view"]),
                (Event, ["view"]),
                (Booking, ["view"]),
            ],
            "Direção Técnica Proform": [
                (AthleteGraduation, ["add", "change", "delete", "view"]),
                (Event, ["add", "change", "delete", "view"]),
                (Booking, ["add", "change", "delete", "view"]),
                (Modality, ["add", "change", "view"]),
                (Resource, ["add", "change", "view"]),
                (Instructor, ["add", "change", "view"]),
                (Person, ["change", "view"]),
                (ProtocolPeriodSettlement, ["view"]),
                (Payment, ["add", "view"]),
                (ClientSubscription, ["add", "change", "view"]),
            ],
            "Staff Proform": [
                (Booking, ["add", "change", "delete", "view"]),
                (Event, ["view"]),
                (AthleteGraduation, ["view"]),
                (Person, ["change", "view"]),
                (Payment, ["add", "view"]),
                (ClientSubscription, ["add", "change", "view"]),
            ],
            "Instrutores": [
                (Event, ["view"]),
                (Booking, ["change", "view"]),
                (AthleteGraduation, ["add", "view"]),
                (Person, ["view"]),
            ],
        }

        for group_name, model_rules in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            all_perms = []
            for model, actions in model_rules:
                all_perms.extend(get_perms(model, actions))

            group.permissions.set(all_perms)
            status_str = "criado" if created else "atualizado"
            self.stdout.write(self.style.SUCCESS(f"✅ Grupo '{group_name}' {status_str} com {len(all_perms)} permissões."))

        self.stdout.write(self.style.SUCCESS("Concluída a parametrização dos grupos e permissões com sucesso."))
