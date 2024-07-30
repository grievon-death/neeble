"""
Bot commands.
"""

import os
import json
from datetime import datetime, timedelta

from time import sleep

from random import randrange

from discord import Embed, Intents
from discord.ext import commands
from settings.config import IMAGE_TYPES, OW_API_CONFIG, PERMISSIONS, QUOTE_STACK, RQ_LEADERBOARD, ROULETTE_LEADERBOARD

from utils.database import (count_quotes, count_quotes_user, get_by_id, get_by_user, get_quote_contains,
                            get_quotes, remove_quote, set_quote)
from utils.machine_monitor import Monitor
from utils.news_paper import News
from utils.tools import datetime_to_string, kbytes_to_gbytes
from utils.weather import displayweather, getweatherdata

client = commands.Bot(command_prefix='--', intents=Intents.all())

# This defines how big Neeble's quote "memory" is. If --rq is called, the quotes in the stack are removed from the query
stack_limit = int((count_quotes() * .25))

# When starting the bot for the first time, repetitions are going to be common. If, after a couple hundred saved quotes, the
# bot gets restarted a lot, the stack would reset and quotes would repeat themselves a lot more. Saving the stack on disk
# prevents repeating quotes in between restarts
with open(QUOTE_STACK, mode='r') as f:
    quote_id_stack = json.load(f)

# Leaderboards must never be reset with the bot.
with open(RQ_LEADERBOARD, mode='r') as f:
    rq_leaderboard = json.load(f)

# This dictionary is used to save the last message of all users in the server, used in `on_message(message)`
# which in turn is used in `grab_quote(bot: object)`
quote_content = {}

# Some commands (e.g. --roulette) cannot process two calls at the same time, comlock (or "command lock") serves as a way to make all affected commands wait.
comlock = {'roulette': False           
           }

# Used in `roulette(bot: object)`
drum = []
chamber = -1
pot = 1
russians = {}
with open(ROULETTE_LEADERBOARD, mode='r') as f:
    roulette_leaderboard = json.load(f)

# last_rq is a dictionary that keeps track of each user's --rq call; Sorting that dictionary by time everytime --rq is called _would_ be possible,
# but it would scale poorly, that's why last_rqer exists. rq_abusers is a dictionary that keeps track of how many failed --rq attempts each user has.
# After three "Chill.", --rq stops responding
last_rq = {}
last_rqer = ''
rq_abusers = {}

@client.event
async def on_message(message):
    content = str(message.content)
    author = str(message.author).split('#')[0]
    quote_content[author] = content
    await client.process_commands(message)

@client.command(aliases=['q'])
async def quote(bot: object, *quote: str) -> str:
    """
    Saves a quote into the database.
    """
    if not quote:
        return await bot.send('You\'re not my mute uncle, tell me something to remember.\n'\
            '(You haven\'t provided a quote)')

    quote = ' '.join(quote)

    if 'http' in quote and 'discord' in quote and not quote[-4:] in IMAGE_TYPES:
        return await bot.send("- _Check your link, dumbass! You're trying to quote an image from a"\
            " 'message, but you're quoting the message itself!_\n"\
            "'(Make sure to copy the link for the image by clicking on it, right-clicking the "\
            "image and then clicking on \"Save Link\")'")

    try:
        user = bot.author.name
        date = datetime.now().replace(microsecond=0)
        qtid = set_quote(user, quote, date, "#nograb")
    except Exception as ex:
        if ex.args[0].find("Duplicate") != -1:
            return await bot.send("There's already a quote from that same person, with that "\
                "exact match!")
        elif ex.args[0].find("Lost") != -1:
            await bot.send("SQL did an oopsie! Trying again...")
            sleep(2)
            qtid = set_quote(user, quote, date, "#nograb")
            return await bot.send(f"Done: `{quote}\n` ID: `{qtid}`")
        return await bot.send(f'{ex.args}\n_What the fuck are you doing?_')            
    else:
        global stack_limit
        stack_limit = int((count_quotes() * .25))
        return await bot.send(f"Done: `{quote}\n` ID: `{qtid}`")

