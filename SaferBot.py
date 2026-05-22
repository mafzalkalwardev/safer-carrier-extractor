from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options
import pandas as pd
import time
import os
import signal

# Define paths
template_path = "template.csv"
url = "https://safer.fmcsa.dot.gov/CompanySnapshot.aspx"
output_csv = "records.csv"

template_df = pd.read_csv(template_path)
columns = template_df.columns.tolist()

necessary_columns = ["legal name", "address", "telephone", "email"]
for column in necessary_columns:
    if column not in columns:
        columns.append(column)

initial_id = 1725914
process_interrupted = False

def signal_handler(sig, frame):
    global process_interrupted
    process_interrupted = True
    print("Process interrupted by user")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ✅ No webdriver-manager — use your local EXE
def initialize_driver():
    options = Options()
    options.use_chromium = True
    return webdriver.Edge(
        service=EdgeService("msedgedriver.exe"),
        options=options
    )

driver = initialize_driver()

def validate_data(flattened_data, columns):
    if len(flattened_data) != len(columns):
        flattened_data.extend([''] * (len(columns) - len(flattened_data)))
    return flattened_data

def save_to_csv(data, output_csv, columns):
    df = pd.DataFrame([data], columns=columns)
    if not os.path.isfile(output_csv):
        df.to_csv(output_csv, index=False)
    else:
        df.to_csv(output_csv, mode='a', header=False, index=False)

try:
    while not process_interrupted:
        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/form/p/table/tbody/tr[2]/td[2]/input"))
            )
            driver.find_element(By.XPATH, "/html/body/form/p/table/tbody/tr[2]/td[2]/input").click()
            driver.find_element(By.XPATH, "/html/body/form/p/table/tbody/tr[3]/td/input").send_keys(str(initial_id))
            driver.find_element(By.XPATH, "/html/body/form/p/table/tbody/tr[4]/td/input").click()
            if len(driver.find_elements(By.XPATH, "/html/body/table/tbody/tr[2]/td/p/font/b/i")) > 0:
                initial_id += 1
                continue
            table_xpath = "/html/body/p/table/tbody/tr[2]/td/table/tbody/tr[2]/td/center[1]/table/tbody"
            table_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, table_xpath))
            )
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            new_rows = []
            start_removing = False
            for row in rows:
                if not start_removing and "Operation Classification:" in row.get_attribute("outerHTML"):
                    start_removing = True
                if start_removing:
                    continue
                new_rows.append(row)
            data = []
            for row in new_rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                data.append([col.text for col in cols])
            if len(data) > 0:
                flattened_data = [item for sublist in data for item in sublist]
                validated_data = validate_data(flattened_data, columns)
                save_to_csv(validated_data, output_csv, columns)
            link_xpath = "/html/body/p/table/tbody/tr[2]/td/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr[3]/td[2]/font/a"
            driver.find_element(By.XPATH, link_xpath).click()
            driver.switch_to.window(driver.window_handles[-1])
            driver.find_element(By.XPATH, "/html/body/div[3]/div[2]/article/div[2]/div[2]/section/a[1]").click()
            email_container = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "regBox"))
            )
            ul_element = email_container.find_element(By.CLASS_NAME, "col1")
            li_elements = ul_element.find_elements(By.TAG_NAME, "li")
            extracted_data = {"legal name": "", "address": "", "telephone": "", "email": ""}
            for li in li_elements:
                text = li.text.lower()
                if "legal name" in text:
                    extracted_data["legal name"] = li.text.split(":", 1)[-1].strip()
                elif "address" in text:
                    extracted_data["address"] = li.text.split(":", 1)[-1].strip()
                elif "telephone" in text:
                    extracted_data["telephone"] = li.text.split(":", 1)[-1].strip()
                elif "email" in text:
                    extracted_data["email"] = li.text.split(":", 1)[-1].strip()
            if any(extracted_data.values()):
                df = pd.read_csv(output_csv)
                for key, value in extracted_data.items():
                    df.at[df.index[-1], key] = str(value)
                df.to_csv(output_csv, index=False)
            driver.get(url)
            initial_id += 1
        except Exception as e:
            print(f"Error encountered: {e}")
            time.sleep(5)
            driver.get(url)
            initial_id += 1
except KeyboardInterrupt:
    print("Process interrupted by user")
finally:
    driver.quit()
