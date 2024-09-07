import discord
from DrissionPage import WebPage
from bs4 import BeautifulSoup
import asyncio
import aiohttp
import ssl
import random
from datetime import datetime, timedelta
from config import TOKEN, CHANNEL_ID, URL

page = WebPage()

emoji_mapping = {        # for special emojis
    ":)": ":smilefata:",
    ";)": ":winkfata:",
    ":(": ":frownfata:",
    ":mad:": ":madfata:",
    ":confused:": ":confusedfata:",
    ":oops:": ":oopsfata:",
    ":cool:": ":coolfata:",
    ":p": ":stickouttonguefata:",
    ":D": ":grinbbnbfata:",
    ":eek:": ":eekfata:",
    ":ROFLMAO:": ":ROFLfata:",
    ":LOL:": ":laughfata:",
    ":love:": ":lovefata:",
    ":cry:": ":cryfata:",
    ":censored:": ":censoredfata:",
    ":cautious:": ":cautiousfata:",
    "o_O": ":o_ofata:",
    ":rolleyes:": ":rolleyesfata:",
    ":sick:": ":sickfata:",
    ":sleep:": ":sleepfata:",
    ":sneaky:": ":sneakyfata:",
    "(y)": ":thumbsupfata:",
    "(n)": ":thumbsdownfata:",
    ":unsure:": ":unsurefata:",
    ":whistle:": ":whistlefata:",
    ":coffee:": ":coffeefata:",
    ":giggle:": ":gigglefata:",
    ":poop:": ":poopfata:",
    ":geek:": ":geekfata:",
    ":devilish:": ":devilishfata:",
    ":alien:": ":alienfata:"
}

class FatalityClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_message_id = None  
        self.last_roll_time = datetime.now()  
        self.roll_cooldown = 6 
        self.processed_rolls = set()  

    async def start(self, *args, **kwargs):
        
        sslcontext = ssl.create_default_context()
        sslcontext.check_hostname = False
        sslcontext.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=sslcontext)

       
        self.http.connector = connector

        await super().start(*args, **kwargs)

    async def setup_hook(self):
       
        self.bg_task = self.loop.create_task(self.monitor_shoutbox())

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        if message.author == self.user:
            return


      # roll command
        if message.channel.id == CHANNEL_ID:
            if message.content.startswith("/roll"):
                current_time = datetime.now()
                if (current_time - self.last_roll_time).total_seconds() >= self.roll_cooldown:
                   
                    roll_result = random.randint(1, 6)
                    roll_response = f"{message.author.display_name} rolled a {roll_result}"
                   
                    page.get(URL)
                    input_box = page.run_js('return document.querySelector(".siropuShoutbox input.input");')
                    if input_box:
                        page.run_js(f'document.querySelector(".siropuShoutbox input.input").value = "{roll_response}";')
                        await asyncio.sleep(1)
                        page.run_js('document.querySelector(\'button[aria-label="Shout!"]\').click();')
                        print(f"Roll response sent to shoutbox: {roll_response}")

                    # Update last roll time
                    self.last_roll_time = current_time
                    self.processed_rolls.add(message.id)
            else:
                try:
                    page.get(URL)
                    
                    if page.url != URL:
                        raise Exception("Failed to load the page")
                    
                    await asyncio.sleep(1)  
                    
                    input_box = page.run_js('return document.querySelector(".siropuShoutbox input.input");')
                    
                    if not input_box:
                        raise Exception("Shoutbox input element not found.")

                    page.run_js(f'document.querySelector(".siropuShoutbox input.input").value = "{message.content}";')

                    await asyncio.sleep(1)
                    page.run_js('document.querySelector(\'button[aria-label="Shout!"]\').click();')
                    
                    await message.channel.send(f"Message sent to shoutbox: {message.content}")
                    
                except Exception as e:
                    print(f"An error occurred while sending the message: {e}")
                    await message.channel.send(f"Error occurred: {e}")

    def replace_emojis(self, content):
        """
        Replaces forum custom emojis in the content with corresponding Discord emojis.
        """
        soup = BeautifulSoup(content, 'html.parser')
        for img in soup.find_all('img', {'data-shortname': True}):
            shortname = img['data-shortname']
            if shortname in emoji_mapping:
                img.replace_with(emoji_mapping[shortname])
        return str(soup)

    async def monitor_shoutbox(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        
        print("Accessing shoutbox page...")
        page.get(URL)

        while not self.is_closed():
            try:
                print("Checking for new messages...")
                
                html = page.html  
                soup = BeautifulSoup(html, 'html.parser')
                shoutbox = soup.find('div', {'class': 'siropuShoutbox'}) 
                
                if shoutbox is None:
                    print("Not possible to find div that contains class 'siropuShoutbox'")
                    continue
                
                messages_container = shoutbox.find('ol', {'class': 'siropuShoutboxShouts'})
                
                if not messages_container:
                    print("Not possible to find ol that contains class 'siropuShoutboxShouts'")
                    continue

                messages = messages_container.find_all('li', {'class': 'js-lbContainer'})
                if messages:
                    print(f"Number of messages found: {len(messages)}")
                    new_messages = []

                    for message in reversed(messages):
                        timestamp_data = message.find('time', {'class': 'u-dt'})['data-time']
                        timestamp = f"<t:{timestamp_data}:R>" 

                        user_element = message.find('a', {'class': 'username'})
                        user = user_element.text.strip()
                        user_id = user_element['data-user-id']

                        role_check = user_element.find('span', class_=lambda c: c and c.startswith('username--style'))
                        if role_check:
                            role_class = role_check['class'][0]
                            if 'username--style5' in role_class:
                                user = f"(Premium) {user}"
                            elif 'username--style21' in role_class:
                                user = f"(Alpha) {user}"
                            elif 'username--style4' in role_class:
                                user = f"(Moderator) {user}"
                            elif 'username--style23' in role_class:
                                user = f"(Supporter) {user}"
                            elif 'username--style8' in role_class:
                                user = f"(Owner) {user}"
                            elif 'username--style2' in role_class:
                                user = f"(Member) {user}"
                            elif 'username--style17' in role_class:
                                user = f"(Banned) {user}"
                            elif 'username--style3' in role_class:
                                user = f"(Developer) {user}"
                            elif 'username--style30' in role_class:
                                user = f"(Designer) {user}"

                        content = message.find('span', {'class': 'siropuShoutboxMessage'}).decode_contents().strip()
                        content = self.replace_emojis(content)  
                        message_id = message['data-id'] 
                        timestamp_data = int(message.find('time', {'class': 'u-dt'})['data-time'])
                        message_time = datetime.fromtimestamp(timestamp_data)
                        current_time = datetime.now()

                        if (current_time - message_time) > timedelta(minutes=1):
                            continue

                        if content.startswith("/roll"):
                            if message_id not in self.processed_rolls:
                                roll_result = random.randint(1, 6)
                                roll_response = f"{user} rolled a {roll_result}"

                                page.get(URL)
                                input_box = page.run_js('return document.querySelector(".siropuShoutbox input.input");')
                                if input_box:
                                    page.run_js(f'document.querySelector(".siropuShoutbox input.input").value = "{roll_response}";')
                                    await asyncio.sleep(1)
                                    page.run_js('document.querySelector(\'button[aria-label="Shout!"]\').click();')
                                    print(f"Roll response sent to shoutbox: {roll_response}")
                                  
                                self.last_roll_time = current_time
                                self.processed_rolls.add(message_id)
                            continue 


                        if self.last_message_id is None or int(message_id) > int(self.last_message_id):
                            new_messages.append((timestamp, user, user_id, content))


                    if new_messages:
                        new_messages.reverse() 
                        for msg in new_messages:
                            uid_hyperlink = f"[{msg[2]}](https://fatality.win/members/{msg[2]})"
                            log_message = f"**{msg[1]}** (UID: {uid_hyperlink}): **{msg[3]}** *{msg[0]}*"
                            print(f"Sending message to DC: {log_message}")
                            await channel.send(log_message)

                        self.last_message_id = messages[-1]['data-id']
                    else:
                        print("No new messages to send.")
                else:
                    print("0 messages found in this container.")

            except Exception as e:
                print(f"An error occurred: {e}")

            await asyncio.sleep(1)  

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.presences = True

client = FatalityClient(intents=intents)

async def main():
    await client.start(TOKEN)

asyncio.run(main())