@client.command(aliases=['g', 'grab'])
async def grab_quote(bot: object, *author: str) -> str:
    """
    Grabs the last thing someone said, and makes it into a quote.
    """
    author = ' '.join(author)
    if not author:
        return await bot.send("You haven\'t told me whose sentence I'm supposed to grab!")
    
    if author == bot.author.name or author == "Neeble" or author == "neebly":
        return await bot.send("`ALERTA LAMBEÇÃO DE CACETA`")

    if quote_content[author][:2] == "--":
        return await bot.send("I will not grab commands.")
    
    if author in quote_content.keys():
        try:
            grabber = bot.author.name
            quote = quote_content[author]
            date = datetime.now().replace(microsecond=0)
            qtid = set_quote(author, quote, date, grabber)
        except Exception as ex:
            if ex.args[0].find("Duplicate") != -1:
                return await bot.send("There's already a quote from that same person, with that "\
                    "exact match!")
            return await bot.send(f'{ex.args}\n_What the fuck are you doing?_')
        else:
            global stack_limit
            stack_limit = int((count_quotes() * .25))
            return await bot.send(f"Done: `{quote}\n` ID: `{qtid}`")
    else:
        return await bot.send("No quotes from anyone with that name!")


@client.command(aliases=['rq'])
async def random_quote(bot: object) -> str:
    """
    Get a random quote from the database.
    """
    global last_rq
    global last_rqer
    global rq_abusers
    chosen_one = get_quotes(quote_id_stack)
    stack_len = len(quote_id_stack)

# The next two IF statements are meant to deal with `--rq` abuse
    if last_rqer != bot.author.name:
        rq_abusers[last_rqer] = 0

    if last_rqer == bot.author.name and datetime.now() < last_rq[bot.author.name] + timedelta(seconds = 30):
        if bot.author.name in rq_abusers.keys():
            rq_abusers[bot.author.name] += 1
        else:
            rq_abusers[bot.author.name] = 1
        if rq_abusers[bot.author.name] > 3:
            return 0
        return await bot.send('Chill.')

    last_rqer = bot.author.name
    last_rq[bot.author.name] = datetime.now()


    #Adds to --rq leaderboard
    if bot.author.name in rq_leaderboard.keys():
        rq_leaderboard[bot.author.name] += 1
    else:
        rq_leaderboard[bot.author.name] = 1

    if not chosen_one and stack_len > 0:
        quote_id_stack.pop(0)
        chosen_one = get_quotes(quote_id_stack)
    elif not chosen_one:
        return await bot.send('You\'ve got no quotes saved yet.\n(Save quotes by using '\
            '`--q <quote`)')

    quote_id_stack.append(chosen_one.id)
    if stack_len >= stack_limit:
        quote_id_stack.pop(0)
    
    # Writes to persistent stackfile
    with open(QUOTE_STACK, mode='w') as f:
        json.dump(quote_id_stack, f)

    # Writes to persistent rq leaderboard
    with open(RQ_LEADERBOARD, mode='w') as f:
        json.dump(rq_leaderboard, f)

    try:
        # To image links.
        if 'http' in chosen_one.quote:
            return await bot.send(f'{chosen_one.quote}')
        if chosen_one.grabber == "#nograb":
            content = f'{chosen_one.quote}\n`By: {chosen_one.user}`'
        else:
            content = f'{chosen_one.quote}\n`By: {chosen_one.user} and grabbed by {chosen_one.grabber}`'
        return await bot.send(content)

    except Exception as ex:
        return await bot.send(ex)


@client.command(aliases=['qid'])
async def by_id(bot: object, _id: int=None) -> str:
    """
    Gets one quote by ID.
    """
    syntax = "`--qid <quote id>`"
    
    if not _id:
        return await bot.send("_If you don't tell me the ID, how the fuck do you expect me to "\
            f"quote it to you!?_\n(The correct syntax is {syntax})")

    quote = get_by_id(_id)

    if not quote:
        return await bot.send(f"_Wrong ID, sucker!_\n(There's no such quote with id {_id})")

    try:
        data = ''
        # To image links.
        if 'http' in quote.quote:
            return await bot.send(f'{quote.quote}')
        if quote.grabber == "#nograb":
            data = f'{quote.quote}\n`By: {quote.user}`'
        else:
            data = f'{quote.quote}\n`By: {quote.user} and grabbed by {quote.grabber}`'
        return await bot.send(data)

    except Exception as ex:
        return await bot.send(ex)

