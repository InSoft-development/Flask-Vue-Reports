# Flask-Vue-Reports

Стек Flask + Vue 3.  Веб-приложение построения и просмотра отчетов срезов, сеток и дребезга сигналов архивных данных.

## Назначение

Веб-приложение предназначено для построения, просмотра и выкачки шаблонизированных отчетов срезов, сеток и дребезга сигналов за определенный период времени или интервал по составленному пользователю запросу. Получение данных для построения отчетов возможно с помощью конфигурируемых пользователем клиентов OPC UA и базы данных Clickhouse. После выполнения запроса и отображения результата запроса в веб-интерфейсе возможно осуществить выкачку построенных отчетов в форматах pdf и csv для их дальнейшего анализа.

## Требования к платформе

<table>
 	<tr>
  		<td align="center">Платформа</td>
   		<td align="center">Debian подобные дистрибутивы ОС</td>
 	</tr>
	<tr>
  		<td align="center">Python</td>
   		<td align="center">версия 3 не ниже 3.8.10</td>
 	</tr>
	<tr>
  		<td align="center">Браузер</td>
   		<td>веб-браузеры на основе веб-движка Chromium (Chrome не ниже релиза 57, Microsoft Edge не ниже 14-ой версии, Firefox не ниже релиза 52, Opera не ниже релиза 43), Internet Explorer 11, Safari не ниже 10-ой версии</td>
 	</tr>
</table>

Необходимы следующие пакеты Python:

- beautifulsoup4\=\==4.11.1
- clickhouse_connect\=\=0.5.18
- Flask\=\==2.2.5
- Flask_Cors\=\=4.0.1
- Flask_SocketIO\=\=5.3.6
- gevent\=\==22.10.2
- Jinja2\=\==3.1.2
- jsonschema\=\==4.23.0
- loguru\=\==0.5.3
- matplotlib\=\==3.5.2
- numba\=\==0.56.3
- numpy\=\==1.23.5
- pandas\=\==1.4.4
- pdfkit\=\==1.0.0
- python_dateutil\=\=2.8.2
- traces\=\==0.6.4
- werkzeug\=\==3.0.3

## Установка

1. скачать релизную версию из репозитория, распаковать архив и перейти в директорию веб-приложения;
2. установить пакеты Python из файла requirements.txt с помощью команды: 

```
pip install -r requirements.txt
```

