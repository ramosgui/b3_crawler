import json
import time
import os
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tkinter import Tk, Button, Label
from constants import *
from parser_json import order_json

TRANSACTIONS = []


def get_element(driver, xpath: str, timeout: int = 10, raise_error: bool = True):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )
    except TimeoutException as e:
        if raise_error:
            raise e
    else:
        return element

def get_element_by_class(driver, class_name: str, timeout: int = 10, raise_error: bool = True):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CLASS_NAME, class_name))
        )
    except TimeoutException as e:
        if raise_error:
            raise e
    else:
        return element

def create_popup():
    popup = Tk()
    popup.title("Ação necessária")

    popup.geometry("400x100-2300+300")

    popup.attributes('-topmost', True)

    # Configurar o layout do popup
    label = Label(popup, text="Resolva o CAPTCHA e clique em CLOSE para seguir a automação.")
    label.pack(pady=10)

    # Botão de fechar
    close_button = Button(popup, text="CLOSE", command=popup.destroy)
    close_button.pack(pady=5)

    # Manter o popup aberto
    popup.mainloop()

def format_dt(raw_date: str):
    _map = {'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'ABRIL': 4, 'MAIO': 5, 'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8,
            'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12}
    day, raw_month, year = raw_date.split(' DE ')
    month = _map.get(raw_month)
    return datetime(int(year), int(month), int(day)).strftime('%Y-%m-%d')

def format_number(raw_number: str):
    if isinstance(raw_number, float):
        return raw_number
    else:
        try:
            return float(raw_number.replace('.', '').replace(',', '.'))
        except ValueError:
            return raw_number

def format_price(raw_price: str):
    price = raw_price.replace('R$ ', '')
    return format_number(price)

async def format_transaction(transaction, raw_trx_dt: str):
    raw_in_out = transaction.find_element(By.CLASS_NAME, 'cdk-column-tipoOperacao').text
    raw_type = transaction.find_element(By.CLASS_NAME, 'cdk-column-tipoMovimentacaoFormatado').text
    raw_product = transaction.find_element(By.CLASS_NAME, 'cdk-column-nomeProduto').text
    raw_qtd = transaction.find_element(By.CLASS_NAME, 'cdk-column-quantidade').text
    raw_unit_price = transaction.find_element(By.CLASS_NAME, 'cdk-column-precoUnitario').text
    raw_total_price = transaction.find_element(By.CLASS_NAME, 'cdk-column-valorOperacao').text

    return {
        'in_out': 'in' if raw_in_out == 'ENTRADA' else 'out',
        'type': raw_type,
        'product': raw_product,
        'qtd': format_number(raw_qtd),
        'raw_unit_price': raw_unit_price,
        'unit_price': format_price(raw_unit_price),
        'raw_total_price': raw_total_price,
        'total_price': format_price(raw_total_price),
        'id': hash(transaction.text),
        'date': format_dt(raw_trx_dt)
    }

async def thread_asset(transaction_content):
    raw_transaction_dt = transaction_content.text.split("\n")[0]
    transactions = transaction_content.find_elements(By.CLASS_NAME, "cdk-row")

    for transaction in transactions:
        formatted_transaction = await format_transaction(transaction, raw_transaction_dt)
        TRANSACTIONS.append(formatted_transaction)

async def get_assets(driver):
    assets_dt = get_element_by_class(driver, class_name="tabela-desktop", raise_error=False)
    if assets_dt:
        assets_dt_elements = driver.find_elements(By.CLASS_NAME, "tabela-desktop")

        trxs = 0
        for transaction_content in assets_dt_elements:
            transactions = transaction_content.find_elements(By.CLASS_NAME, "cdk-row")
            trxs += len(transactions)

        print(f'> Processando {trxs} transações encontradas, aguarde...')

        # Executa o filtro de forma assíncrona
        await asyncio.gather(*(thread_asset(transaction_content) for transaction_content in assets_dt_elements))

    else:
        print(f'> Nenhuma transação encontrada.')

    return assets_dt


def abrir_tela_movimentacao(driver):
    input_usuario = click_element(driver, xpath=USER_INPUT_XPATH)
    input_usuario.send_keys(os.getenv('USER'))

    # enter button
    click_element(driver, xpath=ENTER_BUTTON_XPATH)

    input_pass = click_element(driver, xpath=PASSWORD_INPUT_XPATH)
    input_pass.click()
    input_pass.send_keys(os.getenv('PASS'))

    # Chama a função para exibir o popup e aguarda ele ser fechado
    create_popup()

    # ENTER
    click_element(driver, xpath=CONTINUE_BUTTON_XPATH)

    # REJEITA COOKIES
    click_element(driver, xpath=REJECT_COOKIES_XPATH)

    # PULAR TOUR
    click_element(driver, xpath=SKIP_TOUR_XPATH)

    # ACESSAR MOVIMENTAÇÃO
    driver.get(MOVIMENTACAO_URL)

def click_element(driver, xpath):
    element = get_element(driver, xpath)
    time.sleep(1)
    element.click()
    return element


def get_date_filters(start_date_limit: str, end_date_limit: str):
    dt_filters = []

    start_date = datetime.strptime(start_date_limit, '%d/%m/%Y')
    end_date = datetime.strptime(end_date_limit, '%d/%m/%Y')

    dt_control = start_date

    while dt_control < end_date:
        s_dt = dt_control
        e_dt = dt_control + relativedelta(years=1)

        if e_dt > end_date:
            dt_filters.append({'start_date': s_dt, 'end_date': end_date})
        else:
            dt_filters.append({'start_date': s_dt, 'end_date': e_dt})

        dt_control = e_dt + timedelta(days=1)

    return dt_filters

async def thread_filter(driver, dt_filter):
    input_start_element = get_element_by_class(driver, "input-start")
    input_start_element.clear()
    input_start_element.send_keys(dt_filter['start_date'].strftime('%d%m%Y'))

    input_end_element = get_element_by_class(driver, "input-end")
    input_end_element.clear()
    input_end_element.send_keys(dt_filter['end_date'].strftime('%d%m%Y'))

    print(f"\nFiltrando transações entre os dias {dt_filter['start_date'].strftime('%d/%m/%Y')} e {dt_filter['end_date'].strftime('%d/%m/%Y')}")
    click_element(driver=driver, xpath=MODAL_FILTER_BUTTON_XPATH)

    await get_assets(driver)

    pagination_element = get_element(driver, xpath="//*[@id='paginacao-extrato-movimentacao']", raise_error=False)
    if pagination_element:
        next_page_element = get_element(driver, xpath=NEXT_PAGE_BUTTON_XPATH, raise_error=False)
        if next_page_element:
            print('> Navegando para a próxima página, aguarde...')
            next_page_element.click()

            while next_page_element:
                await get_assets(driver)
                next_page_element = get_element(driver, xpath=NEXT_PAGE_BUTTON_XPATH, raise_error=False)
                try:
                    next_page_element.click()
                    print('> Navegando para a próxima página, aguarde...')
                except ElementClickInterceptedException:
                    print('> Finalizado a navegação entre páginas.')
                    next_page_element = None

    # abre o filtro novamente
    click_element(driver=driver, xpath=FILTER_BUTTON_XPATH)

async def definir_filtros(driver):
    start_time = time.time()

    # clica no botão filtrar
    click_element(driver, xpath=FILTER_BUTTON_XPATH)

    # obtem data limite inferior
    start_raw_date_element = get_element(driver=driver, xpath=START_LIMIT_STRING_XPATH)
    start_date = start_raw_date_element.text.split(" ")[-1].strip('.')

    # obtem data limite superior
    input_end_element = get_element_by_class(driver, "input-end")
    input_end_element.clear()
    input_end_element.send_keys(datetime.now().strftime('%d%m%Y'))

    pagination_element = get_element(driver=driver, xpath=END_LIMIT_STRING_XPATH)
    str_dt_limit_end = pagination_element.text.split(" ")[-1]

    dt_filters = get_date_filters(start_date_limit=start_date, end_date_limit=str_dt_limit_end)

    for dt_filter in dt_filters:
        await thread_filter(driver=driver, dt_filter=dt_filter)

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Tempo de execução: {execution_time:.6f} segundos")


async def first_function():
    driver = webdriver.Firefox()
    driver.set_window_position(-1300, 100)
    driver.maximize_window()
    driver.get(FIRST_PAGE_URL)
    assert "Área do Investidor | B3" in driver.title

    try:
        abrir_tela_movimentacao(driver)
        await definir_filtros(driver)
    except Exception as e:
        raise e

    finally:

        driver.quit()

        # Salvar as transações no arquivo data.json
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(TRANSACTIONS, f, ensure_ascii=False, indent=4)

        order_json()

        print(f'\nScript executado com sucesso! Foram processadas {len(TRANSACTIONS)} transações no total.')


if __name__ == '__main__':
    asyncio.run(first_function())
