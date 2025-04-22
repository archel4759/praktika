import os
import numpy as np
import tensorflow as tf
import keras as kr
model = kr.models.load_model(model_path, compile=False)
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()

#Создаем папку для html шаблонов
os.makedirs('templates', exist_ok=True)

#Окно авторизации
with open('templates/login.html', 'w') as f:
    f.write('''
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Вход</title>
        <style>
            body {
                font-family: Calibri, sans-serif;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                height: 100vh;
                margin: 0;
            }
            .container {
                margin-top: 50px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Вход</h2>
            <form method="POST" action="/login">
                <label for="username">Имя пользователя:</label>
                <input type="text" id="username" name="username"><br><br>
                <label for="password">Пароль:</label>
                <input type="password" id="password" name="password"><br><br>
                <input type="submit" value="Войти">
            </form>
            {% if error %}
                <p style="color:red;">{{ error }}</p>
            {% endif %}
             <p>Идентификатор сессии: {{ session_id }}</p>
        </div>
    </body>
    </html>
    ''')

#Основное окно
with open('templates/upload.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Загрузка файла</title>
    <style>
        body {
            font-family: Calibri, sans-serif; /* Установка шрифта Calibri */
            display: flex;
            justify-content: center;
            align-items: flex-start;
            height: 100vh;
            margin: 0;
        }
        .container {
            margin-top: 50px;
            text-align: center;
        }
        .hidden {
            display: none;
        }
        button {
            margin-top: 10px;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
        select {
            margin-top: 10px;
            padding: 10px;
            font-size: 16px;
        }
        .form-section {
            margin-bottom: 20px; /* Интервал между объектами формы */
        }
    </style>
    <script>
        function showOptions() {
            document.getElementById('options').classList.remove('hidden');
            document.getElementById('processButton').classList.add('hidden'); // Скрыть кнопку "Обработать"
            document.getElementById('clientOptions').classList.add('hidden');
            document.getElementById('serverOptions').classList.add('hidden');
        }

        function showClientOptions() {
            document.getElementById('clientOptions').classList.remove('hidden');
            document.getElementById('serverOptions').classList.add('hidden');
            document.getElementById('uploadFromClient').classList.add('hidden');
            document.getElementById('uploadFromServer').classList.remove('hidden');
        }

        function showServerOptions() {
            document.getElementById('serverOptions').classList.remove('hidden');
            document.getElementById('clientOptions').classList.add('hidden');
            document.getElementById('uploadFromServer').classList.add('hidden');
            document.getElementById('uploadFromClient').classList.remove('hidden');
            loadServerFiles();
        }

        function loadServerFiles() {
            fetch('/list_files')
                .then(response => response.json())
                .then(data => {
                    let fileSelect = document.getElementById('fileSelect');
                    fileSelect.innerHTML = '';
                    data.files.forEach(file => {
                        let option = document.createElement('option');
                        option.value = file;
                        option.textContent = file;
                        fileSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Ошибка при загрузке файлов с сервера:', error);
                });
        }

        function processClientFile() {
            let fileInput = document.querySelector('input[name="file"]');
            if (!fileInput.value) {
                alert('Пожалуйста, выберите файл для загрузки.');
                return false;
            }
            document.getElementById('uploadForm').submit(); // Подать форму загрузки файла с клиента
        }

        function processServerFile() {
            document.getElementById('fileSelectForm').submit(); // Подать форму загрузки файла с сервера
        }
    </script>
</head>
<body>
    <div class="container">
        <h2>Добро пожаловать, {{ user }}</h2>
        <p>Идентификатор сессии: {{ session_id }}</p>
        <p>Флаг обработки: {{ processed }}</p> <!-- Диагностика состояния флага -->

        <!-- Форма для обработки файла -->
        <form method="POST" action="/process" id="processForm">
            <button type="button" id="processButton" onclick="showOptions()">Обработать</button>
        </form>

        <!-- Опции выбора способа загрузки файла для обработки -->
        <div id="options" class="hidden">
            <h3>Выберите способ загрузки файла для обработки:</h3>
            <!-- Большие кнопки -->
            <button id="uploadFromClient" class="form-section" onclick="showClientOptions()">Загрузить с клиента</button>
            {% if role != 'ext' %}
            <button id="uploadFromServer" class="form-section" onclick="showServerOptions()">Загрузить с сервера</button>
            {% endif %}
        </div>

        <!-- Опции для загрузки с клиента -->
        <div id="clientOptions" class="hidden">
            <form method="POST" action="/upload" enctype="multipart/form-data" id="uploadForm">
                <input type="file" name="file" accept=".tif" required><br><br>
                <button type="button" onclick="processClientFile()">Начать обработку клиентского файла</button>
            </form>
        </div>

        <!-- Опции для загрузки с сервера -->
        {% if role != 'ext' %}
        <div id="serverOptions" class="hidden">
            <form method="POST" action="/download_from_drive" id="fileSelectForm">
                <label for="fileSelect">Выберите файл с сервера:</label>
                <select id="fileSelect" name="file">
                    <!-- Опции будут добавлены через JavaScript -->
                </select><br><br>
                <button type="button" onclick="processServerFile()">Начать обработку серверного файла</button>
            </form>
        </div>
        {% endif %}

        {% if processed %}
        <!-- Кнопка для сохранения файла на клиенте -->
        <form method="POST" action="/save_local">
            <button type="submit">Сохранить на клиент</button>
        </form>

        <!-- Кнопка для сохранения файла на сервере -->
        {% if role != 'ext' %}
        <form method="POST" action="/save_drive">
            <button type="submit">Сохранить на сервер</button>
        </form>
        {% endif %}
        {% endif %}

        {% if role == 'adm' %}
        <!-- Кнопка для скачивания лога-->
        <form method="post" action="{{ url_for('download_log') }}">
            <button type="submit">Выгрузить лог</button>
        </form>

        <form method="get" action="{{ url_for('register') }}">
            <button type="submit">Зарегистрировать пользователя</button>
        </form>

        {% endif %}

        {% if error %}
            <p style="color:red;">{{ error }}</p>
        {% endif %}
        {% if message %}
            <p style="color:green;">{{ message }}</p>
        {% endif %}
    </div>
</body>
</html>

    ''')

#Окно регистрации пользователя
with open('templates/register.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Регистрация пользователя</title>
    <style>
        body {
            font-family: Calibri, sans-serif;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            height: 100vh;
            margin: 0;
        }
        .container {
            margin-top: 50px;
            text-align: center;
        }
        form {
            margin-top: 20px;
        }
        input, select {
            margin-top: 10px;
            padding: 10px;
            font-size: 16px;
            width: 100%;
            max-width: 300px;
        }
        button {
            margin-top: 20px;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
        .flash {
            color: red;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Регистрация нового пользователя</h2>

        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash">
              {% for message in messages %}
                <p>{{ message }}</p>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}

        <form method="POST">
            <label for="username">Имя пользователя:</label><br>
            <input type="text" id="username" name="username" required><br><br>

            <label for="password">Пароль:</label><br>
            <input type="password" id="password" name="password" required><br><br>

            <label for="role">Роль:</label><br>
            <select id="role" name="role" required>
                <option value="adm">adm</option>
                <option value="emp">emp</option>
                <option value="ext">ext</option>
            </select><br><br>

            <button type="submit">Зарегистрировать</button>
        </form>

        <br>
        <a href="{{ url_for('login') }}">На страницу авторизации</a>
    </div>
</body>
</html>
    ''')