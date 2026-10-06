# Покрытие функционала ТЗ автоматическими тестами

Матрица связывает требования `docs/technical-specification.md` с тестами.
«Авто» — требование проверяется в `make verify`; «Ручная» — проверяется по
`docs/manual-testing.md`.

| Раздел ТЗ | Требование | Проверка | Тесты |
|---|---|---|---|
| 6.1 | Регистрация пользователя | Авто | `integration/test_auth.py::test_register_user` |
| 6.1 | Уникальность username | Авто | `test_auth.py::test_duplicate_username_returns_409` |
| 6.1 | Хеширование пароля | Авто | `test_auth.py::test_password_is_stored_as_argon2_hash`, `unit/test_security.py` |
| 6.1 | Вход по username и password | Авто | `test_auth.py::test_login_and_get_current_user`, `test_login_with_wrong_password_returns_401` |
| 6.1 | Выдача JWT | Авто | `test_auth.py::test_login_and_get_current_user` |
| 6.1 | Ограничение срока действия JWT | Авто | `test_auth.py::test_token_contains_subject_and_expiration`, `test_me_rejects_expired_token` |
| 6.1 | Проверка подписи JWT | Авто | `test_auth.py::test_me_rejects_token_with_foreign_signature`, `unit/test_security.py` |
| 6.1 | Получение текущего пользователя | Авто | `test_auth.py::test_login_and_get_current_user` |
| 6.1 | Отказ без JWT или с недействительным JWT | Авто | `test_auth.py::test_me_requires_token`, `test_me_rejects_invalid_token` |
| 6.2 | Создание Participant | Авто | `test_participants.py::test_create_participant` |
| 6.2 | Список Participant | Авто | `test_participants.py::test_list_participants` |
| 6.2 | Participant по id | Авто | `test_participants.py::test_get_participant_by_id`, `test_get_missing_participant_returns_404` |
| 6.2 | Изменение Participant | Авто | `test_participants.py::test_update_participant` |
| 6.2 | Удаление Participant | Авто | `test_participants.py::test_delete_participant`, `test_delete_participant_with_related_records` |
| 6.2 | Уникальность email | Авто | `test_participants.py::test_duplicate_email_returns_409` |
| 6.3 | Создание Application | Авто | `test_applications.py::test_new_application_is_pending` |
| 6.3 | Список Application | Авто | `test_applications.py::test_list_get_and_delete_application` |
| 6.3 | Application по id | Авто | то же |
| 6.3 | Изменение статуса Application | Авто | `test_applications.py::test_can_confirm_after_paid_payment` |
| 6.3 | Причина при отклонении Application | Авто | `test_applications.py::test_reject_application_with_reason`, `test_reject_without_reason_returns_422`, `test_confirming_rejected_application_clears_reason` |
| 6.3 | Удаление Application | Авто | `test_applications.py::test_list_get_and_delete_application` |
| 6.4 | Создание Invitation | Авто | `test_invitations.py::test_new_invitation_is_created_and_not_sent` |
| 6.4 | Список Invitation | Авто | `test_invitations.py::test_list_get_delete_invitation` |
| 6.4 | Invitation по id | Авто | то же |
| 6.4 | Изменение статуса Invitation | Авто | `test_invitations.py::test_sending_invitation_sets_time`, `test_accepting_keeps_sent_time` |
| 6.4 | Удаление Invitation | Авто | `test_invitations.py::test_list_get_delete_invitation` |
| 6.5 | Создание Payment | Авто | `test_payments.py::test_create_pending_payment_without_date`, `test_create_paid_payment_sets_date` |
| 6.5 | Список Payment | Авто | `test_payments.py::test_list_get_delete_payment` |
| 6.5 | Payment по id | Авто | то же |
| 6.5 | Изменение статуса Payment | Авто | `test_payments.py::test_update_status_to_paid_and_back` |
| 6.5 | Удаление Payment | Авто | `test_payments.py::test_list_get_delete_payment` |
| 6.6 | Создание Thesis | Авто | `test_theses.py::test_new_thesis_is_submitted` |
| 6.6 | Список Thesis | Авто | `test_theses.py::test_list_get_delete_thesis` |
| 6.6 | Thesis по id | Авто | то же |
| 6.6 | Изменение статуса Thesis | Авто | `test_theses.py::test_approve_thesis` |
| 6.6 | Удаление Thesis | Авто | `test_theses.py::test_list_get_delete_thesis` |
| 6.7 | Создание HotelRequest | Авто | `test_hotel_requests.py::test_create_hotel_request` |
| 6.7 | Список HotelRequest | Авто | `test_hotel_requests.py::test_list_get_delete_hotel_request` |
| 6.7 | HotelRequest по id | Авто | то же |
| 6.7 | Изменение HotelRequest | Авто | `test_hotel_requests.py::test_update_hotel_request` |
| 6.7 | Удаление HotelRequest | Авто | `test_hotel_requests.py::test_list_get_delete_hotel_request` |
| 6.8 | Отчёт `GET /reports/summary` | Авто | `test_reports.py::test_empty_summary` |
| 6.8 | Количество участников | Авто | `test_reports.py::test_summary_counts_only_matching_records` |
| 6.8 | Количество подтверждённых заявок | Авто | то же |
| 6.8 | Количество оплат `paid` | Авто | то же |
| 6.8 | Количество тезисов | Авто | то же |
| 6.8 | Количество запросов на гостиницу | Авто | то же |
| 6.9 | Web-интерфейс: 11 функций (регистрация, вход, текущий пользователь, сохранение JWT, выход, участники, заявка, оплата, отчёт, ошибки API) | Ручная | `docs/manual-testing.md`; автоматически проверяется только наличие форм (`test_auth.py::test_web_interface_contains_authentication_forms`) |
| 6.10 | `GET /health` | Авто | `test_health.py::test_health_returns_ok` |
| 8.1 | Подтверждение заявки только после оплаты | Авто | `unit/test_rules.py`, `test_applications.py::test_cannot_confirm_*`, `test_can_confirm_after_paid_payment`, мутационная проверка |
| 8.2 | Уникальность email (409) | Авто | `test_participants.py::test_duplicate_email_returns_409`, `test_update_to_existing_email_returns_409` |
| 8.3 | Уникальность username (409) | Авто | `test_auth.py::test_duplicate_username_returns_409` |
| 8.4 | Пароль только в виде Argon2-хеша, не возвращается API | Авто | `test_auth.py::test_password_is_stored_as_argon2_hash`, `test_register_user` |
| 8.5 | JWT содержит `sub` и `exp` | Авто | `test_auth.py::test_token_contains_subject_and_expiration` |
| 8.6 | Причина отклонения обязательна, очищается при другом статусе | Авто | `unit/test_rules.py::test_rejection_*`, `unit/test_schemas.py::test_rejection_reason_length_boundary`, `migrations/test_old_rejected_applications_get_default_reason` |