@client.command(aliases=['quser'])
async def by_user(bot: object, *user: str) -> str:
    """
    Gets one random quote from a specific user.
    """
    syntax = "`--quser <user>`"
    
    if not user:
        return await bot.send(f"The correct syntax is {syntax}")
    
    user = user[0]

    if user == bot.author.name:
        return await bot.send("`ALERTA LAMBEÇÃO DE CACETA`")

    quote = get_by_user(user)

    if not quote:
        return await bot.send(f"There are no quotes from {user}")

    try:
        data = ''
        # To image links.
        if 'http' in quote.quote:
            return await bot.send(f'{quote.quote}')
        if quote.grabber == "#nograb":
            data = f'{quote.quote}\n`By: {quote.user}`'
        else:
            data = f'{quote.quote}\n`By: {quote.user} and grabbed by {quote.grabber}`'
        return await bot.send(data)

    except Exception as ex:
        return await bot.send(ex)

@client.command(aliases=['qinfo'])
async def quote_info(bot: object, _id: str=None) -> str:
    """
    Prints out information about a quote
    """
    syntax = "--qinfo <quote id>"

    if not _id:
        return await bot.send("_If you don't tell me the ID, how the fuck do you expect me to "\
            f"get its info for you!?_\n(The correct syntax is {syntax})")

    if _id == "last":
        _id = quote_id_stack[-1]

    quote = get_by_id(int(_id))
    
    if not quote:
        return await bot.send(f"_Wrong ID, sucker!_\n(There's no such quote with id {_id})")
    
    user = quote.user
    date = quote.date if quote.date else "Before datetimes were stored"
    grabber = quote.grabber
    if grabber == "#nograb":
        data = f"```\n ID:              {_id}\n Quoted by:       {user}\n Quoted datetime: {date}\n```"
    else:
        data = f"```\n ID:              {_id}\n Quoted by:       {user}\n Grabbed by:      {grabber}\n Quoted datetime: {date}\n```"
    return await bot.send(data)


@client.command(aliases=['dq'])
async def delete_quote(bot, _id: int=None) -> str:
    """
    Deletes one quote by ID.
    """
    syntax = "`--dq <quote id>`"
    roles = [r.name for r in bot.author.roles]
    PermStatus = False

    if len(PERMISSIONS['dq']) < 1 or not len(set(PERMISSIONS['dq']).intersection(roles)) < 1:
        PermStatus = True

    if not PermStatus:
        return await bot.send("_And who the fuck do **YOU** think you are!?_.\n"\
            "(You don't have the necessary role for this command)")

    if not _id:
        return await bot.send("_If you don't tell me the ID, how the fuck do you expect me to "\
            f"delete it to you!?_\n(The correct syntax is {syntax})")

    quote = get_by_id(_id)

    if not quote:
        return await bot.send(f"_Wrong ID, sucker!_\n(There's no such quote with id {_id})")

    try:
        if not remove_quote(_id):
            return await bot.send('_Something wrong happened, dude!_')
        global stack_limit
        stack_limit = int((count_quotes() * .25))
        return await bot.send('_Evidence deleted, fella!_')

    except Exception as ex:
        return await bot.send(ex)


@client.command(aliases=['qstack'])
async def queue_stack(bot: object) -> str:
    """
    Displays the 5 quote history stack.
    """
    return await bot.send('A list of the 5 latest message IDs follows:'\
        f' `{",".join(str(q) for q in quote_id_stack[-5:])}`')

@client.command(aliases=['qc', 'cquotes'])
async def quote_count(bot: object) -> str:
    """
    Outputs a quote count from the database.
    """
    amount = count_quotes()
    msg = f"Quote count: `{amount}`"

    return await bot.send(msg)