3. установить под ОС пакет [wkhtmltopdf](https://wkhtmltopdf.org/downloads.html) для рендеринга отчетов из html шаблонов в pdf документ;

4. перейти в директорию с веб-приложением и создать структуру веб-приложения с помощью команды:

```
python app.py -s
```

5. в директории веб-приложения `./client` дать права на чтение, запись и исполнение бинарному файлу `client` и скрипту `slicer.py`:

```
chmod 775 client slicer.py
```

6. в директорию веб-приложения `./data` положить сертификаты `cert.pem`, `key.perm` для обеспечения шифрованной передачи данных между сервером и клиенту по протоколу https. Если сертификаты отсутствуют, то их следует сгенерировать с помощью пакета openssl. 
   **`Предупреждение:`** при создании сертификата потребуется ответить на ряд вопросов. Ключевой момент заключается в указании **полного доменного имени FQDN**, которое **должно соответствовать IP-адресу хоста**, на котором разворачивается веб-приложение. 
   Создать сертификат можно следующим образом: 
   
```
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

7. в директорию веб-приложения `./data` скопировать при наличии файл тега `kks_all.csv`. Затем в той же директории `./data` создать копию файла `kks_all.csv` и назвать ее `kks_all_back.csv`;
8. в директорию веб-приложения `./data` скопировать при наличии конфиг `config.json`.  Если конфига нет, то создать его по описанию из раздела: [Описание конфигурационного файла config.json](#Описание-конфигурационного-файла-configjson).

## Состав скриптов веб-приложения

В состав веб-приложения входят python скрипты бэкенда и фронтенда :

- app.py: запуск и функционирование бэкенда веб-приложения. На стороне бэкенда происходит обработка https запросов клиента посредством устанавливаемого сокетного соединения, сбор и выдача данных клиенту для отображения отчетов в веб-интерфейсе, построение отчетов;
- app_client.py: запуск и функционирование фронтенда веб-приложения. На стороне фронтенда осуществляется взаимодействие пользователя с веб-приложением, конфигурация клиентов, составление пользователем запросов для построения отчетов и отображение отчетов в веб-странице.

## Запуск

Запуск веб-приложения разделен на две части: запуск веб-сервера бэкенда и запуск веб-сервера, обслуживающего фронтенд веб-приложения. Запуск следует осуществлять в **строгой последовательности**: 

1. запустить бэкенд веб-приложения;
2. запустить фронтенд веб-приложения.

### Запуск бэкенда

Для запуска бэкенда веб-приложения, представляющего собой веб-сервер Flask, следует ввести команду:

```
python app.py --host {указать IPv4 адрес хоста} --port {указать порт}
```

Для создания структуры веб-приложения следует использовать опцию -s:

```
python app.py -s
```

Также возможен запуск бэкенда веб-приложения с одновременной проверкой структуры веб-приложения. Для этого можно воспользоваться командой:

```
python app.py --host {указать IPv4 адрес хоста} --port {указать порт} --structure
```

#### Описание аргументов командной строки скрипта app.py

<table>
 	<tr>
  		<td align="center">Сокращенная опция</td>
  		<td align="center">Длинная опция</td>
   		<td align="center">Описание опции</td>
 	</tr>
	<tr>
  		<td align="center">-ip</td>
   		<td align="center">--host</td>
   		<td align="center">IPv4 адрес хоста</td>
 	</tr>
 	<tr>
  		<td align="center">-p</td>
   		<td align="center">--port</td>
   		<td align="center">порт</td>
 	</tr>
 	<tr>
  		<td align="center">-s</td>
   		<td align="center">--structure</td>
   		<td align="center">флаг создания и проверки структуры веб-приложения</td>
 	</tr>
 	<tr>
  		<td align="center">-v</td>
   		<td align="center">--version</td>
   		<td align="center">версия скрипта бэкенда веб-приложения</td>
 	</tr>
</table>

В процессе запуска бэкенда веб-приложения происходит адаптация фронтендной части, которая позволяет обеспечить выполнение сокетного соединения между бэкендом и фронтендом. Перед запуском бэкенда веб-приложения осуществляется этап инициализации, который состоит из: 
- проверки наличия конфига и его валидации;
- чтения (при наличии) файлов csv тегов;
- заполнения шаблонов jinja2 под указанные в параметрах командной строки ip адрес и порт для создания и выдачи шаблонизированных отчетов;
- организации взаимодействия с помощью сокета клиента дистрибутивной версии веб-приложения и бэкендом;
- старта бэкенда веб-приложения.
В случае ошибки запуска бэкенда на этапе инициализации веб-сервера в терминале появится соответствующее сообщение об ошибке. 

### Запуск фронтенда

Фронтенд веб-приложения реализован с помощью фреймворка Vue 3. С помощью сокетного соединения устанавливается связь между клиентом веб-приложения и сервером. Для обслуживания фронтенда дистрибутивной версии веб-приложения используется сервер Flask, который можно запустить как python скрипт следующим образом:

```
python app_client.py --host {указать IPv4 адрес клиента} --port {указать порт}
```

После запуска скрипта станет доступно подключение к веб-приложению по ссылке вида:
`https://{указанный в команде IPv4 адрес клиента}:{указанный в команде порт}`

#### Описание аргументов командной строки скрипта app_client.py

<table>
 	<tr>
  		<td align="center">Сокращенная опция</td>
  		<td align="center">Длинная опция</td>
   		<td align="center">Описание опции</td>
 	</tr>
	<tr>
  		<td align="center">-ip</td>
   		<td align="center">--host</td>
   		<td align="center">IPv4 адрес клиента, использующийся для подключения к веб-приложению</td>
 	</tr>
 	<tr>
  		<td align="center">-p</td>
   		<td align="center">--port</td>
   		<td align="center">порт используемый клиентом</td>
 	</tr>
 	<tr>
  		<td align="center">-v</td>
   		<td align="center">--version</td>
   		<td align="center">версия скрипта бэкенда веб-приложения</td>
 	</tr>
</table>

## Использование

При подключении к веб-приложению браузер может вывести предупреждение о недействительном сертификате, так как сертификат является самоподписанным и браузер не доверяет сертификату безопасности. В таком случае следует разрешить браузеру подключение и перейти на страницу веб-приложения.

Веб-приложение позволяет получить доступ к веб-страницам с отчетами и конфигурации через меню навигации в левой части окна браузера:

<table>
 	<tr>
  		<td align="center">Страница</td>
  		<td align="center">URL адрес страницы</td>
   		<td align="center">Описание страницы</td>
 	</tr>
	<tr>
  		<td align="center">Конфигуратор</td>
   		<td>https://{IP адрес клиента}:{порт клиента}/configurator</td>
   		<td align="center">Конфигурация клиента получения данных для отчетов и установка параметров по умолчанию</td>
 	</tr>
 	<tr>
  		<td align="center">Срезы сигналов</td>
   		<td>https://{IP адрес клиента}:{порт клиента}/ <b><sup>*</sup></b></td>
   		<td align="center">Отчет срезов сигналов в виде таблицы с столбцами: наименование датчика (KKS), дата и время измерения, значение, качество, код качества</td>
 	</tr>
 	<tr>
  		<td align="center">Сетка сигналов</td>
   		<td>https://{IP адрес клиента}:{порт клиента}/grid_report</td>
   		<td align="center">Отчет сетки сигналов в виде таблицы с столбцами: Метка времени, закодированный номер наименования датчика (KKS)</td>
 	</tr>
 	<tr>
  		<td align="center">Дребезг сигналов</td>
   		<td>https://{IP адрес клиента}:{порт клиента}/bounce_report</td>
   		<td align="center">Отчет дребезга сигналов в виде таблицы с столбцами: наименование датчика (KKS), частота</td>
 	</tr>
</table>
<b><sup>*</sup></b> - домашняя страница веб-приложения.

Для выполнения отбора и поиска тегов используется шаблон, ввод которого обязан соответствовать правилам написания и синтаксису регулярных выражения (regex). Синтаксис и правила написания регулярных выражений можно посмотреть на [странице](https://docs.python.org/3/library/re.html#regular-expression-syntax)

#### Текущие ограничения использования веб-приложения:

- однопользовательский режим и сценарий работы;
- запрет одновременного запуска нескольких пользовательских запросов;
- пересохранение отчетов после выполнения каждого пользовательского запроса;
- строго типизированная схема конфига, требующая заполнения всех полей.

## Структура веб-приложения

Ниже приведена упрощенная структура веб-приложения:

```
├── app_client.py
├── app.py
├── client
│   ├── client
│   ├── libuastack.so
│   └── slicer.py
├── data
│   ├── cert.pem (добавляется при установке)
│   ├── config.json (конфигурируется при установке)
│   ├── key.pem (добавляется при установке)
│   ├── kks_all_back.csv (добавляется при установке)
│   └── kks_all.csv (добавляется при установке)
├── jinja
│   ├── pylib
│   │   └── get_template.py
│   └── template
│       ├── bounce
│       ├── grid
│       ├── slice
│       └── source
├── README.md
├── reports
├── requirements.txt
├── static
│   ├── bootstrap
│   └── plotly.js-dist-min
├── utils
│   ├── constants_and_paths.py
│   ├── correct_start.py
│   └── routine_operations.py
└── web
    ├── assets
    └── index.html
```

- в папке `client` находится клиент для связи с OPC UA в виде `бинарного файла client`, библиотеки `libuastack.so` и python скрипта `slicer.py` для выкачки данных сетки;
- в папке `data` лежат файлы, необходимые для корректной работы веб-приложения: сертификаты (`cert.pem` и `key.pem`), конфигурационный файл `config.json`, файлы csv тегов, выкаченных клиентов OPC UA, `kks_all.csv` и `kks_all_back.csv`;
- в папке `jinja` содержится скрипт и шаблоны для автоматизированного построения отчетов;
- в папке `reports` появляются созданные отчеты после успешного выполнения запроса;
- в папке `static` находятся статические элементы веб-приложения, отдаваемые веб-сервером для оформления шаблонизированных html страниц, доступных для выкачки после успешного завершения запроса;
- в папке `utils` находятся служебные python скрипты;
- в папке `web` содержится дистрибутивная версия фронтенда веб-приложения.

### Обязательные файлы для корректного запуска веб-приложения

Для корректно запуска веб-приложения обязательно необходимо разместить в папке `data` следующие файлы: 

- конфигурационный файл `config.json`;
- сертификаты `cert.pem` и `key.pem`.

## Описание конфигурационного файла config.json

**`Предупреждение:`** при запуске бэкенда или импорте пользовательской конфигурации производится валидация конфигурационного файла по строгой [схеме](#схема-конфигурационного-файла). Если файл не удовлетворяет схеме на предмет наличия требуемых полей и отсутствия полей, не соответствующих схеме, то валидация конфигурационного файла будет не пройдена. Также в конфиге существуют поля, требующие определенного значения из перечисления (см. схему конфига).

### поля конфигурационного файла

Конфигурационный файл json содержит как данные выбранного клиента, так и параметры по умолчанию:

`mode:` выбранный режим клиента.

`clickhouse:` объект содержащий конфигурацию клиента Clickhouse:
- `ip:` IPv4 адрес хоста базы данных Clickhouse;
- `port:` порт подключения к базе данных Clickhouse;
- `username:` имя пользователя базы данных Clickhouse;
- `password:` пароль к базе данных Clickhouse.

`opc:` объект содержащий конфигурацию клиента OPC UA:
- `ip:` IPv4 адрес хоста Альфы платформы;
- `port:` порт подключения к Альфе платформе.

`fields:` объект хранения параметров по умолчанию. В качестве значения содержит объекты `OPC` и `CH`, в которых хранятся параметры по умолчанию для полей выбранного режима клиента. Объекты имеют следующие одинаковые поля:

- `typesOfSensors:` массив типов данных;
- `selectionTag:` тип фильтра тегов;
- `sensorsAndTemplateValue:` массив шаблонов (регулярных выражений);
- `quality:` массив кодов качества в виде: {код} - ({аббревиатура}) - {расшифровка}};
- `dateDeepOfSearch:` дата глубины поиска в архиве в формате: %Y-%m-%dT%H:%M:%S;
- `interval:` интервал периода (отсчет начального времени периода на основе указанной размерности в поле `dimension:`);
- `dimension:` размерность интервала периода;
- `countShowSensors:` количество показываемых датчиков в отчете дребезга;
- `lastValueChecked:` включение поиска последних по времени значений в отчете срезов сигналов;
- `intervalDeepOfSearch:` интервал периода глубины поиска в архивах (отсчет начального времени периода на основе указанной размерности в поле `dimensionDeepOfSearch:`);
- `dimensionDeepOfSearch:`размерность интервала периода глубины поиска в архивах;
- `modeOfFilter:` режим фильтрации обновления тегов (доступно только для клиента OPC UA);
- `rootDirectory:` корневая папка (доступно только для клиента OPC UA);
- `exceptionDirectories:` список исключений в виде массива регулярных выражений (доступно только для клиента OPC UA);
- `exceptionExpertTags:` включение исключения тегов, помеченных экспертом (доступно только для клиента OPC UA);
- `filterTableChecked:` включение фильтров к таблицам отчетов.

### схема конфигурационного файла

```
{  
    "type": "object",  
    "properties": {  
        "mode": {"type": "string", "enum": ["OPC", "CH"]},  
        "clickhouse": {  
            "type": "object",  
            "properties": {  
                "ip": {"type": "string"},  
                "port": {  
                    "type": "integer",  
                    "minimum": 0,  
                    "maximum": 65536  
                },  
                "username": {"type": "string"},  
                "password": {"type": "string"}  
            },  
            "additionalProperties": False,  
            "required": ["ip", "port", "username", "password"]  
        },  
        "opc": {  
            "type": "object",  
            "properties": {  
                "ip": {"type": "string"},  
                "port": {  
                    "type": "integer",  
                    "minimum": 0,  
                    "maximum": 65536  
                }  
            },  
            "additionalProperties": False,  
            "required": ["ip", "port"]  
        },  
        "fields": {  
            "type": "object",  
            "properties": {  
                "OPC": {  
                    "type": "object",  
                    "properties": {  
                        "typesOfSensors": {  
                            "type": "array",  
                            "items": {  
                                "type": "string"  
                            }  
                        },  
                        "selectionTag": {"type": "string", "enum": ["sequential", "union"]},  
                        "sensorsAndTemplateValue": {  
                            "type": "array",  
                            "items": {  
                                "type": "string"  
                            }  
                        },  
                        "quality": {  
                            "type": "array",  
                            "items": {  
                                "type": "string",  
                                "enum":  [  
	                                "8 - (BNC) - ОТКАЗ СВЯЗИ (TIMEOUT)",  
	                                "16 - (BSF) - ОТКАЗ ПАРАМ",  
	                                "24 - (BCF) - ОТКАЗ СВЯЗИ",  
	                                "28 - (BOS) - ОТКАЗ ОБСЛУЖ",  
	                                "88 - (BLC) - ОТКАЗ РАСЧЕТ",  
	                                "192 - (GOD) – ХОРОШ",  
	                                "200 - (GLC) - ХОРОШ РАСЧЕТ",  
	                                "216 - (GFO) - ХОРОШ ИМИТИР",  
	                                "224 - (GLT) - ХОРОШ ЛОКАЛ ВРЕМ" 
								]
                            }  
                        },  
                        "dateDeepOfSearch": {"type": "string"},  
                        "interval": {"type": "integer", "minimum": 0},  
                        "dimension": {"type": "string", "enum": ["day", "hour", "minute", "second"]},  
                        "countShowSensors": {"type": "integer", "minimum": 0},  
                        "lastValueChecked": {"type": "boolean"},  
                        "intervalDeepOfSearch": {"type": "integer", "minimum": 0},  
                        "dimensionDeepOfSearch": {"type": "string", "enum": ["day", "hour", "minute", "second"]},  
                        "modeOfFilter": {"type": "string", "enum": ["historian", "exception"]},  
                        "rootDirectory": {"type": "string"},  
                        "exceptionDirectories": {  
                            "type": "array",  
                            "items": {  
                                "type": "string"  
                            }  
                        },  
                        "exceptionExpertTags": {"type": "boolean"},  
                        "filterTableChecked": {"type": "boolean"}  
                    },  
                    "additionalProperties": False,  
                    "required": ["typesOfSensors", "selectionTag", "sensorsAndTemplateValue", "quality",  
                                 "dateDeepOfSearch", "interval", "dimension", "countShowSensors",  
                                 "lastValueChecked", "intervalDeepOfSearch", "dimensionDeepOfSearch", "modeOfFilter",  
                                 "rootDirectory", "exceptionDirectories", "exceptionExpertTags", "filterTableChecked"]  
                },  
                "CH": {  
                    "type": "object",  
                    "properties": {  
                        "typesOfSensors": {  
                            "type": "array",  
                            "items": {  
                                "type": "string"  
                            }  
                        },  
                        "selectionTag": {"type": "string", "enum": ["sequential", "union"]},  
                        "sensorsAndTemplateValue": {  
                            "type": "array",  
                            "items": {  
                                "type": "string"  
                            }  
                        },  
                        "quality": {  
                            "type": "array",  
                            "items": {  
                                "type": "string",  
                                "enum": "enum":  [  
	                                "8 - (BNC) - ОТКАЗ СВЯЗИ (TIMEOUT)",  
	                                "16 - (BSF) - ОТКАЗ ПАРАМ",  
	                                "24 - (BCF) - ОТКАЗ СВЯЗИ",  
	                                "28 - (BOS) - ОТКАЗ ОБСЛУЖ",  
	                                "88 - (BLC) - ОТКАЗ РАСЧЕТ",  
	                                "192 - (GOD) – ХОРОШ",  
	                                "200 - (GLC) - ХОРОШ РАСЧЕТ",  
	                                "216 - (GFO) - ХОРОШ ИМИТИР",  
	                                "224 - (GLT) - ХОРОШ ЛОКАЛ ВРЕМ" 
								]  
                            }  
                        },  
                        "dateDeepOfSearch": {"type": "string"},  
                        "interval": {"type": "integer", "minimum": 0},  
                        "dimension": {"type": "string", "enum": ["day", "hour", "minute", "second"]},  
                        "countShowSensors": {"type": "integer", "minimum": 0},  
                        "lastValueChecked": {"type": "boolean"},  
                        "intervalDeepOfSearch": {"type": "integer", "minimum": 0},  
                        "dimensionDeepOfSearch": {"type": "string", "enum": ["day", "hour", "minute", "second"]},  
                        "modeOfFilter": {"type": "string", "enum": ["historian", "exception"]},  
                        "rootDirectory": {"type": "string"},  
                        "exceptionDirectories": {  
                            "type": "array",  
                            "items": {  
                                "type": "string"  
                            }  
                        },  
                        "exceptionExpertTags": {"type": "boolean"},  
                        "filterTableChecked": {"type": "boolean"}  
                    },  
                    "additionalProperties": False,  
                    "required": ["typesOfSensors", "selectionTag", "sensorsAndTemplateValue", "quality",  
                                 "dateDeepOfSearch", "interval", "dimension", "countShowSensors",  
                                 "lastValueChecked", "intervalDeepOfSearch", "dimensionDeepOfSearch", "modeOfFilter",  
                                 "rootDirectory", "exceptionDirectories", "exceptionExpertTags", "filterTableChecked"]  
                }  
            },  
            "additionalProperties": False,  
            "required": ["OPC", "CH"]  
        }  
    },  
    "additionalProperties": False,  
    "required": ["mode", "clickhouse", "opc", "fields"]  
}
```
