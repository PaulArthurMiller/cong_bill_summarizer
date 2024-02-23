from openai import OpenAI
import openai
#from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
import json
import os
from bs4 import BeautifulSoup
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#load_dotenv()
#for name, value in os.environ.items():
# print("{0}: {1}".format(name, value))

# Checking for API key access

congress_api_key = os.getenv('CONGRESS_API_KEY')
if congress_api_key is not None:
    print("Congress API Key found!")
else:
    print("Congress API Key not found. Please set it as an environment variable.")

openai.api_key = os.getenv('OPENAI_API_KEY')
if openai.api_key is not None:
    print("OpenAI API Key found!")
else:
    print("OpenAI API Key not found. Please set it as an environment variable.")

# Setting up the first Congress.gov API call for summaries
    
headers = {
    'X-API-KEY' : congress_api_key
    }

today = datetime.now()
days_to_last_monday = (today.weekday() - 0) % 7 + 7
last_monday = today - timedelta(days=days_to_last_monday)
last_sunday = last_monday + timedelta(days=6)
start_date = last_monday.strftime('%Y-%m-%d')
end_date = last_sunday.strftime('%Y-%m-%d')

url = f'https://api.congress.gov/v3/summaries?fromDateTime={start_date}T00:00:00Z&toDateTime={end_date}T00:00:00Z&sort=updateDate+asc'

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    print('Response code 200 - all good!')
else:
    print(f"Failed to retrieve data: {response.status_code}")

bills = data['summaries']

# Collecting the information for the bills from the object

bill_congresses = []
bill_numbers = []
bill_types = []
bill_titles = []
bill_actdates = []
bill_actdescs = []
prompts = []

for bill in bills :
    action_date = bill.get('actionDate')
    action_desc = bill.get('actionDesc')
    bill_title = bill.get("bill", {}).get("title", "No title found")
    bill_congress = bill.get("bill", {}).get("congress", "No congress found")
    bill_number = bill.get("bill", {}).get("number", "No bill number found")
    bill_type = bill.get("bill", {}).get("type", "No bill type found")
    current_chamber = bill.get('currentChamber')
    update_date = bill.get('updateDate')
    summary_text = bill.get('text')

    bill_congresses.append(bill_congress)
    bill_numbers.append(bill_number)
    bill_types.append(bill_type)
    bill_titles.append(bill_title)
    bill_actdates.append(action_date)
    bill_actdescs.append(action_desc)

    soup = BeautifulSoup(summary_text, "html.parser")
    clean_text = soup.get_text(separator=" ")
    prompts.append(clean_text)

    print('Prompts: ', len(prompts))
    print("bill_numbers: ", len(bill_numbers))
    print()

# Selecting the pdfs from the bill summary information
    
pdf_urls = []

with requests.Session() as session :
    for bcong, btype, bnumb in zip(bill_congresses, bill_types, bill_numbers):
        text_url = f'https://api.congress.gov/v3/bill/{bcong}/{btype.lower()}/{bnumb}/text?api_key={congress_api_key}'

        try:
            link_response = session.get(text_url)
            time.sleep(1)

            if link_response.status_code == 200:
                text_data = link_response.json()
                last_text_version = text_data["textVersions"][-1]

                pdf_url = ""

                for format_dict in last_text_version["formats"]:
                    if format_dict["type"] == "PDF":
                        pdf_url = format_dict["url"]
                        break

                if pdf_url:
                    pdf_urls.append(pdf_url)
                else:
                    pdf_url = "PDF URL not found."
                    pdf_urls.append(pdf_url)
                    print(pdf_url)
            else:
                print(f"Failed to fetch data for {bcong}-{btype}-{bnumb}: {link_response.status_code}")
                pdf_url = "PDF URL not found."
                pdf_urls.append(pdf_url)

        except requests.RequestException as e:
                print(f"Request failed: {e}")

# Setting up the OpenAI model, running through the prompts, then collecting the responses as 'stories'

syst_instr = 'You are an experienced U.S. congressional reporter with over 18 years on the beat. Your new job includes sending weekly updates on the bills under consideration in Congress. You turn the bill summaries into one paragraph stories, up to 200 words, in narrative form, on what each bill is about, including important details such as costs; industries, groups or organizations affected, timeframes, etc. Your audience includes well-read Americans interested in politics and government.'
stories = []

for prompt in prompts:
    try:
        response = openai.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[
                {"role": "system", "content": syst_instr},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        time.sleep(3)
    except openai.RateLimitError:
        print("Rate limit exceeded. Waiting before retrying.")
        time.sleep(60)
    except openai.BadRequestError as e:
        print(f"Invalid request: {str(e)}")
    except openai.OpenAIError as e:
        print(f"An OpenAI error occurred: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

    model_response = response.choices[0].message.content
    stories.append(model_response)

# Gathering together the information for the email from the various API calls

email_content = ""
for title, bill_actdesc, bill_actdate, story, pdf_url in zip(bill_titles, bill_actdescs, bill_actdates, stories, pdf_urls):
    email_content += f"'{title}' \n{bill_actdesc} as of {bill_actdate}\n{story}\nPDF at: {pdf_url}\n\n"

print(email_content)

# Setting up the email for sending

sender_email = os.getenv('SENDER_EMAIL_ADDR')
if sender_email is not None:
    print("Sender Email found!")
else:
    print("Sender email not found. Please set it as an environment variable.")

receiver_email = os.getenv('RECEIVER_EMAIL_ADDR')
if receiver_email is not None:
    print("Receiver Email found!")
else:
    print("Receiver email not found. Please set it as an environment variable.")

password = input("Type your password and press enter: ")

msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = "Weekly Bill Summaries"

msg.attach(MIMEText(email_content, 'plain'))

try:
    server = smtplib.SMTP('smtp.example.com', 587)  # SMTP server and port
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")