## Итог

| Показатель | Значение |
|---|---|
| Требований ТЗ в разделах 6 и 8 | 65 (11 из них — функции Web-интерфейса, считаются отдельными пунктами) |
| Проверяются автоматически | 54 |
| Покрытие функционала ТЗ | 54 / 65 = **83,1 %** (требование ЛР №3 — не менее 40 %) |
| Покрытие кода (`make test`) | не ниже порога `fail_under` в `pyproject.toml` |

## Ошибочные данные и граничные случаи

| Правило | Граница | Тесты |
|---|---|---|
| Сумма оплаты > 0 | 0 и −0,01 отклоняются, 0,01 принимается | `unit/test_schemas.py`, `test_payments.py::test_amount_boundaries` |
| Выезд позже заезда | тот же день отклоняется, следующий день принимается | `unit/test_rules.py`, `test_hotel_requests.py` |
| Длина username 3–50 | 2 и 51 отклоняются, 3 и 50 принимаются | `unit/test_schemas.py` |
| Длина пароля 8–128 | 7 и 129 отклоняются, 8 и 128 принимаются | `unit/test_schemas.py`, `test_auth.py` |
| Причина отклонения 1–500 символов | пустая и из пробелов отклоняются, 500 принимается, 501 отклоняется | `unit/test_rules.py`, `unit/test_schemas.py` |
| Статусы из фиксированного списка | неизвестный статус → 422 (API) и ошибка CHECK (БД) | `test_*.py::test_unknown_*`, `migrations/test_constraints_reject_invalid_data` |
| Оплата другого участника | не позволяет подтвердить заявку | `test_applications.py::test_cannot_confirm_with_payment_of_another_participant` |
| Несуществующие записи | 404 для get/put/delete | `test_*::test_missing_*` |
| Неверный формат email | 422 | `unit/test_schemas.py`, `test_participants.py` |

## Мутационная проверка

`make mutation` вносит в `app/services/rules.py` изменения условий (== ↔ !=,
< ↔ <=, and ↔ or, удаление not, подмена статусов и возвращаемых значений)
и после каждого запускает unit-тесты. Все мутанты должны быть «убиты».
