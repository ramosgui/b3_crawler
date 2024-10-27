import json
import time
import os
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tkinter import Tk, Button, Label
from selenium.webdriver.common.keys import Keys

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

def get_element_by_class(driver, class_name: str, timeout: int = 10):
    element = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CLASS_NAME, class_name))
    )
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

def format_transaction(transaction, raw_trx_dt: str):
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

def get_assets(driver):
    assets_dt = driver.find_elements(By.CLASS_NAME, "tabela-desktop")

    if assets_dt:

        time.sleep(2)

        all_transactions = []

        for transaction_content in assets_dt:
            raw_transaction_dt = transaction_content.text.split("\n")[0]

            print(f'Buscando transações do dia {raw_transaction_dt.lower()}...')

            transactions = transaction_content.find_elements(By.CLASS_NAME, "cdk-row")
            for transaction in transactions:
                formatted_transaction = format_transaction(transaction, raw_transaction_dt)
                # all_transactions.append(formatted_transaction)

                TRANSACTIONS.append(formatted_transaction)


def abrir_tela_movimentacao(driver):
    # Pega o elemento e faz login
    element = get_element(driver, "//*[@id='investidor']")
    element.click()
    element.send_keys(os.getenv('USER'))

    element = get_element(driver, "/html/body/app-root/app-landing-page/div/div[2]/aside/form/b3-button[1]/button/div")
    element.click()

    element = get_element(driver, "//*[@id='PASS_INPUT']")
    element.click()
    element.send_keys(os.getenv('PASS'))

    # Chama a função para exibir o popup e aguarda ele ser fechado
    create_popup()

    # Continuar execução após o popup ser fechado

    # ENTER
    element = get_element(driver, "//*[@id='Btn_CONTINUE']")
    element.click()

    # REJEITA COOKIES
    element = get_element(driver, "//*[@id='onetrust-reject-all-handler']")
    time.sleep(2)
    element.click()

    # PULAR TOUR
    element = get_element(driver,
                          "/html/body/app-root/app-core/app-tour-guiado-inicio/div/div/div/b3-button[1]/button/div/span")
    time.sleep(2)
    element.click()

    # ACESSAR MOVIMENTAÇÃO
    driver.get("https://www.investidor.b3.com.br/extrato/movimentacao")
    time.sleep(5)

def click_element(driver, xpath):
    element = get_element(driver, xpath)
    time.sleep(1)
    element.click()
    time.sleep(1)


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

    # dt_filters.append({'start_date': dt_control, 'end_date': end_date})
    return dt_filters


def definir_filtros(driver):
    # clica no botão filtrar
    click_element(driver, "/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/div/app-tabela-filtro/div/div/b3-button[1]/button")

    # obtem data limite inferior
    element = get_element(driver, "/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/app-movimentacao-filtrar/div/b3-modal-drawer/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/p")
    str_dt_limit = element.text.split(" ")[-1].strip('.')

    # obtem data limite superior
    input_end_element = get_element_by_class(driver, "input-end")
    input_end_element.clear()
    input_end_element.send_keys(datetime.now().strftime('%d%m%Y'))

    element = get_element(driver, '/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/app-movimentacao-filtrar/div/b3-modal-drawer/div[1]/div[2]/div/div[1]/div/div[2]/div[1]/app-datepicker-composto/div/form/b3-datepicker/div/b3-message/small')
    str_dt_limit_end = element.text.split(" ")[-1]

    dt_filters = get_date_filters(start_date_limit=str_dt_limit, end_date_limit=str_dt_limit_end)
    for dt_filter in dt_filters:

        input_start_element = get_element_by_class(driver, "input-start")
        input_start_element.clear()
        input_start_element.send_keys(dt_filter['start_date'].strftime('%d%m%Y'))

        input_end_element = get_element_by_class(driver, "input-end")
        input_end_element.clear()
        input_end_element.send_keys(dt_filter['end_date'].strftime('%d%m%Y'))

        # clica no botao filtrar
        click_element(driver, "/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/app-movimentacao-filtrar/div/b3-modal-drawer/div[1]/div[2]/div/div[2]/b3-button[1]/button")

        time.sleep(2)

        get_assets(driver)

        print('Verificar paginação....')

        element = get_element(driver, xpath="//*[@id='paginacao-extrato-movimentacao']", raise_error=False)
        if element:
            print('Paginação encontrada, mapeando...')
            next_page_element = get_element(driver,
                                            xpath="/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/div/div/*/b3-paginator/div/nav/ul/b3-paginator-lateral-button[3]/li/a/b3-icon/span", raise_error=False)

            if next_page_element:
                print('Próxima página encontrada, navegando até ela...')
                next_page_element.click()

                while next_page_element:

                    get_assets(driver)
                    time.sleep(2)

                    print('Procurando se existe próxima página...')
                    xpath1 = "/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/div/div/*/b3-paginator/div/nav/ul/b3-paginator-lateral-button[3]/li/a/b3-icon/span"
                    next_page_element = get_element(driver, xpath=xpath1, raise_error=False)

                    try:
                        next_page_element.click()
                        print('Próxima página encontrada, navegando até ela...')
                    except ElementClickInterceptedException:
                        print('Próxima página não encontrada, finalizando navegação entre páginas.')
                        next_page_element = None

                    time.sleep(2)


        # abre o filtro novamente
        click_element(driver, "/html/body/app-root/app-core/div/div/app-extrato/div/app-movimentacao/div/app-tabela-filtro/div/div/b3-button[1]/button")

        time.sleep(2)


def first_function():
    driver = webdriver.Firefox()
    driver.set_window_position(-1300, 100)
    driver.maximize_window()

    driver.get('https://www.investidor.b3.com.br/login?utm_source=B3_MVP&utm_medium=HM_PF&utm_campaign=menu')

    assert "Área do Investidor | B3" in driver.title

    try:
        abrir_tela_movimentacao(driver)

        definir_filtros(driver)

        # time.sleep(60)

    except Exception as e:
        raise e

    finally:
        # driver.quit()

        # Salvar as transações no arquivo data.json
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(TRANSACTIONS, f, ensure_ascii=False, indent=4)

        order_json()


if __name__ == '__main__':
    first_function()
