from openai import OpenAI
import openai
import requests
import json
import os
from bs4 import BeautifulSoup
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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



headers = {
    'X-API-KEY' : congress_api_key
    }

start_date = '2024-02-11'
end_date = '2024-02-18'

url = f'https://api.congress.gov/v3/summaries?fromDateTime={start_date}T00:00:00Z&toDateTime={end_date}T00:00:00Z&sort=updateDate+asc'

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    print('Response code 200 - all good!')
else:
    print(f"Failed to retrieve data: {response.status_code}")

bills = data['summaries']

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

    #print(len(bill_congresses), len(bill_types), len(bill_numbers))
    #print()
    #print(f'Date: {action_date}; {current_chamber}; {action_desc}; Updated: {update_date}\n{clean_text}')

pdf_urls = []

with requests.Session() as session :
    req_try = 1
    for bcong, btype, bnumb in zip(bill_congresses, bill_types, bill_numbers):
        text_url = f'https://api.congress.gov/v3/bill/{bcong}/{btype.lower()}/{bnumb}/text?api_key={congress_api_key}'

        try:
            link_response = session.get(text_url)
            #print(req_try)
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
        except requests.RequestException as e:
                print(f"Request failed: {e}")
        req_try += 1

syst_instr = 'You are an experienced U.S. congressional reporter with over 18 years on the beat. Your new job includes sending weekly updates on the bills under consideration in Congress. You turn the bill summaries into one paragraph stories, up to 200 words, in narrative form, on what each bill is about, including important details such as costs; industries, groups or organizations affected, timeframes, etc. Your audience includes well-read Americans interested in politics and government.'
stories = []

print(f'Number of prompts: {len(prompts)}')

try_num = 1

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
        print(f'{try_num} prompt(s) completed')
        try_num += 1
        time.sleep(1)
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

print(f'Number of stories: {len(stories)}')
#for story in stories:
#    print(story)
#    print()
print(len(bill_titles), len(bill_actdescs), len(bill_actdates), len(stories), len(pdf_urls))
email_content = ""
counter = 1
for title, bill_actdesc, bill_actdate, story, pdf_url in zip(bill_titles, bill_actdescs, bill_actdates, stories, pdf_urls):
    print(counter)
    email_content += f"'{title}' \n{bill_actdesc} as of {bill_actdate}\n{story}\nPDF at: {pdf_url}\n\n"
    counter += 1

print(email_content)

sender_email = "your_email@example.com"
receiver_email = "receiver@example.com"
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



