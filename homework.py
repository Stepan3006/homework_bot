import time
import os
from telegram import Bot
import requests
import logging
from dotenv import load_dotenv
from http import HTTPStatus
import sys

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат.
    Jпределяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимаем на вход
    два параметра: экземпляр класса Bot и строку
    с текстом сообщения.
    """
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logging.info(f'Бот успешно отправил сообщение Telegram: {message}')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Делаем запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получаем временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error('Эндпойнт не доступен, программа остановлена')
        raise Exception(
            f'Oшибочный статус ответа по Api{homework_statuses.status_code}'
        )
    response = homework_statuses.json()
    return response


def check_response(response):
    """Проверяем ответ API на корректность.
    В качестве параметра
    функция получает ответ API, приведенный к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна
    вернуть список домашних работ (он может быть и пустым),
    доступный в ответе API по ключу 'homeworks'.
    """
    if type(response) != dict:
        logging.error(f'В {response} отсутствует словарь')
        raise TypeError(
            f'В {response} отсутствует словарь'
        )
    if type(response.get('homeworks')) != list:
        logging.error(f'В {response}отсутствует список')
        raise Exception(
            f'В {response}отсутствует список'
        )
    return response


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ. В случае успеха, функция возвращает
    подготовленную для отправки в Telegram строку, содержащую один
    из вердиктов словаря HOMEWORK_STATUSES.
    """
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
    except Exception as error:
        logging.error(f'Ошибка в ключах {error}')
        raise KeyError
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(f'Неизвестный статус домашней работы{homework_status}')
        raise Exception('Неизвестный статус домашней работы')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    logging.info(f'Новый статус домашней работы :{homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения
    — функция должна вернуть False, иначе — True.
    """
    if PRACTICUM_TOKEN or TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is not None:
        return True
    else:
        return False


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Не заданы переменные аутитентификации', exc_info=True
        )
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response).get('homeworks')
            if homework != []:
                logging.info('Статус домашней работы обновлен')
                message = parse_status(homework[0])
                current_timestamp = int(time.time())
                if last_status != message:
                    send_message(bot, message)
                    last_status = message
            else:
                logging.debug('Новых статусов  у работ нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
