import argparse
import requests
from bs4 import BeautifulSoup
import logging
import altair as alt
import pandas as pd
import datetime
from typing import List, Dict, Any
from configs import ALL_PRODUCTS, STORES_DICT

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-30s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_meta_info(product: str, store: str) -> Dict:
    sku = None
    brand = None
    description = None
    availability = None
    price_currency = None
    price_amount = None
    url = None

    if ALL_PRODUCTS[product][store] is not None:
        url = ALL_PRODUCTS[product][store]
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        if store == "the_bar":
            sku = soup.find("meta", property="product:sku")
            brand = soup.find("meta", property="product:brand")
            price_currency = soup.find(
                "meta", property="product:price:currency")
            availability = soup.find("meta", property="product:availability")
            price_amount = soup.find("meta", property="product:price:amount")

            sku = sku['content'] if sku else None
            brand = brand['content'] if brand else None
            price_currency = price_currency['content'] if price_currency else None
            availability = availability['content'] if availability else None
            price_amount = float(
                price_amount['content']) if price_amount else None

        elif store == "casadabebida":
            sku = soup.find(itemprop="sku").get_text()
            brand = soup.find(itemprop="brand").get_text().strip()

            description = soup.find("meta", property="og:title")
            description = description['content'] if description else None

            price_currency = soup.find(itemprop="priceCurrency").get("content")
            availability = soup.find(itemprop="availability").get(
                "content").split("/")[-1]
            price_amount = float(soup.find(itemprop="price").get_text())

    infos = {
        "sku": sku,
        "marca": brand,
        "descricao": description,
        "disponibilidade": availability,
        "preco_moeda": price_currency,
        "preco_valor": price_amount,
        "loja": STORES_DICT[store],
        "data": datetime.datetime.now().isoformat(),
        "url": url
    }
    return infos


if __name__ == '__main__':
    logger.info(f"::.. STARTING WHISKY 🥃  CRAWLING PROCESS")
    my_parser = argparse.ArgumentParser(prog='python whisky_crawler.py',
                                        usage='%(prog)s [options] --loja',
                                        description='Crawls stores for whisky prices and stores CSV file')
    my_parser.add_argument('--loja', action='store',
                           type=str, required=True, default="casadabebida")
    args = my_parser.parse_args()
    logger.info(
        f"::.. ARGUMENTS {args} ")

    file_output = f"output/dataframe_{args.loja}.csv"
    old_df = pd.read_csv(file_output, index_col=0,
                         parse_dates=True, infer_datetime_format=True)

    data = [get_meta_info(x, "casadabebida") for x in ALL_PRODUCTS.keys()]
    new_df = pd.DataFrame(data=data, columns=[
        "marca", "descricao", "disponibilidade", "loja", "sku", "preco_moeda", "preco_valor", "data", "url"])
    new_df.sort_values(by="preco_valor", ascending=True, inplace=True)
    new_df = new_df.reset_index(drop=True)
    new_df = new_df.set_index('data')
    logger.info(
        f"::.. DATAFRAME FOR {args.loja} HAS {len(new_df)} ENTRIES")

    store_df = pd.concat([old_df, new_df], axis=0)
    store_df.to_csv(file_output)
    logger.info(
        f"::.. DATAFRAME STORED 💾 IN {file_output}")

    # Plot results using Altair
    chart_output = f"chart_whisky.png"
    logger.info(
        f"::.. PLOTTING RESULTS 📊 {chart_output}")

    plot_df = store_df.reset_index()
    plot_df = plot_df[["data", "marca", "preco_valor"]]
    chart = alt.Chart(plot_df).mark_line().encode(
        x='data:T',
        y='preco_valor:Q',
        color='marca'
    ).properties(
        title="Whisky Price Trends",
        width=840,
        height=320,
    )
    chart.save(chart_output)
