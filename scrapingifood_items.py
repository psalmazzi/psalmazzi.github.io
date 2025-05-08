#pip install playwright pandas beautifulsoup4
#playwright install

import asyncio
from playwright.async_api import async_playwright
import pandas as pd
from bs4 import BeautifulSoup
import random
from datetime import datetime
import os

# Configurações
CITY = "Piracicaba"
STATE = "SP"
SEARCH_TERMS = ["x salada","hot dog","cachorro quente"]
MAX_RESTAURANTS_PER_TERM = 0  # Limite para demonstração // Zero para deixar sem limite
OUTPUT_FOLDER = "scraped_data"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class IFoodScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
        ]
        
    async def get_page_content(self, page, url):
        """Acessa a URL com headers aleatórios e retorna o conteúdo"""
        try:
            await page.set_extra_http_headers({
                'User-Agent': random.choice(self.user_agents),
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
            })
            
            await page.goto(url, timeout=60000)
            await page.wait_for_selector('.merchant-list-carousel', timeout=15000)
            
            # Clicar em "Ver Mais"
            
            async def has_closed_card():
                return await page.query_selector('.merchant-list-with-item-carousel--closed') is not None
        
            async def scroll_and_click_more():
                while True:
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(2) 
                    
                    try:
                        await page.click('button[variant="cardstack-nextcontent__button"]', timeout=3000)
                        print("Clicou em 'Ver Mais'")
                        await asyncio.sleep(3) 
                        return True
                    except:
                        print("Botão 'Ver Mais' não encontrado")
                        if await has_closed_card():
                            return False
                        continue
            
            while True:
                success = await scroll_and_click_more()
                if not success:
                    break
                
                if await has_closed_card():
                    print("Card closed encontrado - terminando")
                    break
            
            await page.evaluate('window.scrollTo(0, 0)')
            print("Retornou ao topo da página")
            
            # Scroll lento para carregar imagens
            
            scroll_increment = 600
            loaded_images = []
            scroll_attempts = 0
            max_attempts = 10000  # Limite de segurança

            while scroll_attempts < max_attempts:
                scroll_attempts += 1
                
                await page.evaluate(f'window.scrollBy(0, {scroll_increment})')
                await asyncio.sleep(1)  # Espera o lazy loading
                
                current_height = await page.evaluate('document.documentElement.scrollHeight')
                scroll_position = await page.evaluate('window.innerHeight + window.pageYOffset')
                
                if scroll_position >= current_height:
                    print("Chegou ao final da página")
                    break
                
                current_images = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('.swiper-slide img'))
                        .filter(img => !img.src.startsWith('data:'))
                        .map(img => img.src);
                }''')
                
                new_images = [img for img in current_images if img not in loaded_images]
                if new_images:
                    loaded_images.extend(new_images)
                
            return await page.content()
            
        except Exception as e:
            print(f"Erro ao acessar {url}: {str(e)}")
            return None

    def parse_restaurant_data(self, html):
        """Extrai dados dos restaurantes do HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        restaurants = []
        
        soup.select('.merchant-list-carousel')
        all_carousels = soup.select('.merchant-list-carousel')
        valid_carousels = [carousel for carousel in all_carousels 
                  if not carousel.find_parent(class_='merchant-list-with-item-carousel--closed')]
        
        for card in valid_carousels:
            try:
                lanchonete = card.select_one('.merchant-list-carousel__merchant-title').get_text(strip=True)
                rating = card.select_one('.cardstack-rating') and card.select_one('.cardstack-rating').get_text(strip=True)
                link = card.find('a', class_='merchant-list-carousel__merchant').get('href')
                slides = card.select('.swiper-slide')      
                if slides:
                    primeiro_slide = slides[0]
                    produto = primeiro_slide.select_one('.merchant-list-carousel__item-title').get_text(strip=True) if primeiro_slide.select_one('.merchant-list-carousel__item-title') else None
                    precoR = primeiro_slide.select_one('.card-stack-item-price--regular').get_text(strip=True) if primeiro_slide.select_one('.card-stack-item-price--regular') else None
                    precoP = primeiro_slide.select_one('.card-stack-item-price--promotion').get_text(strip=True) if primeiro_slide.select_one('.card-stack-item-price--promotion') else None
                    foto = primeiro_slide.select_one('.cardstack-image img').get('src')   
                
                restaurants.append({
                    'lanchonete': lanchonete,
                    'rating': rating or 'Não avaliado',
                    'link': link,
                    'preco': precoR or precoP,
                    'foto':foto,
                    'produto':produto,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                print(f"Erro ao parsear restaurante: {e}")
                continue
                
        return restaurants

    async def scrape_search_term(self, term):
        """Raspa dados para um termo de busca específico"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            url = f"https://www.ifood.com.br/busca?q={term}&tab=1&sort=price_range%3Aasc&term={term}&city={CITY}&state={STATE}"
            print(f"Iniciando scraping para: {term}")
            
            html = await self.get_page_content(page, url)
            if not html:
                return []
                
            restaurants = self.parse_restaurant_data(html)
            await browser.close()
            
            if MAX_RESTAURANTS_PER_TERM==0:
                return restaurants             
            return restaurants[:MAX_RESTAURANTS_PER_TERM]

    async def run(self):
        """Executa o scraping para todos os termos de busca"""
        all_data = []
        
        for term in SEARCH_TERMS:
            try:
                restaurants = await self.scrape_search_term(term)
                for r in restaurants:
                    r['search_term'] = term
                all_data.extend(restaurants)
                
                # Salva dados parciais
                df = pd.DataFrame(all_data)
                df.to_csv(f"{OUTPUT_FOLDER}/ifood_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
                
                # Intervalo aleatório entre buscas
                await asyncio.sleep(random.uniform(5, 10))
                
            except Exception as e:
                print(f"Erro no termo '{term}': {e}")
                continue
                
        return all_data
    
def filtrar_avaliacoes(x):
    return (x != 'Não avaliado') & (x != 'Novidade')

# Execução principal
async def main():
    scraper = IFoodScraper()
    data = await scraper.run()
    
    # Salva dados finais
    df = pd.DataFrame(data)
    output_file = f"{OUTPUT_FOLDER}/ifood_final_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Scraping completo! Dados salvos em: {output_file}")
    print(f"Total de restaurantes coletados: {len(df)}")
    
    # Exemplo de análise rápida
    if not df.empty:
        print("\n📊 Estatísticas:")
        print(df.groupby('search_term').size())
        print("\n⭐ Média de avaliações por termo:")
        print(df.groupby('search_term')['rating'].apply(lambda x: x[filtrar_avaliacoes(x)].astype(float).mean()))

if __name__ == "__main__":
    asyncio.run(main())