# Changelog

All notable changes to this project will be documented in this file.
This project follows Semantic Versioning.

## Unreleased
- Add structured logging with request-id and optional Sentry integration.
- Fix Gantt data loading and improve UI defaults (resource filters, today date, scheduler plugins).
- Add async Google Calendar sync tasks via Celery.
- Add caching and query optimizations for Gantt and reports.
- Add CSV export and advanced filters for events and bookings.
- Add CI workflow (ruff + pytest), health check, and backup script.
- Add data integrity constraints and i18n settings.
- Improve Gantt UX: auto-title on empty, no edit modal on drag.
- Gantt: close modal on save and allow deleting events from the modal.
- Gantt: use double-click to edit; single click reserved for drag adjustments.
- Gantt: add day navigation arrows and drag threshold to enable double-click edit.
- Clientes: prompt após criação e ação de eliminar na lista.

## 0.1.0
- Initial baseline.