@client.command(aliases=['v', 'version'])
async def info(bot: object) -> str:
    """
    Displays the bot's information.
    """
    roles = [r.name for r in bot.author.roles]
    PermStatus = False

    if len(PERMISSIONS['v']) < 1 or not len(set(PERMISSIONS['v']).intersection(roles)) < 1:
        PermStatus = True

    if not PermStatus:
        return await bot.send("_And who the fuck do **YOU** think you are!?_.\n"\
            "(You don't have the necessary role for this command)")
    
    motd = open("./motd", mode='r')
    text = motd.readlines()
    fullbanner = ""

    for lines in text:
        fullbanner = fullbanner + lines
    msg = f'''```\n{fullbanner}\n```'''

    return await bot.send(msg)


@client.command(aliases=['w'])
async def weather(bot: object, *location: str) -> str:
    """
    Displays the weather information for a given place.
    """
    
    if OW_API_CONFIG['api_id'] == 'no':
        return await bot.send("You haven't set up an API key! Make an user and set up an API key in https://openweathermap.org/\n \
        (The weather command hansn't been set up properly, make sure you have `OPENWEATHER_API_TOKEN` set up")
    if location:
        location = ' '.join(location)
        location = location.encode('utf-8').decode('utf-8')
        location = location.replace(" ", "+")
    else:
        location = "curitiba,paraná".encode('utf-8').decode('utf-8')

    weatherdata = getweatherdata(location)
    msg = displayweather(weatherdata)
    default_msg = 'No data!'
    embed = Embed(type='rich')
    embed.add_field(
        name='City',
        value=msg.name,
    )
    embed.add_field(
        name='Description',
        value=msg.description+f' {msg.icon}' if msg.description and msg.icon else default_msg,
    )
    embed.add_field(
        name='Temperature',
        value=f'{msg.temp} ºC' if msg.temp else default_msg,
    )
    embed.add_field(
        name='Feels like',
        value=f'{msg.feels_like} ºC' if msg.feels_like else default_msg,
    )
    embed.add_field(
        name='Humidity',
        value=f'{msg.humidity} %' if msg.humidity else default_msg,
    )
    embed.add_field(
        name='Cloud coverage',
        value=f'{msg.cloud_coverage} %' if msg.cloud_coverage else default_msg,
    )
    embed.add_field(
        name='Wind gusts',
        value=f'{msg.wind_gusts} m/s' if msg.wind_gusts else default_msg,
    )
    embed.add_field(
        name='Wind speed',
        value=f'{msg.wind_speed} m/s' if msg.wind_speed else default_msg,
    )

    return await bot.send('**`Weather`**', embed=embed)


@client.command(aliases=['qcontains', 'qsearch'])
async def quote_contains(bot: object, *part: str) -> str:
    """
    Filter quote by part of saved message.
    """
    syntax = '--qcontains <part>'

    if not part:
        return await bot.send("_If you don't tell me the part, how the fuck do you expect me to "\
            f"find it to you!?_\n(The correct syntax is {syntax})")

    part = ' '.join(part)

    quotes = get_quote_contains(part)

    if not quotes:
        return await bot.send(f"_Wrong text, sucker!_\n(There's no such quote with text `{part}`)")

    for quote in quotes:
        await bot.send(f'```\nID: {quote.id}\nMessage: {quote.quote[:10]} ... '\
            f'{quote.quote[-10:]}\nUser: {quote.user}\n```')

    return


