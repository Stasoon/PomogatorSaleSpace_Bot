import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import gspread
from gspread import SpreadsheetNotFound, Spreadsheet
from gspread.worksheet import Worksheet
from oauth2client.service_account import ServiceAccountCredentials


class GoogleSheetsAPI:
    _executor = None
    _loop = None
    _client = None

    @staticmethod
    def get_table_url(table_id: str) -> str:
        return f'https://docs.google.com/spreadsheets/d/{table_id}'

    @classmethod
    async def make_auth(cls, credentials_filename: str = 'google_sheets_credentials.json') -> None:
        if cls._client:
            return

        if not os.path.exists(credentials_filename):
            raise ValueError(f'Файл {os.path.join(os.getcwd(), credentials_filename)} не найден!')

        cls._loop = asyncio.get_event_loop()
        cls._executor = ThreadPoolExecutor()

        # Подключаемся к Google Sheets API с использованием учетных данных
        scopes = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(filename=credentials_filename, scopes=scopes)
        client = await cls._loop.run_in_executor(cls._executor, gspread.authorize, credentials)
        cls._client = client

    @classmethod
    async def create_table(cls, table_name: str, title_data: list[str] = None) -> str:
        # Создаем новую таблицу
        spreadsheet: Spreadsheet = await cls._loop.run_in_executor(cls._executor, cls._client.create, table_name)

        if title_data:
            await cls._loop.run_in_executor(cls._executor, spreadsheet.sheet1.insert_row, title_data, 1)

            await cls.set_sheet_styles(spreadsheet.sheet1)

        # Делаем таблицу доступной для всех пользователей
        await cls._loop.run_in_executor(cls._executor, spreadsheet.share, '', 'anyone', 'reader')

        return spreadsheet.id

    @classmethod
    async def set_sheet_styles(cls, sheet: Worksheet):
        await cls._loop.run_in_executor(cls._executor, sheet.freeze, 1)
        # Стили шапки
        await cls._loop.run_in_executor(cls._executor, sheet.format, 'A1:R1', {
            "backgroundColor": {'red': 0.6, 'green': 0.75, 'blue': 0.95},
            'borders': {'bottom': {'style': 'SOLID'}}
        })
        # Текст (шрифт)
        await cls._loop.run_in_executor(cls._executor, sheet.format, 'A1:K1000', {
            'textFormat': {"fontFamily": "Comfortaa"}
        })
        # Установка ширины столбцов
        # await cls._loop.run_in_executor(cls._executor, sheet.dimension, 'A:J', 'auto')

    @classmethod
    async def insert_row_data(cls, table_id: str, data: list[any], position: int = None):
        spreadsheet = await cls._loop.run_in_executor(cls._executor, cls._client.open_by_key, table_id)

        # Получаем доступ к листу таблицы
        sheet: Worksheet = spreadsheet.sheet1

        # Определяем номер последней строки
        if not position:
            row_count = len(await cls._loop.run_in_executor(cls._executor, sheet.get_all_values))
        else:
            row_count = position

        # Добавляем данные
        data = [str(i) for i in data]
        await cls._loop.run_in_executor(cls._executor, sheet.insert_row, data, row_count + 1)

        return spreadsheet.url

    @classmethod
    async def edit_cell(cls, table_id: str, data: any, xy: tuple[int, int]):
        spreadsheet = await cls._loop.run_in_executor(cls._executor, cls._client.open_by_key, table_id)
        sheet: Worksheet = spreadsheet.sheet1
        await cls._loop.run_in_executor(cls._executor, cls._client.open_by_key, table_id)
        await cls._loop.run_in_executor(cls._executor, sheet.update_cell, *xy, data)

    @classmethod
    async def is_table_exists(cls, table_id: str) -> bool:
        try:
            await cls._loop.run_in_executor(cls._executor, cls._client.open_by_key, table_id)
        except SpreadsheetNotFound:
            return False
        return True

    @classmethod
    async def delete_row(cls, table_id: str, number: int):
        spreadsheet = await cls._loop.run_in_executor(cls._executor, cls._client.open_by_key, table_id)
        sheet: Worksheet = spreadsheet.sheet1
        sheet.delete_rows(start_index=number+1)
