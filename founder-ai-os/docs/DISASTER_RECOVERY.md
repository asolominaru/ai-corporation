# DISASTER_RECOVERY.md

## 1. Принципы

- Система не зависит от одного хостинг-провайдера и от одной страны.
- Бэкап, который не восстанавливали, — не бэкап. Restore test — регулярная процедура, а не надежда.
- Все бэкапы шифруются клиентски (restic) до отправки в storage.

## 2. Что и куда бэкапится

| Данные | Метод | Частота | Куда |
|---|---|---|---|
| PostgreSQL control-plane (Spain) | WAL-архив + nightly base (pg_dump через restic stdin) | WAL continuous, base nightly 03:17 UTC | Object storage (off-provider) + pull-копия на KZ |
| PostgreSQL production (RU) | WAL + nightly base | то же | RU object storage (RU-юрисдикция) + владелец решает о выходе за пределы РФ отдельно |
| Git | push в 2 remotes (GitHub + зеркало на KZ) | каждый push / 15 мин зеркало | GitHub + KZ |
| Docker images | registry retention + weekly export ключевых образов | weekly | registry + KZ |
| Секреты | SOPS-файлы в Git + мастер-ключ офлайн | при изменении | Git + офлайн носитель |
| Конфигурация (compose, env шаблоны, ACL) | Git | при изменении | GitHub + KZ |
| Audit logs export | daily export, WORM bucket | daily | object storage с object lock |
| Knowledge/documents | источники (GDrive) — provider-native; чанки пересобираются | ingestion повторяем | — |

## 3. RPO / RTO

| Система | RPO | RTO | Механизм |
|---|---|---|---|
| Founder AI OS control-plane | ≤ 15 мин (WAL) | ≤ 4 ч | активация KZ warm standby |
| ВФОРУМЕ production (RU) | ≤ 15 мин | ≤ 1 ч | restore на том же или запасном RU VPS |
| Git | ~0 (два remote) | ≤ 30 мин | переключение remote |
| Документы (GDrive) | provider SLA | provider SLA | экспорт критичных документов weekly в object storage |
| Secrets | последняя версия в Git | ≤ 1 ч | мастер-ключ + sops |

## 4. Процедура: полная потеря Spain-node

Предусловия: KZ-node жив, в tailnet, имеет свежие зеркала и бэкапы.

1. **Объявить инцидент**, зафиксировать время последней WAL в бэкапе (это граница потерь).
2. На KZ: `restore-control-plane.sh --latest` — restic restore → PostgreSQL base + WAL replay до последней точки.
3. Применить SOPS-ключ kazakhstan к зашифрованным секретам (LLM-ключи дублированы в sops-файле для KZ-контура).
4. `docker compose -f docker-compose.kz.yml up -d` — профиль standby→active (orchestrator, model-router, agent-runner, n8n, monitoring).
5. Обновить DNS `api.<domain>` → KZ IP (TTL заранее 300s) — human approval, т.к. DNS в списке критичных.
6. Проверить: health endpoints, тестовая задача через очередь, связность с RU (deploy-broker на KZ имеет свой ключ deploy-ai — второй authorized key на RU).
7. Объявить Spain потерянным; при появлении нового Spain-сервера — install-spain.sh, репликация в обратную сторону, возврат primary по плану.

Ожидаемое время при отработанной процедуре: 2–4 часа. Первый реальный прогон — обязательный учебный (см. §5).

**Что НЕ восстанавливается на KZ:** staging-окружение (можно пожертвовать), очередь задач в статусе `running` (помечаются `failed` с reason=node_loss, перезапускаются по retry policy).

## 5. Restore testing

- **Ежемесячно, 1-е число:** автоматический restore PostgreSQL nightly backup в изолированный контейнер на KZ + прогон стандартных SQL-проверок (количество строк в ключевых таблицах, целостность hash-chain аудита). Результат — запись в `audit_logs` и метрика `restore_test_success`.
- **Ежеквартально:** полный учебный DR-прогон §4 с секундомером. Отчёт владельцу: фактический RTO, что сломалось, что поправить.
- Отсутствие успешного restore test > 45 дней → автоматический инцидент HIGH.

## 6. Потеря других узлов

- **RU-node:** сайты падают → развёртывание на запасном RU VPS по install-russia.sh + restore production DB (RTO ≤ 1 ч). Founder AI OS продолжает работать — это отдельный контур, и это правильно.
- **KZ-node:** некритично. Поднять новый за 1 час, восстановить зеркала. Риск-окно: до восстановления KZ нет standby.
- **Два узла одновременно:** GitHub + object storage вне периметра — восстановление с нуля по install-скриптам, RTO ~1 рабочий день. Мастер-ключ офлайн — критично, без него секреты не восстановить.