@client.command(aliases=['macinfo', 'minfo'])
async def machine_info(bot: object, *args: str) -> str:
    """
    Return machine information.
    """
    embed = Embed(type='rich')
    supported_args = [
        'network'
    ]
    roles = [r.name for r in bot.author.roles]

    if 'BotMan' not in roles:
        return await bot.send("_And who the fuck do **YOU** think you are!?_.\n"\
            "(You don't have the necessary role for this command)")

    if not args:
        embed.add_field(name='CPU', value=f'{Monitor.cpu_percent} %')
        embed.add_field(name='RAM', value=f'{Monitor.memory.percent} %')
        embed.add_field(name='Swap', value=f'{Monitor.swap.percent} %')
        embed.add_field(name='Disk total', value=f'{kbytes_to_gbytes(Monitor.disk_usage.total)} Gb')
        embed.add_field(name='Disk used', value=f'{kbytes_to_gbytes(Monitor.disk_usage.used)} Gb')
        embed.add_field(name='Disk free', value=f'{kbytes_to_gbytes(Monitor.disk_usage.free)} Gb')
        return await bot.send('**`Monitor`**', embed=embed)

    if args[0] not in supported_args:
        return await bot.send('The argument is not supported!')

    if args[0] == 'network':
        ios = Monitor.net_io_counters

        for io in ios:
            embed.clear_fields()
            embed.add_field(name='Bytes received', value=ios[io].bytes_recv, inline=True)
            embed.add_field(name='Bytes sent', value=ios[io].bytes_sent, inline=True)
            embed.add_field(name='Packets received', value=ios[io].packets_recv, inline=True)
            embed.add_field(name='Packets sent', value=ios[io].packets_sent, inline=True)
            embed.add_field(name='Drop in', value=ios[io].dropin, inline=True)
            embed.add_field(name='Drop out', value=ios[io].dropout, inline=True)
            embed.add_field(name='Error in', value=ios[io].errin, inline=True)
            embed.add_field(name='Error out', value=ios[io].errout, inline=True)
            await bot.send(f'**`{io}`**', embed=embed)

        return


@client.command(aliases=['nw'])
async def news(bot: object, *options: str) -> None:
    """
    Return some news from Google.
    options:
        quantity: int
        search: str
    """
    embed = Embed(type='rich')
    filter = {}
    news = None

    if not options:
        _news = News(quantity=5)
        news = _news.news()

    else:
        # Validate option operation.
        if not all(['=' in op for op in options]):
            return await bot.send('Blabla')

        for op in options:
            key, value = op.split('=')
            filter[key] = value

        _news = News(quantity=filter.get('quantity', 5))
        news = _news.filter(phrase=filter.get('search'))

    if not news:
        return

    for new in news:
        dt = datetime_to_string(new['publishedAt'])
        embed.add_field(name='Font', value=new['source']['name'], inline=False)
        embed.add_field(name='Published at', value=dt, inline=False)
        embed.add_field(name='Link', value=new['url'], inline=False)
        embed.add_field(name=new['title'], value=new['description'], inline=False)
        embed.add_field(name='---', value='---')

    return await bot.send(f'**`News`**', embed=embed)

@client.command(aliases=['nf', 'nfetch'])
async def neofetch(bot: object) -> str:
    """
    Runs neofetch on the host.
    """
    os.system('neofetch --stdout --disable gpu --disable shell --disable packages --disable resolution --cpu_temp C > /tmp/neofetch')
    nfetch = open('/tmp/neofetch', mode='r')
    nfetch = nfetch.read()
    return await bot.send("```\n" + nfetch + "\n```")

@client.command(aliases=['qlb'])
async def count_leaderboard(bot:object) -> str:
    """
    Returns a list of quoters, sorted by amount of quotes.
    """
    qlb = "```\nLista de quoteiros\n"
    lis = count_quotes_user()
    lis = sorted(lis, key=lambda lis: lis[1], reverse=True)
    for data in lis:
        qlb = qlb + data[0] + " - " + str(data[1]) + "\n"
    qlb = qlb +  "```"

    return await bot.send(qlb)

@client.command(aliases=['rqlb'])
async def random_quote_leaderboard(bot:object) -> str:
    """
    Returns a list of --rq invokers, sorted by amount
    """
    data = "```\nLista de rqueiros\n"
    lis = rq_leaderboard
    lis = sorted(lis.items(), key=lambda x:x[1], reverse=True)
    for people in lis:
        data = data + people[0] + " - " + str(people[1]) +  "\n"
    data = data + "```"

    return await bot.send(data)

@client.command(aliases=['dr', 'droll'])
async def dice_roll(bot:object, size:int=6) -> str:
    """
    Generates a random number between 1 and <size>. Default size is 6.
    """
    syntax = '--dice_roll <size>'

    return await bot.send(f":game_die: : `{str(randrange(1, size + 1))}`")

