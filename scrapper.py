from email.mime import text
import keyword
import unicodedata
from dataclasses import dataclass
import re
import time
from pathlib import Path
import unicodedata
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from requests.exceptions import ChunkedEncodingError, ConnectionError, ReadTimeout
import urllib3
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import pandas as pd

##-------- Imports from other codes --------##
from db_data import EmtpDb
from pandasgui import show


class WebScrapper:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.chrome_options = Options()
        self.set_options()

        self.driver = None
        self.wait = None

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session = requests.Session()

    def set_options(self):
        self.chrome_options.add_argument("--window-size=1200,800")
        self.chrome_options.add_argument("--disable-popup-blocking")
        self.chrome_options.add_argument("--disable-extensions-file-access-check")
        self.chrome_options.add_argument("--allow-running-insecure-content")

        self.chrome_options.add_argument(
            "--disable-features=OptimizationGuideModelDownloading"
        )

        self.chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging"]
        )

    def start_driver(self):
        if self.driver is None:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.wait = WebDriverWait(self.driver, 10)

    def open_web_page(self, url) -> bool:
        try:
            if self.driver is None:
                self.start_driver()

            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True

        except Exception:
            return False

    def transfer_cookies_to_requests(self) -> None:
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(cookie["name"], cookie["value"])

    def sync_user_agent(self) -> None:
        ua = self.driver.execute_script("return navigator.userAgent;")
        self.session.headers["User-Agent"] = ua

    def prepare_requests_context(self) -> None:
        self.session = requests.Session()
        self.transfer_cookies_to_requests()
        self.sync_user_agent()
        self.session.headers.update(
            {
                "Accept": "*/*",
                "Accept-Language": "es-CL,es;q=0.9",
            }
        )
        self.session.headers["Referer"] = self.driver.current_url

    def download_file(
        self,
        file_url: str,
        file_path: Path,
        max_retries: int = 8,
        timeout=(10, 1800),
        chunk_size: int = 1024 * 1024,
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        self.prepare_requests_context()

        downloaded = file_path.stat().st_size if file_path.exists() else 0

        for attempt in range(1, max_retries + 1):
            headers = {}
            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"

            try:
                with self.session.get(
                    file_url,
                    verify=False,
                    allow_redirects=True,
                    stream=True,
                    timeout=timeout,
                    headers=headers,
                ) as response:

                    if downloaded > 0 and response.status_code == 200:
                        downloaded = 0
                        file_path.unlink(missing_ok=True)

                    if response.status_code not in (200, 206):
                        raise RuntimeError(
                            f"HTTP response instead of file. Final URL: {response.url}"
                        )

                    mode = "ab" if downloaded > 0 else "wb"
                    with open(file_path, mode) as f:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)

                return

            except (ChunkedEncodingError, ConnectionError, ReadTimeout):
                wait = min(2**attempt, 60)
                time.sleep(wait)

        raise RuntimeError(
            f"Failed to download file after {max_retries} retries: {file_url}."
        )

    def restart_session(self) -> None:
        if self.driver is not None:
            try:
                self.driver.delete_all_cookies()
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
                self.wait = None

        if self.session:
            try:
                self.session.close()
            except Exception:
                pass

        self.session = requests.Session()
        time.sleep(1)


