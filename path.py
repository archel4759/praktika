import os
import ipywidgets as widgets
from IPython.display import display

from google.colab import drive
drive.mount("/content/drive", force_remount=True)

global base_path, model_path, login_db_path
base_path = None # корневой каталог
model_path = None # путь к нейросетевой модели сегментации болот
login_db_path = None # путь к БД учетных записей

#Проверка расширений
def check_extension(filename, extension):
    return filename.lower().endswith(extension.lower())

#Функция поэтапного заполнения путей 
def handle_path_input(sender):
    global base_path, model_path, login_db_path
    
    if base_path is None:
        if os.path.exists(sender.value):
            base_path = sender.value
            print(f"Корневой каталог сохранён: {base_path}")
            ask_model_path()
        else:
            print("Ошибка: указанный путь не существует!")
    
    elif model_path is None:
        full_model_path = os.path.join(base_path, sender.value)
        if os.path.exists(full_model_path):
            if check_extension(sender.value, '.hdf5'):
                model_path = full_model_path
                print(f"Путь к модели сохранён: {model_path}")
                ask_login_db_path()
            else:
                print("Ошибка: файл модели должен иметь расширение .hdf5!")
        else:
            print("Ошибка: файл модели не найден по указанному пути!")
    
    elif login_db_path is None:
        full_db_path = os.path.join(base_path, sender.value)
        if os.path.exists(full_db_path):
            if check_extension(sender.value, '.sqlite'):
                login_db_path = full_db_path
                print(f"Путь к БД учётных записей сохранён: {login_db_path}")
            else:
                print("Ошибка: файл БД должен иметь расширение .sqlite!")
        else:
            print("Ошибка: файл БД не найден по указанному пути!")

def ask_model_path():
    model_input = widgets.Text(
        placeholder='Введите путь к модели .hdf5 и нажмите Enter',
        description='Модель:',
        layout=widgets.Layout(width='80%')
    )
    model_input.on_submit(handle_path_input)
    display(model_input)

def ask_login_db_path():
    db_input = widgets.Text(
        placeholder='Введите путь к БД учетных записей и нажмите Enter',
        description='БД:',
        layout=widgets.Layout(width='80%')
    )
    db_input.on_submit(handle_path_input)
    display(db_input)


path_input = widgets.Text(
    placeholder='Введите путь к корневому каталогу и нажмите Enter',
    description='Каталог:',
    layout=widgets.Layout(width='80%')
)
path_input.on_submit(handle_path_input)
display(path_input)