@client.command(aliases=[])
async def roulette(bot:object, *option:str) -> str:
    """
    Russian Roulette
    """
    syntax = '--roulette'

    global drum
    global chamber
    global comlock
    global pot
    global russians
    global roulette_leaderboard
    spin = 0

    if comlock['roulette'] == True:
        await bot.send(bot.author.name + " has hit command lock")
        return 0

    if 'lb' in option:
        with open(ROULETTE_LEADERBOARD, mode='r') as file:
            data = "```\nLeaderboard do --roulette:\n"
            lis = json.load(file)
            lis = sorted(lis.items(), key=lambda x:x[1], reverse=True)
            for people in lis:
                data = data + people[0] + " - " + str(people[1]) + "\n"
            data = data + "```"
        return await bot.send(data)

    comlock['roulette'] = True

    if not drum:
        await bot.send("Inserting a bullet and spinning the drum...")
        drum.extend(['click']*6)
        for i in range(0, 10):
            spin = randrange(0, 6)
        drum[spin] = 'bang'
    
    chamber+=1

    if drum[chamber] == 'bang':
        chamber = -1
        drum = []
        pot = 1
        await bot.send(f"BANG! {bot.author.name} died.")
        russians[bot.author.name] = 0
        for r in russians.keys():
            try:
                roulette_leaderboard[r] += russians[r]
            except KeyError:
                roulette_leaderboard[r] = russians[r]
        with open(ROULETTE_LEADERBOARD, mode='w') as file:
            json.dump(roulette_leaderboard, file)
        russians = {}
        comlock['roulette'] = False
        return 0
    else:
        if chamber == 4:
            if bot.author.name in russians.keys():
                russians[bot.author.name] += pot
            else:
                russians[bot.author.name] = pot
            pot += 1
            chamber = -1
            drum = []
            drum.extend(['click']*6)
            spin = randrange(0, 6)
            drum[spin] = 'bang'
            comlock['roulette'] = False
            await bot.send("Click!")
            return await bot.send("FIFTH SHOT! Re-spinning the drum...")

        if bot.author.name in russians.keys():
            russians[bot.author.name] += pot
        else:
            russians[bot.author.name] = pot
        pot += 1
        await bot.send("Click!")
        comlock['roulette'] = False
        return 0

@client.command(aliases=['fc'])
async def fortune(bot:object) -> str:

    os.system("fortune > /tmp/fortune")
    cookie = open('/tmp/fortune', mode='r')
    cookie = cookie.read()
    return await bot.send("```\n" + cookie + "\n```")

@client.command(aliases=['dbg'])
async def neeble_debug(bot:object) -> str:
    """
    Outputs debug data.
    """

    # TODO: This is repeated role checking code from the deletion function, better make this into one function itself
    roles = [r.name for r in bot.author.roles]
    PermStatus = False

    if len(PERMISSIONS['dq']) < 1 or not len(set(PERMISSIONS['dq']).intersection(roles)) < 1:
        PermStatus = True

    if not PermStatus:
        return await bot.send("_And who the fuck do **YOU** think you are!?_.\n"\
            "(You don't have the necessary role for this command)")
    clock = comlock
    qt_count = count_quotes()
    st_size = len(quote_id_stack)
    last_quote = quote_id_stack[-1]
    ct_authors = str(quote_content.keys())
    lrqers = last_rq.keys()
    lrqer = last_rqer
    abusers = rq_abusers
    rl_drum = drum
    rl_chmb = chamber
    rl_pot = pot
    rl_russians = russians
    return await bot.send(f"```\ncomlock:{clock}\nqt_count:{qt_count}\nst_size:{st_size}\nst_limit:{stack_limit}\nlst_qt:{last_quote}\nct_authors:{ct_authors}\nlrqers:{lrqers}\nlrqer:{lrqer}\nabusers:{abusers}\nrl_drum:{rl_drum}\nrl_chmb:{rl_chmb}\nrl_pot:{rl_pot}\nrl_russians:{rl_russians}```")