class Correspondence(WebScrapper):
    def __init__(self, **kwargs):
        self.username = kwargs.pop("username", "")
        self.password = kwargs.pop("password", "")
        debug = kwargs.pop("debug", False)
        super().__init__(debug)

        self.signin_url = "https://correspondencia.coordinador.cl/login?next=%2Fcorrespondencia%2Fshow%2Frecibido%2F681a3bf43563574dd6dd83ad"
        self.search_url = (
            "https://correspondencia.coordinador.cl/correspondencia/busqueda"
        )

    def goto_signin_url(self) -> None:
        ok = self.open_web_page(self.signin_url)
        if not ok:
            raise RuntimeError("No se pudo abrir la página de inicio de sesión.")

        self.click_login_btn()
        self.click_continue_btn()
        self.insert_credentials()

        input(
            "Ingresa tus credenciales manualmente en la ventana del navegador, "
            "haz login y luego presiona ENTER aquí para continuar..."
        )

        self.wait.until(lambda d: "correspondencia.coordinador.cl" in d.current_url)

        self.sync_user_agent()
        self.transfer_cookies_to_requests()

    def go_to_search_page(self) -> None:
        self.driver.get(self.search_url)
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    def click_login_btn(self) -> None:
        login_btn = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[normalize-space()='Ingresar'] | //a[normalize-space()='Ingresar']",
                )
            )
        )
        login_btn.click()
        self.wait.until(
            EC.url_contains("https://correspondencia.coordinador.cl/login_token")
        )

    def click_continue_btn(self) -> None:
        continue_btn = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='button' and @value='Coordinador-Acceso-Unificado']",
                ),
            )
        )

        self.driver.execute_script(
            """
            arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            arguments[0].dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));
            """,
            continue_btn,
        )

        self.wait.until(lambda d: "nidp/saml2" in d.current_url)
        self.wait.until(EC.url_contains("hub.coordinador.cl/nidp/saml2/sso"))

    def insert_credentials(self) -> None:
        username_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "Ecom_User_ID"))
        )
        password_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "Ecom_Password"))
        )

        if self.username:
            username_input.clear()
            username_input.send_keys(self.username)

        password_input.click()

    def click_unified_login_btn(self) -> None:
        self.wait.until(EC.url_contains("https://correspondencia.coordinador.cl"))

    def search(
        self,
        keyword: str = None,
        from_date: datetime = datetime(2022, 1, 1),
        to_date: datetime = datetime.now(),
        doc_type: str = "T",
        company: str = None,
    ) -> None:
        """Performs a search in the web scrapper with the given parameters."""

        from_day = from_date.day if from_date else ""
        from_month = from_date.month if from_date else ""
        from_year = from_date.year if from_date else ""

        to_day = to_date.day if to_date else ""
        to_month = to_date.month if to_date else ""
        to_year = to_date.year if to_date else ""
        period_subs = (
            f"&period={from_day}%2F{from_month}%2F{from_year}+-+{to_day}%2F{to_month}%2F{to_year}"
            if from_date
            else ""
        )
        company_subs = f"&empresa={company}" if company else ""
        doc_type_subs = f"&doc_type={doc_type}"

        condition = (
            keyword
            and doc_type in ["R", "E", "OP", "T"]
            and (type(from_date) in [datetime, type(None)])
            and (type(to_date) in [datetime, type(None)])
        )

        if not condition:
            raise ValueError("Invalid search parameters. Please check the inputs.")

        url = f"https://correspondencia.coordinador.cl/correspondencia/busqueda?query={keyword}{period_subs}{company_subs}{doc_type_subs}"

        self.driver.get(url)
        self.transfer_cookies_to_requests()


