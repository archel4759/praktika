import os
os.environ["SM_FRAMEWORK"] = "tf.keras"
import cv2
import sys
import patchify
import tifffile
import rasterio
from rasterio.features import shapes as rasterio_shapes
import fiona
import imageio
import glob
from matplotlib import pyplot as plt
from patchify import patchify as pch, unpatchify as unpch
from PIL import Image
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from pyngrok import ngrok
!ngrok config add-authtoken 2jkKaaRUcIKjLeWuoqKhtw5w513_zNJavfxTQEBZdyP2V75H
import pyodbc
import bcrypt
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import matplotlib.pyplot as plt
import logging
import zipfile
import py7zr
from datetime import datetime, timedelta
import secrets


app = Flask(__name__)
app.secret_key = 'sk'
app.config['UPLOAD_FOLDER'] = f'{base_path}/upload folder'
app.config['DRIVE_FOLDER'] = f'{base_path}/drive folder'

os.makedirs(app.config['UPLOAD_FOLDER'] , exist_ok=True)
os.makedirs(app.config['DRIVE_FOLDER'] , exist_ok=True)

def generate_session_id():
    return f"{secrets.token_hex(3).upper()[:3]}-{secrets.token_hex(3).upper()[:3]}"

SESSION_ID = generate_session_id()

log_file_path = os.path.join(app.config['DRIVE_FOLDER'], 'session_log.txt')
os.makedirs(os.path.dirname(log_file_path), exist_ok=True) 
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(username)s - %(message)s')

# Журналирование действие
def log_action(content):
    with open(log_file_path, 'a') as f:
        current_time = datetime.now()
        new_time = current_time + timedelta(hours=3)
        timestamp = new_time.strftime('%Y-%m-%d %H:%M:%S')
        f.write(f"{timestamp}/{SESSION_ID}: {content}\n")
        print(f'+ log / {content}')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])

