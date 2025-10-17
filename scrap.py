#scrap.py
#Scrap code for downloading all documents related to car purchase invoices
#
#Python v3.12
#Playwright
#Selectolax


import os
import asyncio


from urllib.parse import urljoin
from playwright.async_api import async_playwright
from selectolax.parser import HTMLParser




BASE_URL = "https://www.uvo.gov.sk"
SEARCH_URL = (
    "https://www.uvo.gov.sk/vyhladavanie/globalne-vyhladavanie"
    "?searchType=ALL&globalSearch=nakup+avtomobilov"
)
SAVE_DIR = "dokumenty"
os.makedirs(SAVE_DIR, exist_ok=True)


#################### All links on the page ####################
async def get_document_page_links(page) -> list[str]:

    html = await page.content()
    tree = HTMLParser(html)

    links = []
    for a in tree.css("a"):
        href = a.attributes.get("href", "")
        if "/dokumenty/" in href:
            full_url = urljoin(BASE_URL, href)
            if full_url not in links:
                links.append(full_url)
    print(f"{len(links)} pages of documents")

    return links


#################### Opening one page ####################
async def process_document_page(page, link: str, page_number: int = 0):

    try:
        await page.goto(link, wait_until="networkidle", timeout=40000)
        print(f"\ndocuments page opened |{page_number}|: {link}")

        html_docs = await page.content()
        tree = HTMLParser(html_docs)
        rows = tree.css("tr[onclick]")

        

        if not rows:
            print("!!!No documents on this page!!!")
            return
        print(f"{len(rows)} documents found")


        for i, row in enumerate(rows, start=1):
            onclick = row.attributes.get("onclick", "")
            if "window.location.href" not in onclick:
                continue

            
            start = onclick.find("'") + 1
            end = onclick.rfind("'")
            doc_url = urljoin(BASE_URL, onclick[start:end])
            await process_single_document(page, doc_url, i)

    except Exception as e:
        print(f"!!!!Error opening document page {link}: {e}")



#################### Opening one order ####################
async def process_single_document(page, doc_url: str, index: int):

    try:
        await page.goto(doc_url, wait_until="networkidle", timeout=40000)
        print(f"({index}) document opened: {doc_url}")

        html = await page.content()
        tree = HTMLParser(html)


        download_links = tree.css("a[href*='download']")
        if not download_links:
            print("NO downloadable files on this document page")
            return


        print(f"----------------------Found {len(download_links)} files to download")

        for k, link_tag in enumerate(download_links, start=1):
            file_href = link_tag.attributes.get("href")
            if not file_href:
                continue

            print(f"----------------------({k}/{len(download_links)}) downloading file...")
            await download_file(page, file_href)

    except Exception as e:
        print(f"ERROR processing document: {e}")



#################### Downloading a file ####################
async def download_file(page, file_href: str):
    try:
        async with page.expect_download() as download_info:
            await page.click(f"a[href='{file_href}']")
        download = await download_info.value


        file_name = download.suggested_filename
        save_path = os.path.join(SAVE_DIR, file_name)
        await download.save_as(save_path)
        print(f"----------------------file downloaded: {file_name}")

    except Exception as e:
        print(f"!!!!Download error!!!!: {e}")



#################### Main ####################
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page_docs = await browser.new_page()

        current_url = SEARCH_URL
        page_count = 1

        while True:
            print(f"\npage №{page_count}: {current_url}")
            await page.goto(current_url, wait_until="load", timeout=40000)
            await asyncio.sleep(2)

            document_pages = await get_document_page_links(page)
            


            for doc_link in document_pages:
                await process_document_page(page_docs, doc_link, page_count)


            html = await page.content()
            tree = HTMLParser(html)
            next_link = tree.css_first('a[title="Ďalšia"]')
            if not next_link:
                print("ALL files downloaded")
                break

            href = next_link.attributes.get("href")
            current_url = urljoin(current_url, href)
            page_count += 1

        await page_docs.close()
        await page.close()
        await browser.close()



if __name__ == "__main__":
    asyncio.run(main())