class PendingLettersFinder(Correspondence):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run_pending_searches(
        self, pending_df: pd.DataFrame, doc_types: list[str]
    ) -> pd.DataFrame:
        pending_df["Status"] = None
        pending_df["New_Correlative"] = None
        N_row = -1
        for row in pending_df.itertuples(index=False):
            N_row = N_row + 1
            msgid = row.MsgID
            msgdate = row.MsgDate
            correlativo = row.Correlativo
            company = row.CompanyName
            sender = row.SenderName
            subject = row.Subject
            unit = row.UnitName
            print(f"Running search for unit '{unit}'")
            if subject == None:
                continue
            else:
                new_correlative, status = self.run_search(
                    keyword=subject,
                    doc_type="E",
                    company=company,
                    msgdate=msgdate,
                    unit=unit,
                )
                pending_df.at[N_row, "Status"] = status
                pending_df.at[N_row, "New_Correlative"] = new_correlative
        print(pending_df)
        return pending_df

    def run_search(
        self,
        keyword: list[str],
        doc_type: str,
        company: list[str],
        msgdate: str,
        unit: str,
    ) -> tuple[str, str]:
        """Returns a dictionary of received messages containing any of the keywords,
        with the following structure: {'code1': 'url1', 'code2': 'url2', ...}.
        """

        self.search(
            keyword=keyword,
            doc_type=doc_type,
            from_date=datetime(2022, 1, 1),
            company=company,
        )
        # search_results = self.scrapper.get_all_search_results()
        # messages.update(search_results)
        new_correlative, status = self.process_rows(
            msgdate=msgdate, keyword=keyword, unit=unit
        )
        return new_correlative, status

    def process_rows(self, msgdate: str, keyword: str, unit: str) -> list[dict]:

        rows = self.driver.find_elements(
            By.XPATH, "//table[contains(@class, 'table-hover')]//tr[td]"
        )
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                link_element = cells[0].find_element(By.TAG_NAME, "a")

                row_correlativo = cells[0].text.strip()
                row_href = link_element.get_attribute("href")
                row_date = cells[2].text.strip()
                row_reference = cells[7].text.strip()

                is_date_in_range = self.is_in_date_range(row_date, msgdate)
                is_keyword_in_reference = self.is_keyword_in_reference(
                    keyword, row_reference
                )
                is_lab_id_in_reference = self.is_lab_id_in_reference(
                    row_reference, row_correlativo
                )

                if is_date_in_range and is_keyword_in_reference:
                    unit = self.normalize_text(unit)
                    is_unit_in_reference = unit in self.normalize_text(row_reference)
                    if is_unit_in_reference:
                        status = "Found Unit in Reference"
                        print(f"Unit '{unit}' is in reference: {is_unit_in_reference}")
                        return row_correlativo, status
                    else:
                        self.open_web_page(row_href)

                elif is_date_in_range and is_lab_id_in_reference:
                    print(
                        f"Lab ID '{row_correlativo}' is in reference: {is_lab_id_in_reference}"
                    )
                    status = "Found Lab ID"
                    return row_correlativo, status

            except Exception:
                new_correlativo = ""
                status = "No Message"
                print("There are no more results to fetch.")
                return new_correlativo, status
        return "", "No Message"

    def is_in_date_range(self, date1: str, date2: str) -> bool:
        try:
            d1 = pd.to_datetime(date1, dayfirst=True)
            d2 = pd.to_datetime(date2, dayfirst=True)
            return d1 >= d2
        except ValueError:
            print(
                f"Error parsing dates: '{date1}' or '{date2}' is not in the expected format."
            )
            return False

    def extract_responde(self, text: str) -> str | None:
        match = re.search(r"(Responde\s+a\s+DE\d{5}-\d{2})", text, re.IGNORECASE)
        return match.group(1) if match else None

    def normalize_text(self, text: str) -> str:
        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        return text

    def is_in_date_range(self, date1: str, date2: str) -> bool:
        try:
            d1 = pd.to_datetime(date1, dayfirst=True)
            d2 = pd.to_datetime(date2, dayfirst=True)
            return d1 >= d2
        except ValueError:
            print(
                f"Error parsing dates: '{date1}' or '{date2}' is not in the expected format."
            )
            return False

    def is_keyword_in_reference(self, keyword: str, row_reference: str) -> bool:
        target = self.extract_responde(keyword)

        target_norm = self.normalize_text(target)
        reference_norm = self.normalize_text(row_reference)
        match = target_norm in reference_norm
        print(f"Match found: {match}")
        return match

    def is_lab_id_in_reference(self, row_reference: str, lab_id: str) -> bool:
        pattern = r"\(LabID\s*(\d+)\)"
        match = re.search(pattern, row_reference)

        if not match:
            return False

        found_lab_id = match.group(1)
        return True


class DataShower:
    def __init__(self, data):
        self.data = data

    def show(self):
        print(self.data)


if __name__ == "__main__":
    Plf = None

    try:
        Plf = PendingLettersFinder(debug=True)
        db = EmtpDb()
        df = db.get_pending_with_review2()

        print("Abriendo portal de correspondencia...")
        Plf.goto_signin_url()

        print("Login detectado. Yendo a la página de búsqueda...")
        Plf.go_to_search_page()

        print("Página de búsqueda abierta correctamente.")
        print("URL actual:", Plf.driver.current_url)

        pending_df = Plf.run_pending_searches(pending_df=df, doc_types=["E"])
        print("Resultados de las búsquedas:")
        print(pending_df)
        input("Presiona ENTER para cerrar el navegador...")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if Plf and Plf.driver is not None:
            Plf.driver.quit()
