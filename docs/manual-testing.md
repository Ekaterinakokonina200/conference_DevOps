\# Ручное тестирование



\## 1. Назначение



Документ описывает последовательность ручной проверки Conference Management System перед приёмкой версии.



Проверка включает:



\* подготовку окружения;

\* применение миграций;

\* запуск приложения;

\* проверку служебных адресов;

\* проверку Web-интерфейса;

\* проверку основного бизнес-правила;

\* проверку сводного отчёта;

\* проверку обработки ошибок.



\## 2. Предварительные условия



На компьютере должны быть установлены:



\* Python;

\* PostgreSQL;

\* Git;

\* зависимости проекта.



Необходимо находиться в корне проекта:



```powershell

cd "C:\\Users\\Admin\\Polytech\\DevOps\\conference\_DevOps"

```



\## 3. Виртуальное окружение



Если виртуальное окружение ещё не создано:



```powershell

python -m venv .venv

```



Активировать:



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



Установить зависимости:



```powershell

python -m pip install -r requirements.txt

```



\## 4. Переменные окружения



Проверить наличие `.env`:



```powershell

Test-Path .env

```



Если результат `False`:



```powershell

Copy-Item .env.example .env

notepad .env

```



Пример локального содержимого:



```env

DATABASE\_URL=postgresql://postgres:LOCAL\_PASSWORD@localhost:5432/conference

```



Вместо `LOCAL\_PASSWORD` указывается локальный пароль PostgreSQL.



Файл `.env` нельзя добавлять в Git.



\## 5. Подготовка базы данных



Убедиться, что PostgreSQL запущен.



Применить миграции:



```powershell

alembic upgrade head

```



Проверить текущую миграцию:



```powershell

alembic current

```



Проверить последнюю миграцию:



```powershell

alembic heads

```



Ожидаемая revision:



```text

1dbb1a8d5df8

```



Значения `current` и `heads` должны совпадать.



\## 6. Автоматические проверки



Запустить Ruff:



```powershell

ruff check .

```



Ожидаемый результат:



```text

All checks passed!

```



Запустить pytest:



```powershell

python -m pytest

```



Все тесты должны иметь статус `passed`.



Проверить пробелы:



```powershell

git diff --check

```



При успешной проверке команда ничего не выводит.



\## 7. Запуск приложения



Запустить сервер:



```powershell

python -m uvicorn app.main:app --reload

```



Ожидается:



```text

Uvicorn running on http://127.0.0.1:8000

```



Сервер необходимо оставить запущенным.



Последующие команды выполняются во втором окне PowerShell.



\## 8. Проверка Health Check



Выполнить:



```powershell

Invoke-RestMethod `

&#x20;   -Method Get `

&#x20;   -Uri "http://127.0.0.1:8000/health"

```



Ожидаемый ответ:



```text

status

\------

ok

```



Также можно открыть:



```powershell

Start-Process "http://127.0.0.1:8000/health"

```



Ожидаемый JSON:



```json

{

&#x20; "status": "ok"

}

```



\## 9. Проверка Web-интерфейса



Открыть:



```powershell

Start-Process "http://127.0.0.1:8000/"

```



Проверить:



\* страница загружается;

\* форма создания Participant отображается;

\* таблица участников отображается;

\* форма Application отображается;

\* форма Payment отображается;

\* кнопка формирования отчёта работает;

\* успешные операции сопровождаются сообщениями;

\* ошибки сопровождаются понятными сообщениями;

\* таблица корректно отображается при изменении размера окна.



\## 10. Проверка Swagger



Открыть:



```powershell

Start-Process "http://127.0.0.1:8000/docs"

```



Проверить наличие групп:



\* Participants;

\* Applications;

\* Invitations;

\* Payments;

\* Theses;

\* Hotel Requests;

\* Reports.



\## 11. Создание тестового участника



Создать уникальный email:



```powershell

$email = "manual\_$(\[DateTimeOffset]::UtcNow.ToUnixTimeSeconds())@example.com"

```



Подготовить данные:



```powershell

$participantBody = @{

&#x20;   full\_name = "Manual Test Participant"

&#x20;   email = $email

&#x20;   phone = "+79990000000"

&#x20;   organization = "Test University"

} | ConvertTo-Json

```



Отправить запрос:



```powershell

$participant = Invoke-RestMethod `

&#x20;   -Method Post `

&#x20;   -Uri "http://127.0.0.1:8000/participants/" `

&#x20;   -ContentType "application/json" `

&#x20;   -Body $participantBody

```



Посмотреть результат:



```powershell

$participant

```



Сохранить ID:



```powershell

$participantId = $participant.id

```



Ожидается новый Participant с числовым `id`.



\## 12. Создание заявки



Подготовить данные:



```powershell

$applicationBody = @{

&#x20;   participant\_id = $participantId

} | ConvertTo-Json

```



Отправить:



```powershell

$application = Invoke-RestMethod `

&#x20;   -Method Post `

&#x20;   -Uri "http://127.0.0.1:8000/applications/" `

&#x20;   -ContentType "application/json" `

