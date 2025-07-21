import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# from webdriver_manager.chrome import ChromeDriverManager
# service = Service(ChromeDriverManager().install())

print("Starting setup...")

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service()
driver = webdriver.Chrome(service=service, options=options)

def scrape_profile(url, member_type=''):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.fieldSubContainer.labeledTextContainer"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        profile_data = {
            "Company Name": "",
            "Contact Name": "",
            "Phone": "",
            "Email": "",
            "City": "",
            "Province": "",
            "Website": "",
            "Member Type": member_type
        }

        containers = soup.select("div.fieldSubContainer.labeledTextContainer")
        fields = {}
        for container in containers:
            label = container.select_one(".fieldLabel span")
            value = container.select_one(".fieldBody span, .fieldBody a")
            if label and value:
                fields[label.text.strip()] = value.text.strip()

        profile_data["Contact Name"] = f"{fields.get('First name', '')} {fields.get('Last name', '')}".strip()
        profile_data["Company Name"] = fields.get("Company", "")
        profile_data["Email"] = fields.get("Email", "")
        profile_data["Website"] = fields.get("Web Site", "")
        profile_data["City"] = fields.get("City", "")
        profile_data["Province"] = fields.get("Province/State", "")

        return profile_data
    except Exception as e:
        print(f"Error scraping profile {url}: {e}")
        return {}

try:
    print("✅ Browser launched.")
    driver.get("https://www.ontariosignassociation.com/member-directory")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#idPagingData select"))
    )

    container = driver.find_element(By.ID, "idPagingData")
    select = Select(container.find_element(By.TAG_NAME, "select"))
    page_values = [option.get_attribute("value") for option in select.options]

    member_links = []

    for value in page_values:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#idPagingData select"))
        )
        container = driver.find_element(By.ID, "idPagingData")
        select = Select(container.find_element(By.TAG_NAME, "select"))
        select.select_by_value(value)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "membersTable"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table#membersTable tbody > tr.normal")

        pagelimit = 50  # 50 - default, 2 - test
        count = 0
        for row in rows:
            if count >= pagelimit:
                break
            count += 1

            a_tag = row.find("a")
            if not a_tag or not a_tag.has_attr("href"):
                continue
            profile_url = a_tag["href"]
            if not profile_url.startswith("http"):
                profile_url = "https://www.ontariosignassociation.com" + profile_url

            text = a_tag.get_text(strip=True)
            member_type = "Associate" if text.endswith("(1)") else "Producer"

            member_links.append((profile_url, member_type))

    print(f"\nTotal member: {len(member_links)}")

    all_members = []
    for i, (url, mtype) in enumerate(member_links, 1):
        print(f"🔍 [{i}/{len(member_links)}] Scraping {url}")
        profile_data = scrape_profile(url, mtype)
        if profile_data:
            all_members.append(profile_data)

    driver.quit()

    df = pd.DataFrame(all_members)
    df.to_excel("ontario_sign_members.xlsx", index=False)
    print("\nExported data to 'ontario_sign_members.xlsx'")

except Exception as e:
    print("Failed to run scraper.")
    print("Error:", e)
