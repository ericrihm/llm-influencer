from langchain.chat_models import ChatOpenAI
import pandas as pd
import random
import utils
from prompts.quote import QUOTE_PROMPT, NOTE_TEXT
from prompts.image import IMAGE_PROMPT
from datetime import datetime
from openai import Image
import os
import requests
import warnings
from api.twitter import Twitter
from pathlib import Path
from twitter_text import parse_tweet
warnings.filterwarnings('ignore')
import configparser
import logging
logging.getLogger().setLevel(logging.INFO)

cur_path = Path().cwd() / 'influence'

config = configparser.RawConfigParser()
config.read(cur_path / 'config.ini')

tweeter = Twitter(config=config['twitter'])

os.environ["OPENAI_API_KEY"] = config['openai']['api_key']

tweet_parser_config = {'max_weighted_tweet_length':140}

class Config:
    SSL_VERIFY = True

class Orchestrator:

    def __init__(self):
        self.config = config
        self.llm = ChatOpenAI(temperature=.9, model = 'gpt-3.5-turbo')
        quotes_df = pd.read_json(open('data/finalq.json','r'))

        auth_list = quotes_df['Author'].unique().tolist()
        self.auth = auth_list[random.randint(0,len(auth_list))]
        auth_quotes = quotes_df[quotes_df['Author'] == self.auth]['Quote'].tolist()
        q_list = random.sample(auth_quotes, 4)
        self.fquotes = utils.format_quotes(q_list=q_list)

    def create_quote(self):
        q_prompt = QUOTE_PROMPT.format(author=self.auth.title(), quotes=self.fquotes)
        self.quote = self.llm.predict(q_prompt).replace('"','')
        logging.info(f'{q_prompt}\n----------')
    
    def inspire_image(self):
        i_prompt = IMAGE_PROMPT.format(quote=self.quote)
        dalle_prompt = self.llm.predict(i_prompt)

        logging.info(f'{i_prompt}\n----------')
        logging.info(f'{dalle_prompt}\n----------')
        return dalle_prompt

    def create_image(self, prompt):
        image_url = Image.create(prompt=prompt, size='1024x1024')['data'][0]['url']
        filepath = cur_path / f"gen_images/{datetime.now().strftime('%d%b%y')}.jpg"
        filepath.touch()
        response = requests.get(url=image_url, stream=True, verify=Config.SSL_VERIFY)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath
    
    def run(self):
        valid_tweet = False
        while not valid_tweet:
            self.create_quote()
            if parse_tweet(self.quote, options=tweet_parser_config).valid:
                prompt = self.inspire_image()
                filepath = self.create_image(prompt)
                valid_tweet=True

        tweet_text = self.quote
        logging.info(f'\n\nTWEET TEXT:\n{tweet_text}\n{NOTE_TEXT}')
        tweet_id = tweeter.tweet(filename=filepath, text=tweet_text)
        tweeter.reply_to_tweet(tweet_id=tweet_id, text=NOTE_TEXT)

if __name__=='__main__':
    orchestrator = Orchestrator()
    orchestrator.run()