&#x20;   -Body $applicationBody

```



Сохранить ID:



```powershell

$applicationId = $application.id

```



Проверить статус:



```powershell

$application.status

```



Ожидается:



```text

pending

```



\## 13. Проверка запрета подтверждения без оплаты



Подготовить запрос:



```powershell

$confirmBody = @{

&#x20;   status = "confirmed"

} | ConvertTo-Json

```



Выполнить:



```powershell

try {

&#x20;   Invoke-RestMethod `

&#x20;       -Method Put `

&#x20;       -Uri "http://127.0.0.1:8000/applications/$applicationId" `

&#x20;       -ContentType "application/json" `

&#x20;       -Body $confirmBody

}

catch {

&#x20;   $\_.Exception.Response.StatusCode

&#x20;   $\_.ErrorDetails.Message

}

```



Ожидаемый код:



```text

Conflict

```



Ожидаемое сообщение:



```text

Registration fee must be paid before confirmation

```



Проверка считается успешной, если сервер вернул `409 Conflict`.



\## 14. Создание оплаченного взноса



Подготовить данные:



```powershell

$paymentBody = @{

&#x20;   participant\_id = $participantId

&#x20;   amount = 1500

&#x20;   status = "paid"

} | ConvertTo-Json

```



Создать Payment:



```powershell

$payment = Invoke-RestMethod `

&#x20;   -Method Post `

&#x20;   -Uri "http://127.0.0.1:8000/payments/" `

&#x20;   -ContentType "application/json" `

&#x20;   -Body $paymentBody

```



Сохранить ID:



```powershell

$paymentId = $payment.id

```



Проверить:



```powershell

$payment

```



Ожидается:



```text

status : paid

```



Поле `payment\_date` должно быть заполнено.



\## 15. Повторное подтверждение заявки



Выполнить:



```powershell

$confirmedApplication = Invoke-RestMethod `

&#x20;   -Method Put `

&#x20;   -Uri "http://127.0.0.1:8000/applications/$applicationId" `

&#x20;   -ContentType "application/json" `

&#x20;   -Body $confirmBody

```



Проверить:



```powershell

$confirmedApplication.status

```



Ожидается:



```text

confirmed

```



Проверка считается успешной, если сервер вернул `200 OK`.



\## 16. Проверка сводного отчёта



Выполнить:



```powershell

$report = Invoke-RestMethod `

&#x20;   -Method Get `

&#x20;   -Uri "http://127.0.0.1:8000/reports/summary"

```



Посмотреть:



```powershell

$report

```



Ответ должен содержать:



\* `participants`;

\* `confirmed`;

\* `payments\_received`;

\* `theses\_submitted`;

\* `hotel\_required`.



\## 17. Проверка некорректной суммы



Подготовить запрос:



```powershell

$invalidPaymentBody = @{

&#x20;   participant\_id = $participantId

&#x20;   amount = -100

&#x20;   status = "paid"

} | ConvertTo-Json

```



Выполнить:



```powershell

try {

&#x20;   Invoke-RestMethod `

&#x20;       -Method Post `

&#x20;       -Uri "http://127.0.0.1:8000/payments/" `

&#x20;       -ContentType "application/json" `

&#x20;       -Body $invalidPaymentBody

}

catch {

&#x20;   $\_.Exception.Response.StatusCode

}

```



Ожидается:



```text

UnprocessableEntity

```



или код `422`.



\## 18. Удаление тестовых данных



Удалить Payment:



```powershell

Invoke-RestMethod `

&#x20;   -Method Delete `

&#x20;   -Uri "http://127.0.0.1:8000/payments/$paymentId"

```



Удалить Application:



```powershell

Invoke-RestMethod `

&#x20;   -Method Delete `

&#x20;   -Uri "http://127.0.0.1:8000/applications/$applicationId"

```



Удалить Participant:



```powershell

Invoke-RestMethod `

&#x20;   -Method Delete `

&#x20;   -Uri "http://127.0.0.1:8000/participants/$participantId"

```



Удаление выполняется в указанном порядке, чтобы сначала удалить дочерние записи.



\## 19. Проверка отсутствующего объекта



Выполнить:



```powershell

try {

&#x20;   Invoke-RestMethod `

&#x20;       -Method Get `

&#x20;       -Uri "http://127.0.0.1:8000/participants/999999"

}

catch {

&#x20;   $\_.Exception.Response.StatusCode

&#x20;   $\_.ErrorDetails.Message

}

```



Ожидается:



```text

NotFound

```



и сообщение:



```text

Participant not found

```



\## 20. Итог ручной проверки



Ручная проверка считается успешной, если:



\* сервер запускается;

\* `/health` возвращает `200`;

\* Web UI открывается;

\* Swagger открывается;

\* Participant создаётся;

\* Application создаётся;

\* confirmed без оплаты возвращает `409`;

\* Payment со статусом paid создаётся;

\* после оплаты Application получает confirmed;

\* Report возвращает сводные данные;

\* некорректные данные возвращают `422`;

\* отсутствующие объекты возвращают `404`;

\* тестовые данные успешно удаляются.



