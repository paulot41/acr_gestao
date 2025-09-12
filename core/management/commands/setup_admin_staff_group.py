from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Create or update 'Admin Staff' group with view-only permissions for core models."

    def handle(self, *args, **options):
        group_name = "Admin Staff"
        group, created = Group.objects.get_or_create(name=group_name)

        # Collect all 'view' permissions for core app models
        view_perms = Permission.objects.filter(
            content_type__app_label="core",
            codename__startswith="view_",
        )

        before = group.permissions.count()
        group.permissions.add(*list(view_perms))
        after = group.permissions.count()

        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Group '{group_name}' created with {after} permissions."))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Group '{group_name}' updated ({before} -> {after} permissions)."))

        self.stdout.write("ℹ️ Assign users to this group for read-only Admin access to business data.")

