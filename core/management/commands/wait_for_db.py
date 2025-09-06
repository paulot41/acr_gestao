"""
Comando Django para aguardar que a base de dados esteja pronta.
Útil para containers Docker que dependem da DB.
"""

import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Comando para aguardar a base de dados."""

    help = 'Aguarda que a base de dados esteja disponível'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout em segundos (padrão: 30)'
        )

    def handle(self, *args, **options):
        """Aguardar até a DB estar disponível."""
        self.stdout.write('Aguardando base de dados...')
        timeout = options['timeout']
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Tentar conectar à base de dados padrão
                db_conn = connections['default']
                db_conn.ensure_connection()

                self.stdout.write(
                    self.style.SUCCESS('Base de dados disponível!')
                )
                return

            except OperationalError as e:
                self.stdout.write(
                    f'Base de dados indisponível, aguardando 1 segundo... ({e})'
                )
                time.sleep(1)

        self.stdout.write(
            self.style.ERROR(f'Timeout! Base de dados não disponível após {timeout}s')
        )
        exit(1)
