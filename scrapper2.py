import requests
from bs4 import BeautifulSoup
from pathlib import Path
import getpass


class WebScraper:
    def __init__(self, base_url: str, timeout: int = 20):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.soup = None
        self.last_response = None

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            }
        )

    def open_page(self, url: str | None = None) -> BeautifulSoup:
        target_url = url if url else self.base_url

        response = self.session.get(target_url, timeout=self.timeout)
        response.raise_for_status()

        self.last_response = response
        self.soup = BeautifulSoup(response.text, "html.parser")
        return self.soup

    def get_page_title(self) -> str:
        if not self.soup:
            raise ValueError("Primero debes abrir una página con open_page().")

        return self.soup.title.get_text(strip=True) if self.soup.title else "Sin título"


if __name__ == "__main__":
    url = "https://correspondencia.coordinador.cl/login?next=%2Fcorrespondencia%2Fshow%2Frecibido%2F681a3bf43563574dd6dd83ad"

    scraper = WebScraper(base_url=url)

    try:
        soup = scraper.open_page()
        print("Página abierta correctamente.")
        print("Título:", scraper.get_page_title())
    except requests.RequestException as e:
        print("Error al abrir la página:", e)