# Корневая функция на странице login
def login():
    session['processed'] = False
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Имя пользователя и пароль должны быть заполнены')
            log_action(f"{username} осуществлена попытка входа с пустым логином и/или паролем")
            return render_template('login.html', error='Имя пользователя и пароль должны быть заполнены', session_id=SESSION_ID)

        try:
            conn = sqlite3.connect(login_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT password, role FROM login_db WHERE login = ?", (username,))
            result = cursor.fetchone()
            conn.close()

            if result:
                stored_password_hash, role = result
                if check_password_hash(stored_password_hash, password):
                    session['username'] = username
                    session['role'] = role
                    log_action(f"{username} успешно подключился")
                    return redirect(url_for('upload'))
                else:
                    flash('Неверное имя пользователя или пароль')
                    log_action(f"Осущественна безуспешная попытка входа под логином {username} (неверный пароль)")
            else:
                flash('Неверное имя пользователя или пароль')
                log_action(f"Осущественна безуспешная попытка входа под логином {username} (пользователь не найден)")

        except Exception as e:
            flash('Ошибка при попытке входа')
            log_action(f"Ошибка входа для {username}: {e}")

        return render_template('login.html', error='Неверное имя пользователя или пароль', session_id=SESSION_ID)

    return render_template('login.html', session_id=SESSION_ID)

# Есть ли пользователь в БД
def check_user_exists(username):
    connection = sqlite3.connect(login_db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(1) FROM login_db WHERE login=?", (username,))
    result = cursor.fetchone()
    return result[0] > 0

# Новый пользователь
def add_user_to_db(username, hashed_password, role):
    connection = sqlite3.connect(login_db_path)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO login_db (login, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
    connection.commit()
    cursor.close()

@app.route('/register', methods=['GET', 'POST'])
#Регистрация пользака
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip().lower()
        password = request.form.get('password').strip()
        role = request.form.get('role')

        if not username or not password or not role:
            flash('Все поля должны быть заполнены')
            return render_template('register.html')

        # Проверка, если пользователь с таким именем уже существует
        if check_user_exists(username):
            flash('Пользователь с таким именем уже существует')
            return render_template('register.html')

        # Хеширование пароля
        hashed_password = generate_password_hash(password)

        # Добавление нового пользователя в базу данных
        add_user_to_db(username, hashed_password, role)

        log_action(f"Зарегистрирован пользователь {username}, роль - {role}")
        flash('Пользователь успешно зарегистрирован!')
        return render_template('register.html')

    return render_template('register.html')

@app.route('/upload', methods=['GET', 'POST'])

#Верхнеуровневая фукнция страницы upload.html
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    role = session['role']

    if request.method == 'POST':

        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash('Файл не выбран')
                log_action(f"{username} - попытка загрузить и обработать файл")
                return render_template('upload.html', role=role, session_id=SESSION_ID, processed=session.get('processed', False), user=username, error='Файл не выбран')

            if file and file.filename.endswith('.tif'):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                flash(f"Файл {filename} успешно загружен с клиента")
                log_action(f"{username} загрузил файл на обработку с клиента: {filename}. Путь: {file_path}")
                session['file_path'] = file_path

                log_action(f"{username} начал обработку клиентского файла {filename}. Путь: {file_path}")
                process(file_path) # Загрузить и обработать tif

                log_action(f"{username} успешно завершил обработку {filename}")
                return render_template('upload.html', role=role, user=username, session_id=SESSION_ID, processed=session.get('processed', False), message=f"Клиентский файл {filename} успешно обработан!")
            else:
                flash('Неправильный формат файла. Требуется .tif')
                return render_template('upload.html', role=role, user=username, session_id=SESSION_ID, processed=session.get('processed', False), error='Не удалось обработать клиентский файл')
    return render_template('upload.html', role=role, user=username, session_id=SESSION_ID, processed=session.get('processed', False))

@app.route('/create_zip_archive', methods=['POST'])
#Архивация шейпа и полученного tif. Вызывается из process
def create_zip_archive(input_filename):

    source_folder = f'{base_path}/download folder' # Здесь лежат обработанные файлы

    zip_filename = f"{source_folder}/{input_filename}_completed.zip"

    files_added = False # Флаг для проверки добавления файлов

    with zipfile.ZipFile(zip_filename, 'w') as zipf:

        for filename in os.listdir(source_folder):

            file_path = os.path.join(source_folder, filename) # Полный путь к файлу

            # Проверяем, если имя файла оканчивается на '_completed' и это файл (не папка)
            if os.path.isfile(file_path) and filename.split('_completed')[0] and filename.split('_completed')[-1].startswith('.') and filename.startswith(input_filename):

                # Добавляем файл в архив
                zipf.write(file_path, arcname=filename)
                log_action(f'Файл {filename} добавлен в архив {zip_filename}')
                files_added = True

    if not files_added:
        log_action('Нет файлов для добавления в архив. Убедитесь, что файлы существуют и соответствуют критериям.')

    log_action(f'Создание архива завершено. Архив сохранен как {zip_filename}')

@app.route('/process', methods=['POST'])

#Вызов модели, векторизация
def process(input_imgfile):

    username = session['username']

    input_folder = app.config['DRIVE_FOLDER'] 
    output_folder = f'{base_path}/download folder'
    temp_saved_folder = f'{base_path}/temp folder'

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(temp_saved_folder, exist_ok=True)
    os.makedirs(input_folder, exist_ok=True)

    if not os.path.exists(input_imgfile):
        log_action(f"Ошибка: Файл '{input_imgfile}' не существует.")
    else:
        # Пытаемся прочитать изображение
        img = cv2.imread(input_imgfile)

        # Проверяем, было ли изображение успешно прочитано
        if img is None:
            log_action(f"Ошибка: Не удалось прочитать изображение '{input_imgfile}'")
            session['processed'] = False
            return
        else:
            # Преобразуем изображение из BGR в RGB, особенности openCV.....
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Отображаем изображение
            log_action(f"Изображение {input_imgfile}' прочитано")
            from matplotlib.scale import FuncScaleLog

            filename = os.path.splitext(os.path.basename(input_imgfile))[0]
            print("1")

            patch_size = 256 # размер патча

            n_classes = 6 # кол-во классов

            SIZE_X = (img.shape[1]//patch_size)*patch_size # размер кропа по гор.
            SIZE_Y = (img.shape[0]//patch_size)*patch_size # размер кропа по вер.

            large_img = Image.fromarray(img)

            large_img = large_img.crop((0 ,0, SIZE_X, SIZE_Y))  #Кроп с верхнего левого угла
            large_img = np.array(large_img)

            log_action(f'Началась обработка {filename}')
            patches_img = pch(large_img, (patch_size, patch_size, 3), step=patch_size)  #Нарезаем изображение large_img на патчи
            patches_img = patches_img[:,:,0,:,:,:] #Убираем лишние измерения, т.к. patchify возвращает патчи с доп. размерностью (rows, cols, height, width, channels)
            patched_prediction = [] #Инициализируем список для хранения обработки по каждому пачу

            for i in range(patches_img.shape[0]):
                for j in range(patches_img.shape[1]):

                    single_patch_img = patches_img[i,j,:,:,:]

                    #нормализация парта + добавление batch
                    single_patch_img = scaler.fit_transform(single_patch_img.reshape(-1, single_patch_img.shape[-1])).reshape(single_patch_img.shape)
                    single_patch_img = np.expand_dims(single_patch_img, axis=0)

                    pred = model.predict(single_patch_img) #вызов модели
                    pred = np.argmax(pred, axis=3)

                    pred = pred[0, :,:] #возвращаем двухметрую размерность
                    patched_prediction.append(pred) #добавляем патч в список

            #Переформатируем массив в исходную сетку патчей (чтобы соответствовало нарезке)
            patched_prediction = np.array(patched_prediction)
            patched_prediction = np.reshape(patched_prediction, [patches_img.shape[0], patches_img.shape[1], patches_img.shape[2], patches_img.shape[3]])

            #Скревиваем патчи обратно и сохраняет изображение в tif
            unpatched_prediction = unpch(patched_prediction, (large_img.shape[0], large_img.shape[1]))
            temp_saved_prediction = f'{temp_saved_folder}/predicted_{filename}.tif'
            imageio.imsave(temp_saved_prediction, unpatched_prediction)
            plt.imshow(unpatched_prediction, cmap = 'gray')
            plt.axis('off')
            output_image_path = f'{output_folder}/{filename}_completed.tif'
            log_action(f'Обработка моделью завершена')

            #Восстанавливаем геопривязку через rasterio
            # Получаем метаданные и геопривязку исходного изображения
            with rasterio.open(input_imgfile) as src:
                meta = src.meta
                geotransform = src.transform

                # Открываем обработанное изображение
                with rasterio.open(temp_saved_prediction) as src_cropped:
                    # Прочитайте все бэнды кропнутого изображения
                    cropped_image = src_cropped.read()

                # Присваиваем метаданные исходного изображения к метаданными кропнутого изображения
                meta.update(width=src_cropped.width, height=src_cropped.height, count=cropped_image.shape[0])

                # Сохранение каналов исходного изображения
                with rasterio.open(output_image_path, 'w', **meta) as dst:

                    for i in range(cropped_image.shape[0]):
                        dst.write(cropped_image[i, :, :], i + 1)

                    # геопривязку для результирующего датасета
                    dst.transform = geotransform

                    log_action(f'Геопривязка для {filename} восстановлена')

            os.remove(temp_saved_prediction)
            log_action(f'Обработанный растр {filename} сохранен в формате tif')

            # Формируем путь для сохранения векторного файла
            output_shapefile = os.path.join(output_folder, f'{filename}_completed.shp')

            # Открываем растровое изображение
            with rasterio.open(output_image_path) as src:
                # Получаем геопривязку и количество классов
                transform = src.transform
                num_classes = len(src.colorinterp)
                # Читаем растровые данные и векторизуем
                image = src.read(1)
                vector_shapes = list(rasterio_shapes(image, mask=None, transform=transform))
                # Создаем новый векторный файл
                schema = {
                    'geometry': 'Polygon',
                    'properties': {'class': 'int'},
                }
                with fiona.open(output_shapefile, 'w', 'ESRI Shapefile', schema, crs=src.crs) as output:
                  # Записываем геометрию и атрибуты векторного файла
                  for shape, value in vector_shapes:
                      feature = {
                          'geometry': shape,
                          'properties': {'class': value},
                      }
                      output.write(feature)
            # Выводим информацию о геопривязке и количестве классов
            log_action(f'Векторизация растра {filename} проведена успешно. Shape-файл сохранен')
            print("======================================")


    if 'username' not in session:
        return redirect(url_for('login'))

    file_path = session.get('file_path')
    if not file_path:
        flash('Сначала загрузите файл')
        return render_template('upload.html',role=session['role'], user=session['username'], session_id=SESSION_ID, processed=session.get('processed', False), error='Сначала загрузите файл')

    session['processed'] = True
    print(f"session['processed'] : {session['processed']}")

    return

#Архивация в .7z
def create_7z_from_files(starting_name, source_folder, archive_filename):
    """
    Создает архив .7z, содержащий файлы с именем, начинающимся на `starting_name` и заканчивающимся на `_completed`,
    из папки `source_folder`.

    :param starting_name: Начальное имя файла для поиска
    :param source_folder: Папка, в которой ищутся файлы
    :param archive_filename: Полное имя создаваемого архива
    """
    log_action(f'Начато создание архива для экспорта')
    valid_extensions = {'.tif', '.shp', '.cpg', '.dbf', '.prj', '.shx'}
    # Создаем архив
    with py7zr.SevenZipFile(archive_filename, 'w') as archive:
        # Перебираем файлы в исходной папке
        files_added = False  # Флаг для проверки добавления файлов
        for filename in os.listdir(source_folder):
            # Полный путь к файлу
            file_path = os.path.join(source_folder, filename)

            # Проверяем, если имя файла оканчивается на '_completed' перед расширением и это файл (не папка)
            if os.path.isfile(file_path):
                base_name, ext = os.path.splitext(filename)
                print(f"base_name -- {base_name}")

                if base_name.endswith('_completed') and base_name.startswith(starting_name):

                    file_extension = os.path.splitext(filename)[1].lower()

                    if file_extension in valid_extensions:
                      archive.write(file_path, arcname=filename)

                      log_action(f'Файл {filename} добавлен в архив {archive_filename}')
                      files_added = True

        if not files_added:
            print('Нет файлов для добавления в архив. Убедитесь, что файлы существуют и соответствуют критериям.')
            log_action('Сформирован пустой архив')

    log_action(f'Создание архива завершено. Архив сохранен как {archive_filename}')

@app.route('/save_local', methods=['POST'])

#Сохранить на локальной машине
def save_local():
    if 'username' not in session:
        return redirect(url_for('login'))

    file_path = session.get('file_path')
    if not file_path:
        flash('Сначала загрузите файл')
        return render_template('upload.html',role=session['role'], session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error='Сначала загрузите файл')


    print(f"Началось создание архива")
    starting_name = os.path.splitext(os.path.basename(file_path) )[0]

    source_folder = f'{base_path}/download folder'
    archive_filename = f'{source_folder}/{starting_name}_completed.7z'

    create_7z_from_files(starting_name,source_folder,archive_filename)

    # Проверяем существование созданного архива
    if not os.path.exists(archive_filename):
        flash('Не удалось создать архив')
        log_action(f"Не удалось создать архив: {archive_filename}")
        return render_template('upload.html',role=session['role'], session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error='Не удалось создать архив')

    # Отправляем архив пользователю для скачивания
    log_action('Архив сохранен локально')
    return send_file(archive_filename, as_attachment=True)

@app.route('/save_drive', methods=['POST'])
def save_drive():
    if 'username' not in session:
        return redirect(url_for('login'))

    file_path = session.get('file_path')
    if not file_path:
        flash('Сначала загрузите файл')
        return render_template('upload.html',role=session['role'], session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error='Сначала загрузите файл')

    # Создаем ZIP-архив
    starting_name = os.path.splitext(os.path.basename(file_path))[0]
    source_folder = f'{base_path}/download folder'
    archive_filename = f'{source_folder}/{starting_name}_completed.7z'
    create_7z_from_files(starting_name,source_folder,archive_filename)

    # Проверяем существование созданного архива
    if not os.path.exists(archive_filename):
        flash('Не удалось создать архив')
        log_action(f"Не удалось создать архив: {archive_filename}")  # Debug print
        return render_template('upload.html',role=session['role'],session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error='Не удалось создать архив')
    try:
        dst_folder = f'{base_path}/folder for save'
        os.makedirs(dst_folder, exist_ok=True)
        dst_path = os.path.join(dst_folder, os.path.basename(archive_filename))
        os.rename(archive_filename, dst_path)
        log_action(f'Файл успешно сохранен на Google Drive ({dst_path})')
    except Exception as e:
        flash(f'Ошибка при сохранении файла на Google Drive: {str(e)}')
        log_action(f'Ошибка при сохранении файла на Google Drive: {str(e)}')
        return render_template('upload.html', session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error=f'Ошибка при сохранении файла на Google Drive (archive_filename - {archive_filename}):: {str(e)}')
    return render_template('upload.html',role=session['role'], user=session['username'], session_id=SESSION_ID, processed=session.get('processed', False), message=f'Файл успешно сохранен на Google Drive ({archive_filename}')

@app.route('/download_from_drive', methods=['POST'])

def download_from_drive():
    if 'username' not in session:
        return redirect(url_for('login'))

    file_name = request.form.get('file')
    if not file_name:
        flash('Файл не выбран')
        return render_template('upload.html',role=session['role'], session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error='Файл не выбран')

    file_path = os.path.join(base_path, file_name)
    if not os.path.exists(file_path):
        flash('Файл не найден на сервере')
        return render_template('upload.html',role=session['role'], session_id=SESSION_ID, processed=session.get('processed', False), user=session['username'], error='Файл не найден на сервере')

    # Сохраняем путь к файлу для последующей обработки
    session['file_path'] = file_path
    log_action(f"Начата обработка серверного файла {file_path}")
    process(file_path)
    if session['processed']:
      log_action(f"Успешно завершена обработка серверного файла {file_path}")
      return render_template('upload.html',role=session['role'], user=session['username'], session_id=SESSION_ID, processed=session.get('processed', False), message=f'Серверный файл {file_name} успешно обработан!')
    elif not session['processed']:
      return render_template('upload.html',role=session['role'], user=session['username'], session_id=SESSION_ID, processed=session.get('processed', False), error=f'Не удалось прочитать изображение {file_name}')

@app.route('/download_log', methods=['POST'])

#Выгрузить лог
def download_log():
    if session['role'] != 'adm':
        log_action('У вас нет доступа к этому разделу')
        flash('У вас нет доступа к этому разделу')
        return redirect(url_for('upload'))

    log_file_path = os.path.join(app.config['DRIVE_FOLDER'], 'session_log.txt') 
    if not os.path.exists(log_file_path):
        log_action('Лог-файл не найден')
        flash('Лог-файл не найден')
        return redirect(url_for('upload'))

    log_action(f"{session['username']} выгрузил лог")
    return send_file(log_file_path, as_attachment=True)

@app.route('/list_files', methods=['GET'])

#Список для обработки с сервера
def list_files():
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        files = os.listdir(app.config['DRIVE_FOLDER'])
        tif_files = [file for file in files if file.endswith('.tif')]
        return jsonify({'files': tif_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Запуск сессии
public_url = ngrok.connect(5000)
log_action(f"Сессия запустилась по адресу: {public_url}")
print("URL для доступа к приложению:", public_url)

if __name__ == '__main__':
    app.run(port=5000)
