# Congressional Bill Summaries Emailer

This Python script fetches the latest congressional bill summaries from Congress.gov, generates short, journalistic stories for each bill using OpenAI's GPT model, and emails the compiled summaries. It provides well-read Americans interested in politics and government with weekly updates on the bills under consideration in Congress with links to the full bill PDFs.

## Features

- Fetches bill summaries from Congress.gov using their public API.
- Utilizes OpenAI's GPT-3.5-turbo model to generate concise narratives for each bill.
- Compiles an email with all bill summaries and sends it to a specified recipient.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.8+
- Congress.gov API key
- OpenAI API key
- SMTP server credentials

## Installation

1. Clone the repository to your local machine:
   ```
   git clone https://github.com/paularthurmiller/cong_bill_summarizer.git
   ```
2. Navigate to the project directory:
   ```
   cd cong_bill_summarizer
   ```
3. Create a Conda environment with the required packages:
   ```
   conda env create -f environment.yml
   ```
4. Activate the Conda environment:
   ```
   conda activate myenv
   ```

## Configuration

1. Set your Congress.gov and OpenAI API keys as environment variables:
   ```
   export CONGRESS_API_KEY='your_congress_api_key'
   export OPENAI_API_KEY='your_openai_api_key'
   ```
2. Set your SMTP server details and email credentials as environment variables. Adjust the script to match your SMTP server's configuration.

## Usage

Run the script with the following command:
```
python cong_bill_summarizer.py
```


## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Paul A. Miller - paularthurmiller@gmail.com
